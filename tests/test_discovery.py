"""Offline checks for app/discovery.py: the server id file, the display name order, which addresses get advertised, and the DNS-SD instance name. No network needed. Run: python tests/test_discovery.py"""

import os
import socket
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, ".")

from app import config, discovery  # noqa: E402
import ifaddr  # noqa: E402


def test_server_id_is_created_once():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, "state")
        original = config.STATE_DIR
        config.STATE_DIR = state_dir
        try:
            id1 = discovery.server_id()
            assert len(id1) == 32 and all(c in "0123456789abcdef" for c in id1)
            id2 = discovery.server_id()
            assert id1 == id2
            path = os.path.join(state_dir, "server_id")
            assert os.path.exists(path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            assert content == id1
        finally:
            config.STATE_DIR = original


def test_server_id_replaces_a_bad_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        state_dir = os.path.join(tmpdir, "state")
        original = config.STATE_DIR
        config.STATE_DIR = state_dir
        try:
            os.makedirs(state_dir)
            bad_path = os.path.join(state_dir, "server_id")
            with open(bad_path, "w", encoding="utf-8") as f:
                f.write("not-an-id\n")
            id1 = discovery.server_id()
            assert len(id1) == 32 and all(c in "0123456789abcdef" for c in id1)
            assert id1 != "not-an-id"
            with open(bad_path, "r", encoding="utf-8") as f:
                content = f.read().strip()
            assert content == id1
        finally:
            config.STATE_DIR = original


def test_display_name_order():
    original = config.SERVER_NAME
    config.SERVER_NAME = "Env Name"
    try:
        s1 = SimpleNamespace(plex_server_name="Plex Box", plex_token="token", server_name="Setup Name")
        assert discovery.display_name(s1) == "Plex Box"
        s1_disconnected = SimpleNamespace(plex_server_name="Plex Box", plex_token=None, server_name="Setup Name")
        assert discovery.display_name(s1_disconnected) == "Setup Name"
        s2 = SimpleNamespace(plex_server_name=None, server_name="Setup Name")
        assert discovery.display_name(s2) == "Setup Name"
        s3 = SimpleNamespace(plex_server_name="  ", server_name=None)
        assert discovery.display_name(s3) == "Env Name"
    finally:
        config.SERVER_NAME = original
    s4 = SimpleNamespace(plex_server_name=None, server_name=None)
    assert discovery.display_name(s4) == socket.gethostname()


def test_loopback_is_not_advertised():
    for host in ("127.0.0.1", "localhost", "::1"):
        original = config.WEB_HOST
        config.WEB_HOST = host
        try:
            assert discovery.advertised_addresses() == []
        finally:
            config.WEB_HOST = original


def test_bind_all_advertises_lan_addresses():
    original = config.WEB_HOST
    config.WEB_HOST = "0.0.0.0"
    try:
        addresses = discovery.advertised_addresses()
        assert isinstance(addresses, list)
        for addr in addresses:
            assert not addr.startswith("127.")
        assert len(addresses) == len(set(addresses))
    finally:
        config.WEB_HOST = original


def test_specific_address():
    original = config.WEB_HOST
    config.WEB_HOST = "192.168.50.7"
    try:
        assert discovery.advertised_addresses() == ["192.168.50.7"]
    finally:
        config.WEB_HOST = original


def test_instance_name():
    assert discovery.instance_name("Liam's Den") == "Liam's Den._theden._tcp.local."
    assert discovery.instance_name("den.local  box") == "den local box._theden._tcp.local."
    assert discovery.instance_name("") == "The Den._theden._tcp.local."
    long_label = "é" * 60
    result = discovery.instance_name(long_label)
    label_part = result.replace("._theden._tcp.local.", "")
    assert len(label_part.encode("utf-8")) <= 63


def test_refresh_without_start_is_a_no_op():
    discovery.refresh(SimpleNamespace(plex_server_name="X", server_name=None))
    current = discovery.current()
    assert current["advertised"] is False


def test_advertised_addresses_skips_virtual_and_link_local():
    original_host = config.WEB_HOST
    original_get_adapters = ifaddr.get_adapters

    class FakeIP:
        def __init__(self, ip):
            self.ip = ip

    adapters = [
        SimpleNamespace(name="eth0", ips=[FakeIP("192.168.1.5"), FakeIP("169.254.3.4")]),
        SimpleNamespace(name="docker0", ips=[FakeIP("172.17.0.1")]),
        SimpleNamespace(name="br-1a2b", ips=[FakeIP("172.18.0.1")]),
        SimpleNamespace(name="tailscale0", ips=[FakeIP("100.64.0.9")]),
        SimpleNamespace(name="lo", ips=[FakeIP("127.0.0.1")]),
        SimpleNamespace(name="wlan0", ips=[FakeIP("192.168.1.5"), FakeIP("10.0.0.7")]),
    ]

    config.WEB_HOST = "0.0.0.0"
    ifaddr.get_adapters = lambda: adapters  # noqa: E402
    try:
        result = discovery.advertised_addresses()
        assert result == ["192.168.1.5", "10.0.0.7"]
    finally:
        config.WEB_HOST = original_host
        ifaddr.get_adapters = original_get_adapters


def test_server_id_fallback_when_state_dir_unwritable():
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name

    try:
        unwritable_parent = os.path.join(tmp_path, "sub")
        original_state = config.STATE_DIR
        original_fallback = discovery._fallback_id
        config.STATE_DIR = unwritable_parent
        discovery._fallback_id = None
        try:
            id1 = discovery.server_id()
            assert len(id1) == 32 and all(c in "0123456789abcdef" for c in id1)
            id2 = discovery.server_id()
            assert id1 == id2
        finally:
            config.STATE_DIR = original_state
            discovery._fallback_id = original_fallback
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"{len(tests)} checks passed")
