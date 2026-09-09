"""Headless smoke test for CandidatesModel's request-sequence guard (the fix for
the review finding: a shared model instance across every item's Releases page had
no protection against a slow, superseded reply overwriting whatever's now on
screen). Uses a tiny fake backend instead of a real indexer/qBittorrent so it can
run standalone: item 1's /candidates reply is delayed past item 2's, and a grab
on item 1 is delayed past a load() for item 2, exercising both guards added to
src/models/candidates_model.py.
Run from src/: `python ../tests/check_candidates_model_race_guard.py`
"""

import json
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.candidates_model import CandidatesModel

PORT = 18687
BASE_URL = f"http://127.0.0.1:{PORT}"
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


class FakeBackendHandler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def do_GET(self):
        # /movies/1/candidates is slow (item superseded by the time it lands);
        # /movies/2/candidates is fast (the one that should end up on screen).
        if self.path == "/movies/1/candidates":
            threading.Event().wait(0.6)
            body = json.dumps([{"title": "Stale Item 1 Release", "download_url": "u1",
                                 "indexer_name": "X", "quality": "720p"}]).encode()
        elif self.path == "/movies/2/candidates":
            body = json.dumps([{"title": "Fresh Item 2 Release", "download_url": "u2",
                                 "indexer_name": "X", "quality": "1080p"}]).encode()
        else:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        # Grab on item 1 is slow -- by the time it returns, the model has already
        # load()'d item 2, so grabFinished(1, ...) should never reach a page whose
        # itemId is 2 (verified at the QML layer; here we just confirm the emitted
        # itemId still correctly identifies which item the grab was actually for).
        if self.path == "/movies/1/grab":
            threading.Event().wait(0.6)
        body = json.dumps({"ok": True}).encode()
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = ThreadingHTTPServer(("127.0.0.1", PORT), FakeBackendHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()

app = QCoreApplication(sys.argv)
model = CandidatesModel(lambda: BASE_URL, resource="movies")
grab_results = []


def step1_load_item1_then_item2() -> None:
    print("-- step 1: load(1) [slow], immediately followed by load(2) [fast] --")
    model.load(1)
    model.load(2)  # supersedes the in-flight load(1) before it returns
    QTimer.singleShot(1000, step2_verify_load_guard)


def step2_verify_load_guard() -> None:
    titles = [model.data(model.index(i), CandidatesModel.TitleRole) for i in range(model.rowCount())]
    print(f"model contents after both loads settled: {titles}")
    if titles != ["Fresh Item 2 Release"]:
        fail(f"expected only item 2's release to be showing, got {titles}")
    QTimer.singleShot(100, step3_grab_race)


def step3_grab_race() -> None:
    print("-- step 2: load(1), grab it [slow], then load(2) before the grab replies --")
    model.load(1)
    model.grab("u1", "Stale Item 1 Release")
    model.load(2)  # user navigated away from item 1 before its grab finished
    QTimer.singleShot(1000, step4_finish)


def on_grab_finished(item_id: int, ok: bool, message: str) -> None:
    grab_results.append((item_id, ok, message))
    print(f"grabFinished: itemId={item_id} ok={ok} message={message}")


def step4_finish() -> None:
    if len(grab_results) != 1 or grab_results[0][0] != 1:
        fail(f"expected exactly one grabFinished tagged itemId=1, got {grab_results}")
    # The QML layer is what actually drops this (itemId != page.itemId); this test
    # only confirms the model still reports the correct originating item id so that
    # filter has something correct to check against.
    print("-- done --")
    server.shutdown()
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


model.errorOccurred.connect(lambda msg: fail(f"errorOccurred: {msg}"))
model.grabFinished.connect(on_grab_finished)
QTimer.singleShot(0, step1_load_item1_then_item2)
sys.exit(app.exec())
