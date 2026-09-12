# The Den -- Roadmap

One combined Sonarr+Radarr+Prowlarr+qBittorrent replacement. Built one milestone at a time,
~1 hour/day. Each milestone must run and be tested before the next starts.

Stack: Python + FastAPI + SQLite (SQLAlchemy/Alembic) + Jinja2 UI + libtorrent-rasterbar.
Deploy target: native systemd service on Arch Linux (no Docker).

## Milestones

- [x] M0 -- Skeleton: FastAPI boots, SQLite connects, `/health` works, systemd unit stub
- [x] M1 -- Indexer search (Prowlarr core): add Torznab/Newznab indexer, test connection, manual search, ranked results
- [x] M2 -- Movie library (Radarr core): TMDB lookup, add to library, missing/have status
- [x] M3 -- Release scoring: quality profiles + release-title parser, pick best result for a movie
- [x] M4 -- Download + import (movies): send to qBittorrent, monitor, auto-import/rename
- [x] M5 -- TV library (Sonarr core): series/season/episode via TMDB (not TVDB, see notes)
- [x] M6 -- TV search/grab/import: reuse M3/M4, SxxEyy in the search query
- [x] M7 -- Scheduler/RSS automation: background auto-grab on a timer
- [x] M8 -- Notifications + calendar
- [x] M9 -- Distro packaging: systemd unit, config conventions, PKGBUILD
- [x] M10 -- Built-in torrent client: libtorrent in-process, qBittorrent dependency removed
- [x] M11 -- Discover + Requests (done 2026-09-12): Overseerr-style browsing, Plex + local login, admin-only plumbing, Plex library awareness, user requests with admin approval -- planned, see [docs/requests-plan.md](docs/requests-plan.md)
- [x] M12 -- Indexer presets (done 2026-09-12): a Prowlarr-style catalog (public trackers, usenet, Jackett/Prowlarr/generic), native implementations for eight public trackers, and a Cloudflare solver (built-in Chromium or external FlareSolverr/Byparr) -- see [docs/indexers-plan.md](docs/indexers-plan.md)
- [x] M13 -- Plex-style file names (done 2026-09-12): imports keep hard-linking (torrents seed on) and now name files `Title (Year).ext` and `Show - S01E02 - Episode.ext` inside the existing `Movies/Title (Year)/` and `TV/Show/Season 01/` layout
- [ ] UI redesign track ("HoltOS Glass": left sidebar shell, glass/blur surfaces, poster-first pages, across web + KDE + Android) -- planned, see [docs/ui-redesign-plan.md](docs/ui-redesign-plan.md); sequenced ahead of M11's pages

## Notes
- Movies: TMDB. Free for non-commercial use, attribution required, needs a free API key
  (2-minute signup at themoviedb.org).
- TV: switched from TMDB to **TVmaze** (`app/tvmaze.py`) -- free, no API key, no account
  at all. `Series.tvmaze_id` is a TVmaze show id, unrelated to TMDB's id space; `Movie`
  still uses `tmdb_id`. Originally used TMDB's `/tv` endpoints for M5 (see commit
  history) to avoid TheTVDB's licensing question entirely, but TVmaze removes even the
  TMDB signup for the TV half of the app, so switched over.
- Real config goes in `.env` (see `.env.example`): TMDB_API_KEY, MOVIES_ROOT, TV_ROOT,
  DOWNLOADS_ROOT, STATE_DIR, TORRENT_PORT. Until you set a real TMDB key / indexer,
  `tests/mock_tmdb.py`, `tests/mock_torznab.py` and `tests/local_swarm.py` let the whole
  app be tested end-to-end without live accounts or internet.
- Download tracking uses the torrent's info-hash (`DownloadRecord.info_hash`), the key
  into the built-in engine. (Before M10 it used qBittorrent categories.)
- Known simplification: episode search doesn't verify the grabbed release's season/episode
  actually matches (relies on the SxxEyy search query steering indexer results correctly).
  Fine for now; a stricter release-title parser could validate this later if it causes
  wrong grabs in practice.
- Accounts and sign-in arrived with M11b (local users, Plex login, API tokens). Sign-in is
  optional until Settings -> Accounts turns it on; do not expose the app to the internet
  without doing so.
