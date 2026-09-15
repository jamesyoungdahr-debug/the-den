"""HTTPS for The Den (M35).

Liam never opens ports 80 or 443 on the router, and the router DDNS name has no DNS API, so no
ACME challenge can issue a certificate browsers trust; that arrives with Cloudflare DNS-01 in
M48. Until then the server makes its own certificate under STATE_DIR/tls and the apps pin it.

The pin is the SHA-256 of the certificate's public key (SubjectPublicKeyInfo), in OkHttp's
"sha256/<base64>" form, not a hash of the whole certificate: the key is made once and kept, so
a new LAN address or public name reissues the certificate without breaking any app's pin.
"""

from __future__ import annotations

import base64
import hashlib
import ipaddress
import logging
import os
import socket
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

from app import config

log = logging.getLogger(__name__)

MODES = ("auto", "on", "off")
VALID_DAYS = 730
RENEW_WITHIN_DAYS = 30
KEY_FILE = "server.key"
CERT_FILE = "server.crt"

_pin_cache: tuple[float, str] | None = None


def is_loopback(host: str | None) -> bool:
    """True for localhost and 127.x / ::1. An empty host binds every interface, so it isn't."""
    if not host:
        return False
    if host.strip().lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host.strip()).is_loopback
    except ValueError:
        return False


def mode() -> str:
    """TLS from the environment: auto (the default), on or off. Anything else counts as auto."""
    value = (config.TLS or "auto").strip().lower()
    return value if value in MODES else "auto"


def enabled() -> bool:
    """HTTPS is on with TLS=on, or with TLS=auto whenever WEB_HOST isn't a loopback address."""
    current = mode()
    if current == "auto":
        return not is_loopback(config.WEB_HOST)
    return current == "on"


def tls_dir() -> Path:
    return Path(config.STATE_DIR) / "tls"


def cert_path() -> Path:
    return tls_dir() / CERT_FILE


def key_path() -> Path:
    return tls_dir() / KEY_FILE


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    return [v for v in values if not (v in seen or seen.add(v))]


def wanted_names(public_host: str | None = None) -> tuple[list[str], list[str]]:
    """(DNS names, IP addresses) the certificate has to cover: localhost, this machine's
    hostname and .local name, the public name, loopback and every LAN address the server
    advertises."""
    from app import discovery  # discovery imports this module

    dns = ["localhost"]
    ips = ["127.0.0.1"]
    host = socket.gethostname().strip().lower()
    candidates = [host, f"{host}.local"] if host else []
    public = (public_host or "").strip().lower().rstrip(".")
    if public:
        try:
            ips.append(str(ipaddress.ip_address(public)))
        except ValueError:
            candidates.append(public)
    for name in candidates:
        # x509 DNS names must be ASCII; a non-ASCII hostname is simply left out.
        if name and name.isascii() and " " not in name:
            dns.append(name)
    for addr in discovery.advertised_addresses():
        try:
            ips.append(str(ipaddress.ip_address(addr)))
        except ValueError:
            continue
    return _dedupe(dns), _dedupe(ips)


def _write_atomic(path: Path, data: bytes, mode_bits: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode_bits)
    with os.fdopen(fd, "wb") as handle:
        handle.write(data)
    os.chmod(tmp, mode_bits)  # the umask may have narrowed or O_CREAT kept an old file's bits
    os.replace(tmp, path)


def _load_or_create_key() -> ec.EllipticCurvePrivateKey:
    path = key_path()
    if path.exists():
        try:
            key = serialization.load_pem_private_key(path.read_bytes(), password=None)
            if isinstance(key, ec.EllipticCurvePrivateKey):
                return key
            log.error("TLS key at %s isn't an EC key; making a new one (apps must pin again)", path)
        except (OSError, ValueError, TypeError) as exc:
            log.error("TLS key at %s is unreadable (%s); making a new one (apps must pin again)", path, exc)
    try:
        os.makedirs(tls_dir(), exist_ok=True)
        os.chmod(tls_dir(), 0o700)
    except OSError:
        pass
    key = ec.generate_private_key(ec.SECP256R1())
    pem = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
    _write_atomic(path, pem, 0o600)
    return key


