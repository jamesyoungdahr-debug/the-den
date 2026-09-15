"""Remote access through the router (M36).

A small UPnP client (app/upnp.py) asks the router to forward external TCP WEB_PORT to this
machine's WEB_PORT. The guard refuses unless the server is safe to expose: HTTPS on with an
unexpired certificate, a bind that isn't loopback, first-run setup finished, and never port 80 or
443 (Liam, 2026-09-14). apply() is cheap and idempotent: it runs at startup, after a settings
change and from the periodic re-check, and does the router work in a background thread. Mappings
use a one-hour lease that the re-check renews, so a server that dies without cleaning up drops
off the router on its own. A rule on the router that forwards the port to another machine is
never touched.

Liam doesn't know whether his router does NAT loopback, so check_loopback() finds out: it
connects to https://<public host>:<external port> from this machine, pins the served key against
our own pin and compares the server id from /health. A result from inside the house proves
loopback only; reachability from outside still needs a test on mobile data.
"""

from __future__ import annotations

import asyncio
import http.client
import ipaddress
import json
import logging
import ssl
import threading
from datetime import datetime, timedelta, timezone
from typing import Any

from app import config, tls

log = logging.getLogger(__name__)

FORBIDDEN_EXTERNAL_PORTS = frozenset({80, 443})
RECHECK_MINUTES = 10
LEASE_SECONDS = 3600
RENEW_AFTER = timedelta(minutes=25)
LOOPBACK_TIMEOUT_SECONDS = 8
MAPPING_DESCRIPTION = "The Den"

# off: disabled in Settings. refused: enabled but the guard (or the router's existing rules) says
# no. mapping: talking to the router. mapped: the router lists the mapping. error: no usable
# router, or it refused.
STATES = ("off", "refused", "mapping", "mapped", "error")

_lock = threading.RLock()
_generation = 0  # bumped by every decision; a router job from an older decision drops its result
_workers: list[threading.Thread] = []
_state: dict[str, Any] = {
    "state": "off",
    "reason": None,
    "external_port": None,
    "external_ip": None,
    "internal_client": None,
    "router": None,
    "lease_seconds": None,
    "mapped_at": None,
    "loopback": "unknown",  # works | fails | unknown
    "loopback_detail": None,
    "loopback_checked_at": None,
    "updated_at": None,
}
_gateway: Any = None  # the router the current mapping lives on


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _set(**changes: Any) -> None:
    _state.update(changes)
    _state["updated_at"] = _now().isoformat()


def _default_client() -> Any:
    from app import upnp

    return upnp


def guard(setup_complete: bool) -> str | None:
    """None when the server may be exposed through the router, else the reason in plain words."""
    port = config.WEB_PORT
    if port in FORBIDDEN_EXTERNAL_PORTS:
        return f"Port {port} is never forwarded. Set WEB_PORT to another port, such as 40204."
    if not 1 <= port <= 65535:
        return f"WEB_PORT {port} isn't a valid port."
    if tls.is_loopback(config.WEB_HOST):
        return "The server only listens on this machine (WEB_HOST is a loopback address), so there is nothing to forward to."
    if not tls.enabled():
        return "HTTPS is off. Remote access needs HTTPS."
    expires = tls.certificate_expires_at()
    if expires is None:
        return "There is no certificate yet. Restart the server to make one."
    if expires <= _now():
        return "The certificate has expired. Restart the server to reissue it."
    if not setup_complete:
        return "First-run setup isn't finished."
    return None


def _clear_mapping_fields() -> None:
    _state.update(external_port=None, internal_client=None, router=None, lease_seconds=None, mapped_at=None,
                  loopback="unknown", loopback_detail=None)


def _launch(target: Any, *args: Any) -> None:
    worker = threading.Thread(target=target, args=args, name="remote-access", daemon=True)
    _workers[:] = [w for w in _workers if w.is_alive()]
    _workers.append(worker)
    worker.start()


def _needs_renewal() -> bool:
    mapped_at = _state["mapped_at"]
    if not mapped_at:
        return True
    return _now() - datetime.fromisoformat(mapped_at) >= RENEW_AFTER


def apply(settings: Any, setup_complete: bool, client: Any = None) -> dict[str, Any]:
    """Make the router mapping match the settings: map (or renew) when remote access is enabled and
    the guard passes, remove our mapping otherwise. Returns at once; the router work runs in a thread."""
    global _generation
    client = client or _default_client()
    enabled = bool(getattr(settings, "remote_access_enabled", False))
    with _lock:
        reason = guard(setup_complete) if enabled else None
        if not enabled or reason is not None:
            had_mapping = _gateway is not None
            if _state["state"] not in ("off", "refused") or had_mapping:
                _generation += 1
                if had_mapping:
                    log.info("Remote access %s; removing the router mapping", "refused" if reason else "turned off")
                    _launch(_unmap_job, client, _gateway, _state["external_port"] or config.WEB_PORT)
            _clear_mapping_fields()
            _set(state="refused" if reason else "off", reason=reason)
            return status()
        if _state["state"] == "mapping":
            return status()
        if _state["state"] == "mapped" and _state["external_port"] == config.WEB_PORT and not _needs_renewal():
            return status()
        _generation += 1
        if _state["state"] != "mapped":
            _set(state="mapping", reason=None)
        _launch(_map_job, client, _generation, config.WEB_PORT, config.WEB_HOST)
        return status()


