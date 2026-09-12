"""Headless smoke test for EpisodesModel and the episode-resource CandidatesModel
against a real running backend (see the M5 test setup in ROADMAP.md: a series with 4
episodes across 2 seasons, one already grabbed). No display needed.
Run from src/: `python ../tests/check_episodes_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import os

from api_client import ApiClient
from PySide6.QtCore import QCoreApplication, QTimer

from models.candidates_model import CandidatesModel
from models.episodes_model import EpisodesModel

BASE_URL = os.environ.get("DEN_URL", "http://127.0.0.1:8686")
TOKEN = os.environ.get("DEN_API_TOKEN", "")
api = ApiClient(BASE_URL, TOKEN, persist=False)
app = QCoreApplication(sys.argv)
episodes = EpisodesModel(api)
candidates = CandidatesModel(api, resource="episodes")
failures = []


def fail(msg: str) -> None:
    failures.append(msg)
    print(f"FAIL: {msg}")


def step1_load_episodes() -> None:
    print("-- step 1: load episodes for series 1 --")
    episodes.load(1)
    QTimer.singleShot(1000, step2_verify)


def step2_verify() -> None:
    rows = [
        (
            episodes.data(episodes.index(i), EpisodesModel.SeasonNumberRole),
            episodes.data(episodes.index(i), EpisodesModel.EpisodeNumberRole),
            episodes.data(episodes.index(i), EpisodesModel.HasFileRole),
        )
        for i in range(episodes.rowCount())
    ]
    print(f"episodes: {rows}")
    if episodes.rowCount() == 0:
        fail("expected series 1 to have episodes")
    if episodes.haveCount != sum(1 for r in rows if r[2]):
        fail(f"haveCount {episodes.haveCount} disagrees with the rows")

    print("-- step 2: load candidates for the first episode --")
    first_id = episodes.data(episodes.index(0), EpisodesModel.EpisodeIdRole)
    candidates.load(first_id)
    QTimer.singleShot(1000, step3_verify_candidates)


def step3_verify_candidates() -> None:
    rows = [
        (
            candidates.data(candidates.index(i), CandidatesModel.QualityRole),
            candidates.data(candidates.index(i), CandidatesModel.IsBestRole),
        )
        for i in range(candidates.rowCount())
    ]
    print(f"candidates: {rows} (may be empty without a configured indexer)")
    print("-- done --")
    if failures:
        print(f"{len(failures)} FAILURE(S)")
        sys.exit(1)
    print("ALL CHECKS PASSED")
    app.quit()


episodes.errorOccurred.connect(lambda msg: fail(f"episodes errorOccurred: {msg}"))
candidates.errorOccurred.connect(lambda msg: fail(f"candidates errorOccurred: {msg}"))
QTimer.singleShot(0, step1_load_episodes)
sys.exit(app.exec())
