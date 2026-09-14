"""mDNS/DNS-SD discovery for The Den server."""

from __future__ import annotations

import asyncio
import logging
import socket
import uuid
from ipaddress import IPv4Address
from pathlib import Path
from typing import Any

import ifaddr
from app import config
from zeroconf import IPVersion
from zeroconf.asyncio import AsyncServiceInfo, AsyncZeroconf

log = logging.getLogger(__name__)

SERVICE_TYPE = "_theden._tcp.local."
API_VERSION = "2"

# Module state (reset on stop)
_loop: asyncio.AbstractEventLoop | None = None
_zeroconf: AsyncZeroconf | None = None
_info: AsyncServiceInfo | None = None
_current_name: str | None = None
_addresses: list[str] = []


def server_id() -> str:
    """The random id of this install. Path: Path(config.STATE_DIR) / "server_id"."""
    path = Path(config.STATE_DIR) / "server_id"
    try:
        content = path.read_text(encoding="utf-8").strip()
        if len(content) == 32 and all(c in "0123456789abcdef" for c in content):
            return content
    except (OSError, UnicodeDecodeError):
        pass

    path.parent.mkdir(parents=True, exist_ok=True)
    value = uuid.uuid4().hex
    path.write_text(value, encoding="utf-8")
    return value


def display_name(s: Any) -> str:
    """Return the first non-empty value after .strip() of: s.plex_server_name, s.server_name, config.SERVER_NAME, socket.gethostname()."""
    for name in (s.plex_server_name, s.server_name, config.SERVER_NAME, socket.gethostname()):
        if name and name.strip():
            return name.strip()
    return ""


def advertised_addresses() -> list[str]:
    """IPv4 addresses to advertise, based on config.WEB_HOST read on every call."""
    host = config.WEB_HOST

    # Loopback or wildcard: handle specially
    if not host or host == "0.0.0.0" or host == "::":
        addresses: list[str] = []
        for adapter in ifaddr.get_adapters():
            for ip in adapter.ips:
                if isinstance(ip.ip, str) and not ip.ip.startswith("127."):
                    addresses.append(ip.ip)
        # Remove duplicates while preserving order
        seen: set[str] = set()
        result: list[str] = []
        for addr in addresses:
            if addr not in seen:
                seen.add(addr)
                result.append(addr)
        return result

    loopback_values = ("localhost", "::1")
    if host in loopback_values or host.startswith("127."):
        return []

    # Try IPv4Address first
    try:
        IPv4Address(host)
        return [host]
    except (ValueError, OSError):
        pass

    # Try DNS resolution
    try:
        resolved = socket.gethostbyname(host)
        if not resolved.startswith("127."):
            return [resolved]
    except (OSError, socket.gaierror, socket.herror):
        pass

    return []


def instance_name(name: str) -> str:
    """The DNS-SD instance label for `name`: replace every "." with " ", collapse runs of whitespace to one space, strip, and cut to at most 63 bytes of UTF-8 without splitting a character."""
    label = name.replace(".", " ")
    label = " ".join(label.split())
    label = label.strip()
    encoded = label.encode("utf-8", errors="ignore")
    if len(encoded) > 63:
        label = encoded[:63].decode("utf-8", errors="ignore").strip()
    if not label:
        label = "The Den"
    return f"{label}.{SERVICE_TYPE}"


async def start(s: Any) -> None:
    """Remember the running loop and advertise display_name(s)."""
    global _loop, _zeroconf, _info, _current_name

    _loop = asyncio.get_running_loop()
    name = display_name(s)

    addresses = advertised_addresses()
    if not addresses:
        log.info("Server is not advertised because WEB_HOST is a loopback address")
        return

    try:
        _zeroconf = AsyncZeroconf(ip_version=IPVersion.V4Only)
        await _register(name)
    except Exception:
        log.warning("LAN discovery could not start", exc_info=True)
        if _zeroconf is not None:
            try:
                await _zeroconf.async_close()
            except Exception:
                pass
        _zeroconf = None
        _info = None
        _current_name = None


async def stop() -> None:
    """Unregister the service and close the AsyncZeroconf, then reset the module state."""
    global _loop, _zeroconf, _info, _current_name, _addresses

    if _zeroconf and _info is not None:
        try:
            await _zeroconf.async_unregister_service(_info)
        except Exception as exc:
            log.warning("Failed to unregister service", exc_info=True)

    if _zeroconf is not None:
        try:
            await _zeroconf.async_close()
        except Exception as exc:
            log.warning("Failed to close Zeroconf", exc_info=True)

    _loop = None
    _zeroconf = None
    _info = None
    _current_name = None
    _addresses = []


def refresh(s: Any) -> None:
    """Called from request handlers (which may run in a worker thread) after settings change."""
    name = display_name(s)

    if not _loop or not _zeroconf or name == _current_name:
        return

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    async def do_reregister() -> None:
        await _reregister(name)

    if running_loop == _loop:
        _loop.create_task(do_reregister())
    else:
        asyncio.run_coroutine_threadsafe(do_reregister(), _loop)


def current() -> dict[str, Any]:
    """Return {"advertised": bool, "name": the advertised name or None, "addresses": the advertised addresses list (empty when not advertised)}."""
    return {
        "advertised": _info is not None,
        "name": _current_name,
        "addresses": list(_addresses) if _info is not None else [],
    }


async def _register(name: str) -> None:
    """Build and register the service."""
    global _info, _current_name, _addresses
    addresses = advertised_addresses()
    info = AsyncServiceInfo(
        SERVICE_TYPE,
        instance_name(name),
        addresses=[socket.inet_aton(a) for a in addresses],
        port=config.WEB_PORT,
        properties={"name": name, "id": server_id(), "api": API_VERSION},
        server=f"{socket.gethostname()}.local.",
    )
    await _zeroconf.async_register_service(info, allow_name_change=True)
    _info = info
    _current_name = name
    _addresses = addresses
    log.info("Advertising %s on %s port %d", instance_name(name), addresses, config.WEB_PORT)


async def _reregister(name: str) -> None:
    """Unregister the old service and register with the new name."""
    global _info, _current_name
    if _info is not None:
        try:
            await _zeroconf.async_unregister_service(_info)
            _info = None
            _current_name = None
        except Exception as exc:
            log.warning("Failed to unregister service", exc_info=True)

    try:
        await _register(name)
    except Exception as exc:
        log.warning("Failed to reregister service", exc_info=True)