def _map_job(client: Any, generation: int, port: int, web_host: str) -> None:
    global _gateway
    try:
        gateway = client.discover()
        local_ip = gateway.local_ip
        if web_host and web_host not in ("0.0.0.0", "::"):
            try:
                bound = str(ipaddress.ip_address(web_host))
            except ValueError:
                bound = None
            if bound and bound != local_ip:
                raise _Refused(f"The server listens on {bound}, but the router reaches this machine as {local_ip}.")
        existing = client.get_specific_mapping(gateway, port)
        if existing and existing.get("internal_client") and existing["internal_client"] != local_ip:
            raise _Refused(
                f"Port {port} on the router already forwards to {existing['internal_client']}. "
                "Remove that rule on the router first."
            )
        lease = client.add_port_mapping(gateway, port, port, local_ip, MAPPING_DESCRIPTION, LEASE_SECONDS)
        confirmed = client.get_specific_mapping(gateway, port)
        if not confirmed or confirmed.get("internal_client") != local_ip or confirmed.get("internal_port") != port:
            raise _Failed("The router accepted the mapping but doesn't list it.")
        try:
            external_ip = client.get_external_ip(gateway)
        except Exception:
            external_ip = None
    except _Refused as exc:
        _finish(generation, state="refused", reason=str(exc))
        return
    except Exception as exc:  # UpnpError, or anything unexpected from the network
        _finish(generation, state="error", reason=str(exc) or exc.__class__.__name__)
        return
    with _lock:
        if generation != _generation:
            stale = True
        else:
            stale = False
            _gateway = gateway
            renewed = _state["state"] == "mapped"
            _set(state="mapped", reason=None, external_port=port, external_ip=external_ip, internal_client=local_ip,
                 router=gateway.location, lease_seconds=lease, mapped_at=_now().isoformat())
    if stale:
        # Remote access was turned off (or refused) while the router was answering: undo it.
        _unmap_job(client, gateway, port)
        return
    if not renewed:
        log.info("The router forwards TCP port %s to %s (lease %s s)", port, local_ip, lease or "permanent")


class _Refused(Exception):
    pass


class _Failed(Exception):
    pass


def _finish(generation: int, **changes: Any) -> None:
    global _gateway
    with _lock:
        if generation != _generation:
            return
        _gateway = None
        _clear_mapping_fields()
        _set(**changes)
    log.warning("Remote access: %s", changes.get("reason"))


def _unmap_job(client: Any, gateway: Any, port: int) -> None:
    """Delete our mapping, but only while the router's rule still points at this machine."""
    global _gateway
    if gateway is None:
        return
    try:
        existing = client.get_specific_mapping(gateway, port)
        if existing and existing.get("internal_client") == gateway.local_ip:
            client.delete_port_mapping(gateway, port)
            log.info("Removed the router mapping for TCP port %s", port)
    except Exception as exc:
        log.warning("Couldn't remove the router mapping for TCP port %s: %s", port, exc)
    with _lock:
        if _gateway is gateway:
            _gateway = None


def stop(client: Any = None) -> None:
    """Remove our mapping on shutdown (waits for the router, bounded by the client's timeouts)."""
    global _generation
    client = client or _default_client()
    with _lock:
        _generation += 1
        gateway, port = _gateway, _state["external_port"] or config.WEB_PORT
        _clear_mapping_fields()
        _set(state="off", reason=None)
    _unmap_job(client, gateway, port)


def wait_idle(timeout: float = 30.0) -> None:
    """Wait for background router work to finish (tests and the manual check)."""
    for worker in list(_workers):
        worker.join(timeout)


def _probe(host: str, port: int, own_pin: str, own_id: str) -> tuple[str, str]:
    """Connect to host:port over TLS, check the served key against our pin, then compare /health's
    server_id. Certificate chain checks are replaced by the pin check."""
    context = ssl.create_default_context()
    context.check_hostname = False
    context.verify_mode = ssl.CERT_NONE
    conn = http.client.HTTPSConnection(host, port, context=context, timeout=LOOPBACK_TIMEOUT_SECONDS)
    try:
        conn.connect()
        der = conn.sock.getpeercert(binary_form=True)
        if not der:
            return "fails", "The address answered without a certificate."
        if tls.pin_for_certificate_der(der) != own_pin:
            return "fails", "Something else answers on the public address (its certificate key isn't this server's)."
        conn.request("GET", "/health", headers={"Host": f"{host}:{port}", "Connection": "close"})
        response = conn.getresponse()
        body = response.read(64 * 1024)
        if response.status != 200:
            return "fails", f"The public address answered HTTP {response.status}."
        try:
            data = json.loads(body)
        except ValueError:
            return "fails", "The public address didn't answer with The Den's /health."
        if data.get("server_id") != own_id:
            return "fails", "The public address reached a different The Den server."
        return "works", "This server reached itself through its public address."
    except (OSError, ssl.SSLError, http.client.HTTPException) as exc:
        return "fails", f"Couldn't reach the public address from this machine: {exc}"
    finally:
        conn.close()


async def check_loopback(settings: Any) -> dict[str, Any]:
    """NAT loopback self-check: works, fails or unknown (no public name, HTTPS off, or not mapped)."""
    from app import discovery

    host = (getattr(settings, "public_host", None) or "").strip()
    own_pin = tls.pin()
    with _lock:
        mapped = _state["state"] == "mapped"
        port = _state["external_port"] or config.WEB_PORT
    if not host:
        result, detail = "unknown", "Set the public name in Settings to test it."
    elif not own_pin:
        result, detail = "unknown", "HTTPS is off."
    elif not mapped:
        result, detail = "unknown", "The router mapping isn't confirmed yet."
    else:
        result, detail = await asyncio.to_thread(_probe, host, port, own_pin, discovery.server_id())
    with _lock:
        _set(loopback=result, loopback_detail=detail, loopback_checked_at=_now().isoformat())
    return status()


def status() -> dict[str, Any]:
    """A copy of the current state for the API, Settings and health checks."""
    with _lock:
        return dict(_state)