def _spki(public_key) -> bytes:
    return public_key.public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)


def _load_cert() -> x509.Certificate | None:
    try:
        return x509.load_pem_x509_certificate(cert_path().read_bytes())
    except (OSError, ValueError):
        return None


def _covers(cert: x509.Certificate, dns: list[str], ips: list[str]) -> bool:
    try:
        san = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
    except x509.ExtensionNotFound:
        return False
    have_dns = {name.lower() for name in san.get_values_for_type(x509.DNSName)}
    have_ips = {str(addr) for addr in san.get_values_for_type(x509.IPAddress)}
    return have_dns == set(dns) and have_ips == set(ips)


def ensure_certificate(public_host: str | None = None) -> tuple[Path, Path]:
    """Make sure STATE_DIR/tls holds a certificate for today's names and returns (cert, key).
    The certificate is reissued, with the same key, when the names change, when it expires
    within RENEW_WITHIN_DAYS, or when it doesn't match the key."""
    key = _load_or_create_key()
    dns, ips = wanted_names(public_host)
    now = datetime.now(timezone.utc)
    cert = _load_cert()
    if (
        cert is not None
        and _spki(cert.public_key()) == _spki(key.public_key())
        and _covers(cert, dns, ips)
        and cert.not_valid_after_utc - now > timedelta(days=RENEW_WITHIN_DAYS)
    ):
        return cert_path(), key_path()

    public = (public_host or "").strip().lower().rstrip(".")
    common_name = (public if public in dns else (dns[1] if len(dns) > 1 else "localhost"))[:64]
    subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name), x509.NameAttribute(NameOID.ORGANIZATION_NAME, "The Den")])
    alt_names: list[x509.GeneralName] = [x509.DNSName(name) for name in dns]
    alt_names += [x509.IPAddress(ipaddress.ip_address(addr)) for addr in ips]
    cert = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=1))
        .not_valid_after(now + timedelta(days=VALID_DAYS))
        .add_extension(x509.SubjectAlternativeName(alt_names), critical=False)
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True, content_commitment=False, key_encipherment=False, data_encipherment=False,
                key_agreement=False, key_cert_sign=False, crl_sign=False, encipher_only=False, decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(key, hashes.SHA256())
    )
    _write_atomic(cert_path(), cert.public_bytes(serialization.Encoding.PEM), 0o644)
    log.info("TLS certificate issued for %s", ", ".join(dns + ips))
    return cert_path(), key_path()


def pin_for_certificate_der(der: bytes) -> str:
    """The pin for a DER-encoded certificate, computed the way the apps compute it: "sha256/" + standard
    padded base64 of SHA-256 over the certificate's SubjectPublicKeyInfo DER."""
    cert = x509.load_der_x509_certificate(der)
    return "sha256/" + base64.b64encode(hashlib.sha256(_spki(cert.public_key())).digest()).decode("ascii")


def certificate_expires_at() -> datetime | None:
    """When the current certificate expires (UTC), or None before one exists."""
    cert = _load_cert()
    return cert.not_valid_after_utc if cert is not None else None


def pin() -> str | None:
    """The pin the apps store: "sha256/" + base64 of SHA-256 over the certificate's public key.
    None while HTTPS is off or before a certificate exists."""
    global _pin_cache
    if not enabled():
        return None
    try:
        mtime = cert_path().stat().st_mtime
    except OSError:
        return None
    if _pin_cache is not None and _pin_cache[0] == mtime:
        return _pin_cache[1]
    cert = _load_cert()
    if cert is None:
        return None
    value = "sha256/" + base64.b64encode(hashlib.sha256(_spki(cert.public_key())).digest()).decode("ascii")
    _pin_cache = (mtime, value)
    return value


def txt_properties() -> dict[str, str]:
    """Extra mDNS TXT entries: https ("1" or "0") and, while HTTPS is on, the key pin."""
    out = {"https": "1" if enabled() else "0"}
    value = pin()
    if value:
        out["pin"] = value
    return out
