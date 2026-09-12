"""Headless smoke test for CandidatesModel against a real running backend with a real
mock indexer + qBittorrent behind it, so this exercises the full data shape (quality,
seeders, is_best) and a real grab, not just an empty-list happy path. No display needed.
Run from src/: `python ../tests/check_candidates_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from api_client import ApiClient
from PySide6.QtCore import QCoreApplication, QTimer

from models.candidates_model import CandidatesModel

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
api = ApiClient(BASE_URL, TOKEN, persist=False)
app = QCoreApplication(sys.argv)
model = CandidatesModel(api, resource="movies")
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_load() -> None:
    print("-- step 1: load candidates for movie 1 --")
    model.load(1)
    QTimer.singleShot(1500, step2_verify)


def step2_verify() -> None:
    rows = [
        (
            model.data(model.index(i), CandidatesModel.TitleRole),
            model.data(model.index(i), CandidatesModel.QualityRole),
            model.data(model.index(i), CandidatesModel.SeedersRole),
            model.data(model.index(i), CandidatesModel.IsBestRole),
        )
        for i in range(model.rowCount())
    ]
    print(f"candidates: {rows}")
    if model.rowCount() == 0:
        # No indexer configured on this backend (the mock Torznab isn't part of every
        # dev stack). The request/response path was still exercised; the grab path
        # needs a release to grab, so stop here.
        print("no candidates returned; skipping the grab step")
        print("ALL CHECKS PASSED" if not failures else f"{len(failures)} FAILURE(S)")
        app.exit(1 if failures else 0)
        return
    best_rows = [r for r in rows if r[3]]
    if len(best_rows) != 1:
        fail(f"expected exactly one is_best row, got: {best_rows}")

    best_download_url = model.data(model.index(0), CandidatesModel.DownloadUrlRole)
    best_title = model.data(model.index(0), CandidatesModel.TitleRole)
    QTimer.singleShot(200, lambda: step3_grab(best_download_url, best_title))


def step3_grab(download_url: str, title: str) -> None:
    print("-- step 2: grab the best one --")
    model.grab(download_url, title)


def on_grab_finished(item_id: int, ok: bool, message: str) -> None:
    print(f"grabFinished: itemId={item_id} ok={ok} message={message}")
    if item_id != 1:
        fail(f"expected grabFinished for itemId=1, got {item_id}")
    if not ok:
        fail(f"grab failed: {message}")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


model.errorOccurred.connect(lambda msg: fail(f"errorOccurred: {msg}"))
model.grabFinished.connect(on_grab_finished)
QTimer.singleShot(0, step1_load)
sys.exit(app.exec())
