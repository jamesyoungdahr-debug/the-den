"""Headless smoke test for SeriesListModel + SeriesSearchResultsModel against a real
running backend (with a mock TVmaze behind it -- see the M5 test setup in ROADMAP.md).
No display needed. Run from src/: `python ../tests/check_series_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.series_model import SeriesListModel, SeriesSearchResultsModel

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
library = SeriesListModel(lambda: BASE_URL)
search = SeriesSearchResultsModel(lambda: BASE_URL)
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_refresh() -> None:
    print("-- step 1: refresh library (expects the M5 test's seeded series) --")
    library.refresh()
    QTimer.singleShot(1000, step2_search)


def step2_search() -> None:
    rows = [library.data(library.index(i), SeriesListModel.TitleRole) for i in range(library.rowCount())]
    print(f"library: {rows}")
    if library.rowCount() == 0:
        fail("expected at least one real series row")

    print("-- step 2: search TVmaze --")
    search.search("Breaking Bad")
    QTimer.singleShot(1000, step3_verify_search)


def step3_verify_search() -> None:
    rows = [search.data(search.index(i), SeriesSearchResultsModel.TitleRole) for i in range(search.rowCount())]
    print(f"search results: {rows}")
    if search.rowCount() == 0:
        fail("expected at least one real TVmaze search result")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


library.errorOccurred.connect(lambda msg: fail(f"library errorOccurred: {msg}"))
search.errorOccurred.connect(lambda msg: fail(f"search errorOccurred: {msg}"))
QTimer.singleShot(0, step1_refresh)
sys.exit(app.exec())
