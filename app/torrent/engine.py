"""In-process BitTorrent client built on libtorrent-rasterbar -- the same engine
qBittorrent is a GUI around. This is what makes The Den a single app instead of
"The Den + a torrent client": grabs go straight into this session, and the
download checker reads progress straight back out of it.

One asyncio task drains libtorrent's alert queue and enforces seeding limits;
everything else is a thin synchronous call into the session (cheap, thread-safe).

Persistence lives under EngineConfig.state_dir:
  resume/<key>.fastresume   per-torrent resume data: what's downloaded, where it
                            lives, trackers, and (once known) the metadata itself
  session.state             DHT routing table, so restarts don't re-bootstrap

`key` is the torrent's hex info-hash as chosen by _key() at add time -- v1 when
the torrent has one, else v2. It's what DownloadRecord.info_hash stores.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin

import httpx
import libtorrent as lt

log = logging.getLogger(__name__)

# libtorrent 2.0's bindings expose `version`; Arch's 2.1 bindings only `__version__`.
LT_VERSION = getattr(lt, "__version__", None) or getattr(lt, "version", "unknown")

_RESUME_SAVE_EVERY_SECONDS = 60
_SEED_LIMIT_CHECK_EVERY_SECONDS = 5
_ALERT_POLL_SECONDS = 0.5

_DHT_BOOTSTRAP_NODES = (
    "dht.libtorrent.org:25401,router.bittorrent.com:6881,"
    "router.utorrent.com:6881,dht.transmissionbt.com:6881"
)


@dataclass
class EngineConfig:
    state_dir: str
    downloads_root: str
    listen_port: int
    download_rate_limit_kib: int  # 0 = unlimited
    upload_rate_limit_kib: int  # 0 = unlimited
    seed_ratio_limit: float  # 0 = seed forever
    seed_time_limit_minutes: int  # 0 = seed forever


@dataclass
class TorrentStatus:
    info_hash: str
    name: str
    # metadata | checking | queued | downloading | seeding | done | paused | error
    state: str
    progress: float  # 0.0 - 1.0
    total_size: int
    downloaded: int
    uploaded: int
    download_rate: int  # bytes/s
    upload_rate: int  # bytes/s
    num_peers: int
    num_seeds: int
    eta_seconds: int | None
    ratio: float
    is_finished: bool
    save_path: str
    error: str | None
    added_at: int  # unix epoch


@dataclass
class TorrentFile:
    path: str  # absolute
    size: int
    downloaded: int


def _key(info_hashes) -> str:
    """Stable hex key for a torrent. Prefer v1 because most magnet links and
    indexers only carry v1; picked once at add time and never recomputed, since
    get_best() flips from v1 to v2 for a hybrid torrent once its metadata arrives."""
    if info_hashes.has_v1():
        return str(info_hashes.v1)
    return str(info_hashes.v2)


def _seconds(duration) -> float:
    # The bindings hand back timedelta for some duration fields and plain ints for others.
    return duration.total_seconds() if hasattr(duration, "total_seconds") else float(duration)


class TorrentEngine:
    def __init__(self) -> None:
        self._session: lt.session | None = None
        self._handles: dict[str, lt.torrent_handle] = {}
        self._task: asyncio.Task | None = None
        self._cfg: EngineConfig | None = None
        self._state_dir: Path | None = None

    # ---- lifecycle -------------------------------------------------------------

    @property
    def running(self) -> bool:
        return self._session is not None

    def info(self) -> dict:
        """Engine-wide facts for a status line: is it up, which port, is DHT bootstrapped."""
        if self._session is None:
            return {"running": False, "listen_port": None, "dht_running": False, "torrents": 0}
        return {
            "running": True,
            "listen_port": self._session.listen_port(),
            "dht_running": self._session.is_dht_running(),
            "torrents": len(self._handles),
        }

    def start(self, cfg: EngineConfig) -> None:
        """Create the session, restore every torrent we knew about, start the alert loop.
        Must be called from inside a running asyncio loop (FastAPI startup is)."""
        if self._session is not None:
            return
        self._cfg = cfg
        self._state_dir = Path(cfg.state_dir)
        (self._state_dir / "resume").mkdir(parents=True, exist_ok=True)
        Path(cfg.downloads_root).mkdir(parents=True, exist_ok=True)

        self._session = lt.session(self._settings(cfg))
        state_file = self._state_dir / "session.state"
        if state_file.exists():
            try:
                self._session.load_state(lt.bdecode(state_file.read_bytes()))
                # load_state can drag old settings along with the DHT table; ours win.
                self._session.apply_settings(self._settings(cfg))
            except Exception:
                log.warning("ignoring unreadable session state %s", state_file, exc_info=True)

        for f in sorted((self._state_dir / "resume").glob("*.fastresume")):
            try:
                params = lt.read_resume_data(f.read_bytes())
                self._handles[f.stem] = self._session.add_torrent(params)
            except Exception:
                log.warning("could not restore torrent from %s", f.name, exc_info=True)
        log.info("torrent engine up: port %s, %d torrent(s) restored", cfg.listen_port, len(self._handles))

        self._task = asyncio.get_running_loop().create_task(self._loop())

    def apply_config(self, cfg: EngineConfig) -> None:
        """Live-apply changed limits/port. state_dir and downloads_root changes only
        affect torrents added from now on (existing ones keep their save_path)."""
        self._cfg = cfg
        if self._session is not None:
            self._session.apply_settings(self._settings(cfg))

    async def stop(self) -> None:
        """Flush resume data + DHT state, then drop the session. Bounded wait so a
        stuck tracker can't hold up shutdown."""
        if self._session is None:
            return
        if self._task is not None:
            self._task.cancel()
            await asyncio.gather(self._task, return_exceptions=True)
            self._task = None

        self._session.pause()
        pending = 0
        for h in self._handles.values():
            if h.is_valid() and h.need_save_resume_data():
                h.save_resume_data(lt.torrent_handle.save_info_dict)
                pending += 1
        deadline = time.monotonic() + 10
        while pending > 0 and time.monotonic() < deadline:
            for a in self._session.pop_alerts():
                if isinstance(a, lt.save_resume_data_alert):
                    self._write_resume(a)
                    pending -= 1
                elif isinstance(a, lt.save_resume_data_failed_alert):
                    pending -= 1
            await asyncio.sleep(0.1)

        try:
            state = self._session.save_state(lt.save_state_flags_t.save_dht_state)
            (self._state_dir / "session.state").write_bytes(lt.bencode(state))
        except Exception:
            log.warning("could not save session state", exc_info=True)

        self._session = None
        self._handles.clear()

    def _settings(self, cfg: EngineConfig) -> dict:
        cat = lt.alert.category_t
        return {
            "listen_interfaces": f"0.0.0.0:{cfg.listen_port},[::]:{cfg.listen_port}",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "dht_bootstrap_nodes": _DHT_BOOTSTRAP_NODES,
            "user_agent": f"The Den (libtorrent/{LT_VERSION})",
            "alert_mask": cat.status_notification | cat.error_notification | cat.storage_notification,
            "download_rate_limit": max(cfg.download_rate_limit_kib, 0) * 1024,
            "upload_rate_limit": max(cfg.upload_rate_limit_kib, 0) * 1024,
        }

    # ---- adding torrents -------------------------------------------------------

    async def add(self, source: str, save_path: str | None = None) -> str:
        """Add a torrent from a magnet link, an http(s) URL to a .torrent file (or one
        that redirects to a magnet, as many indexers do), or a local .torrent path.
        Returns the key. Adding something already present is a no-op returning its key."""
        self._require_running()
        params = await self._params_from_source(source)
        params.save_path = save_path or self._cfg.downloads_root
        params.flags |= lt.torrent_flags.auto_managed

        info_hashes = params.info_hashes
        if not info_hashes.has_v1() and not info_hashes.has_v2() and params.ti is not None:
            info_hashes = params.ti.info_hashes()
        key = _key(info_hashes)
        existing = self._handles.get(key)
        if existing is not None and existing.is_valid():
            return key

        handle = self._session.add_torrent(params)
        self._handles[key] = handle
        handle.save_resume_data(lt.torrent_handle.save_info_dict)  # so a restart re-adds it even pre-metadata
        log.info("added torrent %s (%s)", key, params.name or source[:80])
        return key

    async def _params_from_source(self, source: str) -> lt.add_torrent_params:
        if source.startswith("magnet:"):
            return lt.parse_magnet_uri(source)
        if source.startswith(("http://", "https://")):
            return await self._fetch_torrent(source)
        path = Path(source)
        if path.is_file():
            return lt.load_torrent_buffer(path.read_bytes())
        raise ValueError(f"not a magnet link, URL, or .torrent file: {source[:120]}")

    async def _fetch_torrent(self, url: str) -> lt.add_torrent_params:
        async with httpx.AsyncClient(timeout=30, follow_redirects=False) as client:
            resp = await client.get(url)
            for _ in range(5):
                if not resp.is_redirect:
                    break
                location = resp.headers.get("location", "")
                if location.startswith("magnet:"):
                    return lt.parse_magnet_uri(location)
                resp = await client.get(urljoin(str(resp.url), location))
            resp.raise_for_status()
        try:
            return lt.load_torrent_buffer(resp.content)
        except RuntimeError as exc:
            raise ValueError(f"{url} did not return a .torrent file ({exc})") from exc

    # ---- inspection ------------------------------------------------------------

    def status(self, key: str) -> TorrentStatus | None:
        handle = self._handles.get(key)
        if handle is None or not handle.is_valid():
            return None
        return self._to_status(key, handle.status())

    def list(self) -> list[TorrentStatus]:
        out = []
        for key, handle in list(self._handles.items()):
            if handle.is_valid():
                out.append(self._to_status(key, handle.status()))
        out.sort(key=lambda s: s.added_at, reverse=True)
        return out

    def files(self, key: str) -> list[TorrentFile]:
        """Every file in the torrent with its absolute on-disk path. Empty until metadata is known."""
        handle = self._handles.get(key)
        if handle is None or not handle.is_valid():
            return []
        ti = handle.torrent_file()
        if ti is None:
            return []
        storage = ti.files()
        save_path = Path(handle.status().save_path)
        progress = handle.file_progress()
        return [
            TorrentFile(
                path=str(save_path / storage.file_path(i)),
                size=storage.file_size(i),
                downloaded=progress[i] if i < len(progress) else 0,
            )
            for i in range(storage.num_files())
        ]

    def _to_status(self, key: str, st) -> TorrentStatus:
        states = lt.torrent_status.states
        error = st.errc.message() if st.errc.value() != 0 else None
        if error:
            state = "error"
        elif st.paused:
            # Auto-managed + paused is libtorrent's queue; paused with auto-management
            # off is a deliberate stop. "done" (finished, stopped, and past the seed
            # limits) is what the reaper in app.download_check looks for -- a torrent
            # the user paused before its limits were met stays "paused" and is kept.
            if st.auto_managed:
                state = "queued"
            elif st.is_finished and self._seed_limits_met(st):
                state = "done"
            else:
                state = "paused"
        elif st.state in (states.checking_files, states.checking_resume_data, states.allocating):
            state = "checking"
        elif st.state == states.downloading_metadata:
            state = "metadata"
        elif st.state == states.downloading:
            state = "downloading"
        else:  # finished / seeding
            state = "seeding"

        remaining = st.total_wanted - st.total_wanted_done
        eta = remaining // st.download_payload_rate if (remaining > 0 and st.download_payload_rate > 0) else None
        denominator = st.all_time_download or st.total_done
        ratio = st.all_time_upload / denominator if denominator else 0.0

        return TorrentStatus(
            info_hash=key,
            name=st.name or key,
            state=state,
            progress=st.progress,
            total_size=st.total_wanted,
            downloaded=st.total_wanted_done,
            uploaded=st.all_time_upload,
            download_rate=st.download_payload_rate,
            upload_rate=st.upload_payload_rate,
            num_peers=st.num_peers,
            num_seeds=st.num_seeds,
            eta_seconds=eta,
            ratio=ratio,
            is_finished=st.is_finished,
            save_path=st.save_path,
            error=error,
            added_at=int(st.added_time),
        )

    # ---- control ---------------------------------------------------------------

    def pause(self, key: str) -> None:
        handle = self._handle(key)
        handle.unset_flags(lt.torrent_flags.auto_managed)  # or the queue would just restart it
        handle.pause()

    def resume(self, key: str) -> None:
        handle = self._handle(key)
        handle.set_flags(lt.torrent_flags.auto_managed)
        handle.resume()

    def remove(self, key: str, delete_files: bool = False) -> None:
        handle = self._handles.pop(key, None)
        if handle is not None and handle.is_valid():
            self._session.remove_torrent(handle, lt.options_t.delete_files if delete_files else 0)
        resume_file = self._state_dir / "resume" / f"{key}.fastresume"
        if resume_file.exists():
            resume_file.unlink()

    def _handle(self, key: str) -> lt.torrent_handle:
        self._require_running()
        handle = self._handles.get(key)
        if handle is None or not handle.is_valid():
            raise KeyError(key)
        return handle

    def _require_running(self) -> None:
        if self._session is None:
            raise RuntimeError("torrent engine is not running")

    # ---- background loop -------------------------------------------------------

    async def _loop(self) -> None:
        last_resume_save = last_seed_check = time.monotonic()
        while True:
            try:
                for alert in self._session.pop_alerts():
                    self._handle_alert(alert)
                now = time.monotonic()
                if now - last_seed_check >= _SEED_LIMIT_CHECK_EVERY_SECONDS:
                    self._enforce_seed_limits()
                    last_seed_check = now
                if now - last_resume_save >= _RESUME_SAVE_EVERY_SECONDS:
                    for handle in list(self._handles.values()):
                        if handle.is_valid() and handle.need_save_resume_data():
                            handle.save_resume_data(lt.torrent_handle.save_info_dict)
                    last_resume_save = now
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("torrent engine loop error")
            await asyncio.sleep(_ALERT_POLL_SECONDS)

    def _handle_alert(self, alert) -> None:
        if isinstance(alert, lt.save_resume_data_alert):
            self._write_resume(alert)
        elif isinstance(alert, (lt.torrent_finished_alert, lt.metadata_received_alert)):
            # Both change what a restart needs to know (finished flag / the metadata).
            if alert.handle.is_valid():
                alert.handle.save_resume_data(lt.torrent_handle.save_info_dict)
        elif isinstance(alert, (lt.torrent_error_alert, lt.file_error_alert, lt.listen_failed_alert)):
            log.warning("libtorrent: %s", alert.message())

    def _write_resume(self, alert) -> None:
        key = _key(alert.params.info_hashes)
        if key not in self._handles:
            return  # removed while the save was in flight
        data = lt.write_resume_data_buf(alert.params)
        target = self._state_dir / "resume" / f"{key}.fastresume"
        tmp = target.with_suffix(".tmp")
        tmp.write_bytes(data)
        tmp.replace(target)

    def _seed_limits_met(self, st) -> bool:
        cfg = self._cfg
        if not cfg.seed_ratio_limit and not cfg.seed_time_limit_minutes:
            return False
        denominator = st.all_time_download or st.total_done
        ratio = st.all_time_upload / denominator if denominator else 0.0
        seeded_minutes = _seconds(st.seeding_duration) / 60
        ratio_met = bool(cfg.seed_ratio_limit) and ratio >= cfg.seed_ratio_limit
        time_met = bool(cfg.seed_time_limit_minutes) and seeded_minutes >= cfg.seed_time_limit_minutes
        return ratio_met or time_met

    def _enforce_seed_limits(self) -> None:
        for key, handle in list(self._handles.items()):
            if not handle.is_valid():
                continue
            st = handle.status()
            if not st.is_finished or st.paused:
                continue
            if self._seed_limits_met(st):
                log.info("seed limits met for %s -- stopping", st.name)
                handle.unset_flags(lt.torrent_flags.auto_managed)
                handle.pause()


engine = TorrentEngine()
