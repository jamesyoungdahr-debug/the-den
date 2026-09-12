"""Headless smoke test for MovieListModel + MovieSearchResultsModel against the real
running backend. No display needed. Search is exercised for its request/response/
error-handling path only -- whether real TMDB data comes back depends on the
backend's configured TMDB_API_KEY, which this test doesn't control.
Run from src/: `python ../tests/check_movie_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from api_client import ApiClient
from PySide6.QtCore import QCoreApplication, QTimer

from models.movie_model import MovieListModel, MovieSearchResultsModel

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
api = ApiClient(BASE_URL, TOKEN, persist=False)
app = QCoreApplication(sys.argv)
library = MovieListModel(api)
search = MovieSearchResultsModel(api)
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def dump_library(label: str) -> None:
    rows = [
        (library.data(library.index(i), MovieListModel.TitleRole), library.data(library.index(i), MovieListModel.HasFileRole))
        for i in range(library.rowCount())
    ]
    print(f"{label}: {rows}")


def step1_initial_refresh() -> None:
    print("-- step 1: initial library refresh --")
    library.refresh()
    QTimer.singleShot(1000, step2_add)


def step2_add() -> None:
    dump_library("before add")
    print("-- step 2: add a movie directly (no TMDB dependency -- manual data) --")
    library.addMovie(999001, "Client Test Movie", "2020", "", "")
    QTimer.singleShot(1000, step3_verify_added)


def step3_verify_added() -> None:
    dump_library("after add")
    added = next(
        (library.data(library.index(i), MovieListModel.MovieIdRole) for i in range(library.rowCount())
         if library.data(library.index(i), MovieListModel.TitleRole) == "Client Test Movie"),
        None,
    )
    if added is None:
        fail("added movie not found after refresh")
        QTimer.singleShot(200, step5_search)
        return
    QTimer.singleShot(200, lambda: step4_delete(added))


def step4_delete(movie_id: int) -> None:
    print("-- step 3: delete it --")
    library.deleteMovie(movie_id)
    QTimer.singleShot(1000, lambda: step4b_verify_deleted(movie_id))


def step4b_verify_deleted(movie_id: int) -> None:
    dump_library("after delete")
    if any(library.data(library.index(i), MovieListModel.MovieIdRole) == movie_id for i in range(library.rowCount())):
        fail("deleted movie still present")
    QTimer.singleShot(200, step5_search)


def step5_search() -> None:
    print("-- step 4: search TMDB (exercising the request/response path only) --")
    search.searchFinishedOnce = False
    search.search("Inception")
    QTimer.singleShot(2000, step6_finish)


def step6_finish() -> None:
    rows = [search.data(search.index(i), MovieSearchResultsModel.TitleRole) for i in range(search.rowCount())]
    print(f"search results (may be empty if backend has no real TMDB key configured): {rows}")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


library.errorOccurred.connect(lambda msg: print(f"library errorOccurred (non-fatal for this test): {msg}"))
search.errorOccurred.connect(lambda msg: print(f"search errorOccurred (expected if no real TMDB key set): {msg}"))
QTimer.singleShot(0, step1_initial_refresh)
sys.exit(app.exec())
