"""Headless smoke test for CalendarMoviesModel + CalendarEpisodesModel against a real
running backend (a movie and a series with unimported episodes, both still missing).
No display needed. Run from src/: `python ../tests/check_calendar_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.calendar_model import CalendarEpisodesModel, CalendarMoviesModel

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
movies = CalendarMoviesModel(lambda: BASE_URL)
episodes = CalendarEpisodesModel(lambda: BASE_URL)
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_refresh() -> None:
    print("-- step 1: refresh both --")
    movies.refresh()
    episodes.refresh()
    QTimer.singleShot(1500, step2_verify)  # episodes does N+1 requests, give it longer


def step2_verify() -> None:
    movie_rows = [movies.data(movies.index(i), CalendarMoviesModel.TitleRole) for i in range(movies.rowCount())]
    print(f"missing movies: {movie_rows}")
    if movies.rowCount() == 0:
        fail("expected at least one missing movie")

    ep_rows = [
        (
            episodes.data(episodes.index(i), CalendarEpisodesModel.SeriesTitleRole),
            episodes.data(episodes.index(i), CalendarEpisodesModel.SeasonNumberRole),
            episodes.data(episodes.index(i), CalendarEpisodesModel.EpisodeNumberRole),
            episodes.data(episodes.index(i), CalendarEpisodesModel.AirDateRole),
        )
        for i in range(episodes.rowCount())
    ]
    print(f"missing episodes ({len(ep_rows)}): {ep_rows}")
    if episodes.rowCount() == 0:
        fail("expected at least one missing episode")
    # sorted by air_date ascending
    dates = [r[3] for r in ep_rows]
    if dates != sorted(dates):
        fail(f"expected episodes sorted by air_date, got: {dates}")

    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


movies.errorOccurred.connect(lambda msg: fail(f"movies errorOccurred: {msg}"))
episodes.errorOccurred.connect(lambda msg: fail(f"episodes errorOccurred: {msg}"))
QTimer.singleShot(0, step1_refresh)
sys.exit(app.exec())
