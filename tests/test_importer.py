"""Offline checks for app/importer.py: Plex-style names and the hard-link import into a
temp library. Run: python tests/test_importer.py"""

import os
import sys
import tempfile
from types import SimpleNamespace

sys.path.insert(0, ".")

from app import importer  # noqa: E402


def _write(tmpdir: str, name: str, size: int) -> str:
    path = os.path.join(tmpdir, "downloads", name)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(b"x" * size)
    return path


def test_movie_name():
    assert importer.movie_name(SimpleNamespace(title="Blade Runner", year=1982)) == "Blade Runner (1982)"
    assert importer.movie_name(SimpleNamespace(title="Blade Runner", year=None)) == "Blade Runner"
    assert importer.movie_name(SimpleNamespace(title="A: B/C", year=2000)) == "A BC (2000)"


def test_episode_name():
    series = SimpleNamespace(title="Reacher")
    episode = SimpleNamespace(season_number=1, episode_number=2, title="Pilot")
    assert importer.episode_name(series, episode) == "Reacher - S01E02 - Pilot"
    episode.title = None
    assert importer.episode_name(series, episode) == "Reacher - S01E02"


def test_import_movie():
    with tempfile.TemporaryDirectory() as tmpdir:
        movies_root = os.path.join(tmpdir, "movies")
        os.makedirs(movies_root)
        file1 = _write(tmpdir, "Some.Movie.2020.1080p.mkv", 100)
        file2 = _write(tmpdir, "sample.mkv", 10)
        files = [SimpleNamespace(path=file1, size=100, downloaded=True), SimpleNamespace(path=file2, size=10, downloaded=True)]
        assert importer.import_movie(files, SimpleNamespace(title="Some Movie", year=2020), movies_root)
        dest = os.path.join(movies_root, "Some Movie (2020)", "Some Movie (2020).mkv")
        assert os.path.exists(dest)
        assert os.stat(dest).st_size == 100
        with open(dest, "rb") as f:
            dest_content = f.read()
        with open(file1, "rb") as f:
            source_content = f.read()
        assert dest_content == source_content or os.stat(dest).st_nlink == 2
        assert importer.import_movie(files, SimpleNamespace(title="Some Movie", year=2020), movies_root)


def test_import_episode():
    with tempfile.TemporaryDirectory() as tmpdir:
        tv_root = os.path.join(tmpdir, "tv")
        os.makedirs(tv_root)
        series = SimpleNamespace(title="Reacher")
        episode = SimpleNamespace(season_number=1, episode_number=2, title="Pilot")
        file1 = _write(tmpdir, "Reacher - S01E02 - Pilot.mkv", 10)
        files = [SimpleNamespace(path=file1, size=10, downloaded=True)]
        assert importer.import_episode(files, series, episode, tv_root)
        dest = os.path.join(tv_root, "Reacher", "Season 01", "Reacher - S01E02 - Pilot.mkv")
        assert os.path.exists(dest)


def test_no_video_file():
    with tempfile.TemporaryDirectory() as tmpdir:
        movies_root = os.path.join(tmpdir, "movies")
        os.makedirs(movies_root)
        files = [SimpleNamespace(path=os.path.join(tmpdir, "downloads", "sample.nfo"), size=10, downloaded=True)]
        assert not importer.import_movie(files, SimpleNamespace(title="Some Movie", year=2020), movies_root)


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    for t in tests:
        t()
    print(f"{len(tests)} checks passed")
