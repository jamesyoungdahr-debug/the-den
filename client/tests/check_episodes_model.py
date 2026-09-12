"""Headless smoke test for EpisodesModel and the episode-resource CandidatesModel
against a real running backend (see the M5 test setup in ROADMAP.md: a series with 4
episodes across 2 seasons, one already grabbed). No display needed.
Run from src/: `python ../tests/check_episodes_model.py`
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from PySide6.QtCore import QCoreApplication, QTimer

from models.candidates_model import CandidatesModel
from models.episodes_model import EpisodesModel

BASE_URL = "http://127.0.0.1:8686"
app = QCoreApplication(sys.argv)
episodes = EpisodesModel(lambda: BASE_URL)
candidates = CandidatesModel(lambda: BASE_URL, resource="episodes")
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
    if episodes.rowCount() != 4:
        fail(f"expected 4 episodes, got {episodes.rowCount()}")
    # Note: grabbing (done in the M5 curl setup) only queues a download -- has_file
    # only flips after /downloads/{id}/check actually imports it (that's M4's
    # concern). So all 4 episodes are correctly still has_file=false here.
    if any(r[2] for r in rows):
        fail(f"expected all episodes still has_file=false (none checked/imported yet), got: {rows}")

    print("-- step 2: load candidates for episode 2 (S01E02, still missing) --")
    candidates.load(2)
    QTimer.singleShot(1000, step3_verify_candidates)


def step3_verify_candidates() -> None:
    rows = [
        (
            candidates.data(candidates.index(i), CandidatesModel.QualityRole),
            candidates.data(candidates.index(i), CandidatesModel.IsBestRole),
        )
        for i in range(candidates.rowCount())
    ]
    print(f"candidates: {rows}")
    if candidates.rowCount() != 2:
        fail(f"expected 2 candidates, got {candidates.rowCount()}")
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