- M9 packaging (PKGBUILD, systemd, sysusers/tmpfiles) has been verified for real: a
  genuine Arch Linux environment (WSL2, systemd enabled), full `makepkg -si` +
  `pacman -U` + `systemctl enable --now`, service came up and answered `/health`.
  Found and fixed one real bug this way: the post-install migration failed with
  `ModuleNotFoundError: No module named 'app'` because `runuser` doesn't `cd` into
  `/opt/the-den` on its own, so alembic's `env.py` (which does `from app.db import
  Base`) couldn't find the package. Also disabled makepkg's debug-package generation
  -- meaningless for pure Python and it chokes on the Python 3.14 venv's non-ASCII
  "pithon" symlink easter egg. Not literally CachyOS (its kernel/scheduler differences
  don't come into play under a shared-kernel WSL environment), but identical at the
  pacman/systemd level that this packaging actually touches.

## Post-M9 addition: in-app Settings page

Added a `settings` DB table + `/ui/settings` page so TMDB key, library folders,
automation interval, and the Discord webhook can all be set from the browser instead of
hand-editing `.env`/the systemd env file. `app/settings.py`'s `effective(db)` layers DB
overrides on top of `app/config.py`'s env-var defaults -- env vars still work (useful for
the Arch packaging's `/etc/the-den/the-den.env`), the UI just wins when both are set.
Secret fields (TMDB key, Discord webhook) never echo their stored value back into the
page; leaving them blank on save keeps the existing value. Changing the automation
interval reschedules the running APScheduler job immediately via `scheduler.reschedule()`,
no restart needed.

## Post-redesign addition: JSON settings API

Added `app/routers/api_settings.py` -- `GET`/`POST /api/settings`, the same
get-effective/save logic as the `/ui/settings` HTML form (`app/settings.py`), just as
JSON instead of a form post. Needed by the-den-client's future M7 (its Settings screen
can't POST an HTML form). Secrets follow the same rule as the web UI: `GET` never
returns the stored value, only a `has_*` boolean; `POST` only overwrites a secret field
when a non-empty value is actually supplied.

## M10 -- Built-in torrent client

The direction change that makes this a genuine all-in-one: instead of talking to an
external qBittorrent over its WebUI API, The Den now *is* the torrent client.

- `app/torrent/engine.py` embeds **libtorrent-rasterbar** (what qBittorrent itself is built
  on) as one session for the whole process, started/stopped from FastAPI's lifecycle hooks
  like the scheduler. One asyncio task drains libtorrent's alert queue, saves resume data
  (on metadata arrival, on finish, every minute, and at shutdown) under `STATE_DIR`, and
  enforces seeding limits. Everything else is a thin synchronous call into the session.
- `engine.add()` accepts the three shapes indexer download links come in: a magnet link,
  a URL to a `.torrent` file, or a URL that 302-redirects to a magnet. Torrents are keyed by
  hex info-hash (v1 when present, else v2) -- chosen once at add time because
  `get_best()` flips from v1 to v2 for a hybrid torrent once its metadata arrives.
- `DownloadRecord.category` (the qBittorrent tag) became `DownloadRecord.info_hash`; the
  `qbit_*` settings became `downloads_root`, `torrent_port`, rate limits and seed limits
  (migration `b7e2f1c4d9a0`). `settings.effective()` now distinguishes "unset" from `0`,
  since `0` is a real value ("no limit") for the new numeric fields.
- The importer **hard-links** into the library (copy fallback across filesystems) instead
  of moving, so the torrent keeps seeding with no duplicate data. Once an imported torrent
  meets the seed ratio/time limit the engine stops it ("done"), and the automation cycle's
  reaper removes it with its files. Torrents added by hand (no record) are never reaped.
- New `/torrents` JSON API (list with live progress + what each torrent is for, add by
  hand, pause, resume, remove) and a live Downloads page built on it. `/downloads` gained
  `info_hash` so the companion apps can join records to live torrents.
- `tests/local_swarm.py` is a private swarm on localhost: seeder, minimal HTTP tracker,
  and the `.torrent`/magnet endpoints `mock_torznab.py` now links to. Two things it had to
  get right that are worth knowing: the tracker must answer in compact form (a
  tracker-supplied peer id that doesn't match the handshake gets the peer dropped), and
  a loopback swarm needs `allow_multiple_connections_per_ip` because libtorrent otherwise
  keeps one peer entry per IP and every peer here is 127.0.0.1. Also: libtorrent's
  `ignore_limits_on_local_network` (default on) means rate limits don't apply to the
  local seeder, so don't expect them to show up in this setup.
- Verified end to end against that swarm: grab, real download, import as hard link,
  `has_file`, seeding, seed-time limit, reaped with library copy intact; manual magnet
  add; pause/resume; restart restores every torrent from resume data. Not yet exercised
  against a public swarm.

Python packaging note: the PyPI `libtorrent` wheels stop at CPython 3.13, so on 3.14 the
bindings must come from the OS package (`python3-libtorrent` / `libtorrent-rasterbar`) and
the venv is created with `--system-site-packages`. The PKGBUILD does exactly that.

## All milestones done -- what's next is real-world shakedown, not new code

The build is feature-complete per this roadmap. What's left is exercising it against
real accounts/services (see README) and fixing whatever that surfaces -- that's expected
to turn up rough edges no amount of mock-based testing catches.
