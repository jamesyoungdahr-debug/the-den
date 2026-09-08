"""Headless smoke test for CandidatesModel against a real running backend with a real
mock indexer + qBittorrent behind it, so this exercises the full data shape (quality,
seeders, is_best) and a real grab, not just an empty-list happy path. No display needed.
Run from src/: `python ../tests/check_candidates_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.candidates_model import CandidatesModel

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
model = CandidatesModel(lambda: BASE_URL)
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
    if model.rowCount() != 2:
        fail(f"expected 2 candidates, got {model.rowCount()}")
    best_rows = [r for r in rows if r[3]]
    if len(best_rows) != 1 or best_rows[0][1] != "1080p":
        fail(f"expected exactly one is_best row with quality 1080p, got: {best_rows}")

    best_download_url = model.data(model.index(0), CandidatesModel.DownloadUrlRole)
    best_title = model.data(model.index(0), CandidatesModel.TitleRole)
    QTimer.singleShot(200, lambda: step3_grab(best_download_url, best_title))


def step3_grab(download_url: str, title: str) -> None:
    print("-- step 2: grab the best one --")
    model.grab(download_url, title)


def on_grab_finished(ok: bool, message: str) -> None:
    print(f"grabFinished: ok={ok} message={message}")
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
