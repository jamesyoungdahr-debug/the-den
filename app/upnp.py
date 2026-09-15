"""A small UPnP Internet Gateway Device client for remote access (M36).

libtorrent's port mapper can't be driven from Python here: its bindings fail to return the mapping
handles (a TypeError in libtorrent 2.0.12) and no port-map alerts arrive, so a mapping could never
be tracked or removed. This module speaks just enough UPnP IGD to add, check and delete one TCP
mapping: SSDP discovery, the device description, and the WANIPConnection / WANPPPConnection SOAP
actions. Only the standard library is used.

Everything the LAN sends back is untrusted: gateway URLs must be plain http to a private,
link-local or loopback IPv4 address, the SSDP answer must come from the host it names, documents
with a DTD are refused, responses are size-limited and every call has a timeout.
"""

from __future__ import annotations

import http.client
import ipaddress
import logging
import re
import socket
import time
import urllib.parse
from dataclasses import dataclass
from xml.etree import ElementTree as ET
from xml.sax.saxutils import escape

log = logging.getLogger(__name__)

SSDP_ADDR = ("239.255.255.250", 1900)
SEARCH_TARGETS = (
    "urn:schemas-upnp-org:device:InternetGatewayDevice:1",
    "urn:schemas-upnp-org:service:WANIPConnection:1",
    "urn:schemas-upnp-org:service:WANIPConnection:2",
    "urn:schemas-upnp-org:service:WANPPPConnection:1",
)
WAN_SERVICES = (
    "urn:schemas-upnp-org:service:WANIPConnection:2",
    "urn:schemas-upnp-org:service:WANIPConnection:1",
    "urn:schemas-upnp-org:service:WANPPPConnection:1",
)
MAX_RESPONSE_BYTES = 256 * 1024
HTTP_TIMEOUT_SECONDS = 5.0
UPNP_NO_SUCH_ENTRY = 714
UPNP_ONLY_PERMANENT_LEASES = 725


class UpnpError(Exception):
    def __init__(self, message: str, code: int | None = None):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Gateway:
    location: str
    control_url: str
    service_type: str
    local_ip: str  # this machine's address on the router's network


def _lan_host(host: str | None) -> bool:
    try:
        ip = ipaddress.ip_address(host or "")
    except ValueError:
        return False
    return ip.version == 4 and (ip.is_private or ip.is_link_local or ip.is_loopback)


def _checked_url(url: str) -> urllib.parse.SplitResult:
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "http" or not _lan_host(parts.hostname):
        raise UpnpError(f"Ignoring a gateway address outside the local network: {url[:100]}")
    return parts


def _has_dtd(data: bytes) -> bool:
    return re.search(rb"<!\s*(DOCTYPE|ENTITY)", data, re.IGNORECASE) is not None


def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _child_text(element: ET.Element, name: str) -> str:
    for child in element:
        if _local(child.tag) == name:
            return (child.text or "").strip()
    return ""


def _http(method: str, url: str, body: bytes | None = None, headers: dict[str, str] | None = None) -> tuple[int, bytes, str]:
    """(status, body, this machine's address on the connection)."""
    parts = _checked_url(url)
    conn = http.client.HTTPConnection(parts.hostname, parts.port or 80, timeout=HTTP_TIMEOUT_SECONDS)
    try:
        path = parts.path or "/"
        if parts.query:
            path += "?" + parts.query
        conn.request(method, path, body=body, headers=headers or {})
        local_ip = conn.sock.getsockname()[0]
        response = conn.getresponse()
        data = response.read(MAX_RESPONSE_BYTES + 1)
        if len(data) > MAX_RESPONSE_BYTES:
            raise UpnpError("The router sent an oversized response.")
        return response.status, data, local_ip
    except (OSError, http.client.HTTPException) as exc:
        raise UpnpError(f"Couldn't talk to the router: {exc}") from exc
    finally:
        conn.close()


def _search(timeout: float, target: tuple[str, int]) -> list[str]:
    """LOCATION URLs from SSDP answers, in arrival order and de-duplicated."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
    sock.settimeout(0.3)
    locations: list[str] = []
    try:
        for search_target in SEARCH_TARGETS:
            message = (
                "M-SEARCH * HTTP/1.1\r\n"
                "HOST: 239.255.255.250:1900\r\n"
                'MAN: "ssdp:discover"\r\n'
                "MX: 2\r\n"
                f"ST: {search_target}\r\n\r\n"
            ).encode("ascii")
            sock.sendto(message, target)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            try:
                data, sender = sock.recvfrom(4096)
            except socket.timeout:
                continue
            except OSError:
                break
            match = re.search(rb"(?im)^location:[ \t]*(\S+)[ \t]*\r?$", data)
            if not match:
                continue
            location = match.group(1).decode("ascii", "replace")
            parts = urllib.parse.urlsplit(location)
            # Plain http only, and the answer must come from the host it points at, so nothing on
            # the LAN can send us elsewhere.
            if parts.scheme == "http" and parts.hostname == sender[0] and _lan_host(parts.hostname) and location not in locations:
                locations.append(location)
    finally:
        sock.close()
    return locations


def parse_description(data: bytes, location: str) -> tuple[str, str] | None:
    """(control URL, service type) of the best WAN connection service in a device description."""
    if _has_dtd(data):
        return None
    try:
        root = ET.fromstring(data)
    except ET.ParseError:
        return None
    base = location
    for element in root.iter():
        if _local(element.tag) == "URLBase" and (element.text or "").strip():
            base = element.text.strip()
    found: dict[str, str] = {}
    for element in root.iter():
        if _local(element.tag) != "service":
            continue
        service_type = _child_text(element, "serviceType")
        control = _child_text(element, "controlURL")
        if service_type in WAN_SERVICES and control:
            found.setdefault(service_type, urllib.parse.urljoin(base, control))
    for service_type in WAN_SERVICES:
        if service_type in found:
            return found[service_type], service_type
    return None


def discover(timeout: float = 3.0, ssdp_target: tuple[str, int] = SSDP_ADDR) -> Gateway:
    """Find the router's WAN connection service, or raise UpnpError explaining why not."""
    locations = _search(timeout, ssdp_target)
    if not locations:
        raise UpnpError("No UPnP router answered. Turn on UPnP on the router, or forward the port by hand.")
    problem = "no details"
    for location in locations:
        try:
            status, body, local_ip = _http("GET", location)
            if status != 200:
                problem = f"its description answered HTTP {status}"
                continue
            parsed = parse_description(body, location)
            if parsed is None:
                problem = "it has no WAN connection service"
                continue
            control_url, service_type = parsed
            _checked_url(control_url)
            return Gateway(location=location, control_url=control_url, service_type=service_type, local_ip=local_ip)
        except UpnpError as exc:
            problem = str(exc)
    raise UpnpError(f"A UPnP device answered, but it isn't a usable router ({problem}).")


