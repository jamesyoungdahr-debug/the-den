"""Headless smoke test for DownloadsModel against a real running backend with a real
download already in flight (see the M3 test setup this assumes: mock indexer + mock
qBittorrent behind the backend, a movie grabbed). Exercises both the success path
(check on a real download) and the error path (check on a nonexistent one) --
not just a clean load, per the M3 lesson (ROADMAP.md). No display needed.
Run from src/: `python ../tests/check_downloads_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.downloads_model import DownloadsModel

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
model = DownloadsModel(lambda: BASE_URL)
failures = []
saw_error = False


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def on_error(message: str) -> None:
    global saw_error
    saw_error = True
    print(f"errorOccurred (expected for step 3): {message}")


def step1_refresh() -> None:
    print("-- step 1: initial refresh (expects at least the M3 test's grabbed download) --")
    model.refresh()
    QTimer.singleShot(1000, step2_check_real)


def step2_check_real() -> None:
    rows = [
        (model.data(model.index(i), DownloadsModel.ReleaseTitleRole), model.data(model.index(i), DownloadsModel.StatusRole))
        for i in range(model.rowCount())
    ]
    print(f"downloads: {rows}")
    if model.rowCount() == 0:
        fail("expected at least one real download row (run the M3 grab test first, or grab something)")
        QTimer.singleShot(200, step3_check_nonexistent)
        return
    real_id = model.data(model.index(0), DownloadsModel.DownloadIdRole)
    print(f"-- step 2: check(download_id={real_id}) — exercises the success path --")
    model.check(real_id)
    QTimer.singleShot(1000, step3_check_nonexistent)


def step3_check_nonexistent() -> None:
    print("-- step 3: check(download_id=999999) — exercises the error path --")
    model.check(999999)
    QTimer.singleShot(1000, finish)


def finish() -> None:
    if not saw_error:
        fail("expected errorOccurred to fire for the nonexistent download id")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


model.errorOccurred.connect(on_error)
QTimer.singleShot(0, step1_refresh)
sys.exit(app.exec())
