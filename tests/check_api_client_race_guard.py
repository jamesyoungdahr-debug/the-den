"""Headless smoke test for ApiClient.checkHealth's request-sequence guard (the fix
for the review finding: clicking Connect twice in a row -- e.g. after fixing a
typo'd URL -- could have a stale, slower first reply overwrite a newer, correct
result). Points at two fake backends: a slow, failing one and a fast, healthy one.
Run from src/: `python ../tests/check_api_client_race_guard.py`
"""

import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from api_client import ApiClient

SLOW_PORT = 18688
FAST_PORT = 18689
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


class SlowFailingHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        threading.Event().wait(0.6)
        self.send_response(500)
        self.end_headers()


class FastHealthyHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        body = b'{"status":"ok"}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


slow_server = ThreadingHTTPServer(("127.0.0.1", SLOW_PORT), SlowFailingHandler)
fast_server = ThreadingHTTPServer(("127.0.0.1", FAST_PORT), FastHealthyHandler)
threading.Thread(target=slow_server.serve_forever, daemon=True).start()
threading.Thread(target=fast_server.serve_forever, daemon=True).start()

app = QCoreApplication(sys.argv)
client = ApiClient()


def step1_race() -> None:
    print("-- checkHealth() against a slow/failing URL, then immediately against a fast/healthy one --")
    client.baseUrl = f"http://127.0.0.1:{SLOW_PORT}"
    client.checkHealth()  # slow, will fail -- but its reply lands AFTER the one below
    client.baseUrl = f"http://127.0.0.1:{FAST_PORT}"
    client.checkHealth()  # fast, succeeds
    QTimer.singleShot(1000, step2_verify)


def step2_verify() -> None:
    print(f"final state: connected={client.connected} statusText={client.statusText!r}")
    if not client.connected:
        fail(f"expected connected=True (the newer, successful check), got False -- statusText={client.statusText!r}")
    if client.statusText != "Connected":
        fail(f"expected statusText='Connected', got {client.statusText!r}")
    print("-- done --")
    slow_server.shutdown()
    fast_server.shutdown()
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


QTimer.singleShot(0, step1_race)
sys.exit(app.exec())