def _soap(gateway: Gateway, action: str, arguments: list[tuple[str, object]]) -> dict[str, str]:
    body = "".join(f"<{name}>{escape(str(value))}</{name}>" for name, value in arguments)
    envelope = (
        '<?xml version="1.0"?>'
        '<s:Envelope xmlns:s="http://schemas.xmlsoap.org/soap/envelope/" '
        's:encodingStyle="http://schemas.xmlsoap.org/soap/encoding/">'
        f'<s:Body><u:{action} xmlns:u="{escape(gateway.service_type)}">{body}</u:{action}></s:Body></s:Envelope>'
    ).encode("utf-8")
    headers = {"Content-Type": 'text/xml; charset="utf-8"', "SOAPAction": f'"{gateway.service_type}#{action}"'}
    status, data, _ = _http("POST", gateway.control_url, envelope, headers)
    if _has_dtd(data):
        raise UpnpError(f"The router's answer to {action} had a DTD, so it was ignored.")
    try:
        root = ET.fromstring(data) if data.strip() else None
    except ET.ParseError:
        root = None
    if status != 200:
        code, description = None, ""
        if root is not None:
            for element in root.iter():
                name = _local(element.tag)
                text = (element.text or "").strip()
                if name == "errorCode" and text.isdigit():
                    code = int(text)
                elif name == "errorDescription":
                    description = text
        detail = description or f"HTTP {status}"
        raise UpnpError(f"The router refused {action}: {detail}" + (f" (UPnP error {code})" if code else ""), code)
    if root is None:
        raise UpnpError(f"The router's answer to {action} wasn't XML.")
    values: dict[str, str] = {}
    for element in root.iter():
        if _local(element.tag) == f"{action}Response":
            for child in element:
                values[_local(child.tag)] = (child.text or "").strip()
    return values


def get_specific_mapping(gateway: Gateway, external_port: int) -> dict | None:
    """The router's TCP mapping for external_port, or None when there is none."""
    try:
        values = _soap(gateway, "GetSpecificPortMappingEntry",
                       [("NewRemoteHost", ""), ("NewExternalPort", external_port), ("NewProtocol", "TCP")])
    except UpnpError as exc:
        if exc.code == UPNP_NO_SUCH_ENTRY:
            return None
        raise
    port = values.get("NewInternalPort", "")
    return {
        "internal_client": values.get("NewInternalClient", ""),
        "internal_port": int(port) if port.isdigit() else None,
        "enabled": values.get("NewEnabled", "1").lower() in ("1", "true", "yes"),
        "description": values.get("NewPortMappingDescription", ""),
    }


def add_port_mapping(gateway: Gateway, external_port: int, internal_port: int, internal_client: str,
                     description: str, lease_seconds: int) -> int:
    """Add or refresh the TCP mapping; returns the lease used (0 when the router only allows permanent ones)."""
    arguments: list[tuple[str, object]] = [
        ("NewRemoteHost", ""), ("NewExternalPort", external_port), ("NewProtocol", "TCP"),
        ("NewInternalPort", internal_port), ("NewInternalClient", internal_client), ("NewEnabled", 1),
        ("NewPortMappingDescription", description), ("NewLeaseDuration", lease_seconds),
    ]
    try:
        _soap(gateway, "AddPortMapping", arguments)
        return lease_seconds
    except UpnpError as exc:
        if exc.code != UPNP_ONLY_PERMANENT_LEASES or not lease_seconds:
            raise
    arguments[-1] = ("NewLeaseDuration", 0)
    _soap(gateway, "AddPortMapping", arguments)
    return 0


def delete_port_mapping(gateway: Gateway, external_port: int) -> None:
    _soap(gateway, "DeletePortMapping", [("NewRemoteHost", ""), ("NewExternalPort", external_port), ("NewProtocol", "TCP")])


def get_external_ip(gateway: Gateway) -> str | None:
    values = _soap(gateway, "GetExternalIPAddress", [])
    try:
        return str(ipaddress.ip_address(values.get("NewExternalIPAddress", "")))
    except ValueError:
        return None
