"""M49 checks with a temporary database and folders: the library path guard, sidecars, byte ranges and playback state rules. Linux only (uses symlinks). Run from the repo root."""
import os, sys, tempfile, shutil

TMP = tempfile.mkdtemp(prefix="den-m49-")
os.environ["STATE_DIR"] = os.path.join(TMP, "state")
os.environ["MOVIES_ROOT"] = os.path.join(TMP, "no-movies-root")   # does not exist
os.environ["TV_ROOT"] = os.path.join(TMP, "no-tv-root")           # does not exist
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "unused.db")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pathlib import Path
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app import media_stream, playback
from app.models import Episode, Movie, PlaybackState, RootFolder, Series

engine = create_engine("sqlite://")
Base.metadata.create_all(engine)
db = sessionmaker(bind=engine)()

fails = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        fails.append(name)


def status_of(fn):
    try:
        fn()
        return "ok"
    except HTTPException as exc:
        return exc.status_code
    except Exception:
        raise


def write(path, data=b"x"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "wb") as f:
        f.write(data)


# =============================================================================
# Section 1: is_inside
# =============================================================================

ROOT = os.path.join(TMP, "media")
OUT = os.path.join(TMP, "outside")
EVIL = os.path.join(TMP, "media-evil")
os.makedirs(ROOT, exist_ok=True)
os.makedirs(OUT, exist_ok=True)
os.makedirs(EVIL, exist_ok=True)

check("is_inside ROOT/a.mkv", media_stream.is_inside(os.path.join(ROOT, "a.mkv"), [os.path.realpath(ROOT)]), True)
check("is_inside ROOT itself", media_stream.is_inside(ROOT, [os.path.realpath(ROOT)]), True)
check("is_inside EVIL/a.mkv", media_stream.is_inside(os.path.join(EVIL, "a.mkv"), [os.path.realpath(ROOT)]), False)
check("is_inside OUT/a.mkv", media_stream.is_inside(os.path.join(OUT, "a.mkv"), [os.path.realpath(ROOT)]), False)
check("is_inside ROOT/../outside/a.mkv", media_stream.is_inside(os.path.join(ROOT, "..", "outside", "a.mkv"), [os.path.realpath(ROOT)]), False)

# =============================================================================
# Section 2: resolve_item_file
# =============================================================================

film_dir = os.path.join(ROOT, "Film (2020)")
film_path = os.path.join(film_dir, "Film (2020).mkv")
escape_path = os.path.join(OUT, "Escape.mkv")
notes_path = os.path.join(ROOT, "notes.txt")
link_path = os.path.join(ROOT, "Link (2020).mkv")

# Create the main film file: bytes of range(256) repeated 40 times = 10240 bytes
film_data = bytes(range(256)) * 40
write(film_path, film_data)
write(escape_path)
write(notes_path)

# Create symlink that escapes the library
os.symlink(escape_path, link_path)

# Create movies in DB
m_ok = Movie(tmdb_id=1, file_path=film_path, has_file=True, title="T1")
m_out = Movie(tmdb_id=2, file_path=escape_path, has_file=True, title="T2")
m_rel = Movie(tmdb_id=3, file_path="relative/Film.mkv", has_file=True, title="T3")
m_txt = Movie(tmdb_id=4, file_path=notes_path, has_file=True, title="T4")
m_nofile = Movie(tmdb_id=5, file_path=film_path, has_file=False, title="T5")
m_link = Movie(tmdb_id=6, file_path=link_path, has_file=True, title="T6")
m_missing = Movie(tmdb_id=7, file_path=os.path.join(ROOT, "Gone.mkv"), has_file=True, title="T7")

for m in [m_ok, m_out, m_rel, m_txt, m_nofile, m_link, m_missing]:
    db.add(m)
db.commit()

# First: no RootFolder rows -> nothing plays
check("resolve m_ok with no RootFolders", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_ok.id)), 404)

# Add a RootFolder
rf = RootFolder(name="Media", media_type="movie", path=ROOT, is_default=True)
db.add(rf)
db.commit()

lf_ok = media_stream.resolve_item_file(db, "movie", m_ok.id)
check("resolve m_ok path == realpath", lf_ok.path, os.path.realpath(film_path))
check("resolve m_ok content_type", lf_ok.content_type, "video/x-matroska")

check("resolve m_out (outside)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_out.id)), 404)
check("resolve m_rel (relative path)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_rel.id)), 404)
check("resolve m_txt (.txt not video)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_txt.id)), 404)
check("resolve m_nofile (has_file False)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_nofile.id)), 404)
check("resolve m_link (symlink escape)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_link.id)), 404)
check("resolve m_missing (file gone)", status_of(lambda: media_stream.resolve_item_file(db, "movie", m_missing.id)), 404)
check("resolve kind series", status_of(lambda: media_stream.resolve_item_file(db, "series", m_ok.id)), 404)
check("resolve unknown id 9999", status_of(lambda: media_stream.resolve_item_file(db, "movie", 9999)), 404)

# =============================================================================
# Section 3: sidecars
# =============================================================================

srt_en = os.path.join(film_dir, "Film (2020).en.srt")
srt_forced = os.path.join(film_dir, "Film (2020).en.forced.srt")
srt_other = os.path.join(film_dir, "Other.en.srt")
secret_srt = os.path.join(OUT, "secret.srt")
srt_de_link = os.path.join(film_dir, "Film (2020).de.srt")

write(secret_srt)  # target for symlink escape
os.symlink(secret_srt, srt_de_link)

# Write actual subtitle content to the .en.srt file
sub_bytes = b"1\n00:00:01,000 --> 00:00:02,000\nHi\n"
write(srt_en, sub_bytes)
write(srt_forced)
write(srt_other)

lf = media_stream.resolve_item_file(db, "movie", m_ok.id)
tracks = media_stream.sidecar_tracks(lf)

# Sorted by file name: "Film (2020).en.forced.srt" comes before "Film (2020).en.srt".
check("sidecar tails", [t["tail"] for t in tracks], ["en.forced", "en"])
check("sidecar ids", [t["id"] for t in tracks], ["x0", "x1"])

resolved = media_stream.resolve_sidecar(lf, "x1")
check("resolve_sidecar x1 tail", resolved["tail"], "en")

check("resolve_sidecar x9 (missing)", status_of(lambda: media_stream.resolve_sidecar(lf, "x9")), 404)

read_bytes = media_stream.read_sidecar_bytes(tracks[1])
check("read_sidecar_bytes matches written", read_bytes, sub_bytes)

cache_path = media_stream.subtitle_cache_path(lf, 3)
check("subtitle_cache_path name regex", bool(re.match(r"^[0-9a-f]{64}\.vtt$", cache_path.name)), True)
expected_parent = Path(os.environ["STATE_DIR"]) / "media-cache" / "subtitles"
check("subtitle_cache_path parent", cache_path.parent, expected_parent)
check("subtitle_cache_path folder exists", os.path.isdir(str(cache_path.parent)), True)

# =============================================================================
# Section 4: parse_range
# =============================================================================

def _parse(header):
    return media_stream.parse_range(header, 1000)

check("parse_range None -> None", _parse(None), None)
check("parse_range bytes=0-99", _parse("bytes=0-99"), (0, 99))
check("parse_range bytes=900-", _parse("bytes=900-"), (900, 999))
check("parse_range bytes=-100", _parse("bytes=-100"), (900, 999))
check("parse_range bytes=-5000", _parse("bytes=-5000"), (0, 999))
check("parse_range bytes=990-2000", _parse("bytes=990-2000"), (990, 999))
check("parse_range bytes=5-2 (invalid)", _parse("bytes=5-2"), None)
check("parse_range multi-range ignored", _parse("bytes=0-1,5-6"), None)
check("parse_range wrong unit", _parse("items=0-1"), None)
check("parse_range bad syntax", _parse("bytes=abc"), None)

# Raising cases
def _raises(header):
    try:
        media_stream.parse_range(header, 1000)
        return False
    except media_stream.RangeNotSatisfiable:
        return True

check("parse_range bytes=1000- raises", _raises("bytes=1000-"), True)
check("parse_range bytes=-0 raises (size 1000)", _raises("bytes=-0"), True)

# For the size=0 case, check it raises RangeNotSatisfiable
def _raises_zero():
    try:
        media_stream.parse_range("bytes=0-", 0)
        return False
    except media_stream.RangeNotSatisfiable:
        return True

check("parse_range bytes=0- size 0 raises", _raises_zero(), True)
# Over-long numbers are ignored instead of reaching int() and Python's 4300-digit limit (a 500 before the fix).
check("parse_range 19-digit start ignored", _parse("bytes=" + "9" * 19 + "-"), None)
check("parse_range 5000-digit start ignored", _parse("bytes=" + "9" * 5000 + "-"), None)

# =============================================================================
# Section 5: file_response through TestClient
# =============================================================================

app = FastAPI()
LF = media_stream.resolve_item_file(db, "movie", m_ok.id)

@app.api_route("/f", methods=["GET", "HEAD"])
def serve(request: Request):
    return media_stream.file_response(request, LF)

client = TestClient(app)
DATA = film_data  # the Film bytes (10240 bytes)

# GET no Range
r = client.get("/f")
check("file_response GET status", r.status_code, 200)
check("file_response GET content", r.content, DATA)
check("file_response accept-ranges", r.headers["accept-ranges"], "bytes")
check("file_response content-length", r.headers["content-length"], "10240")

# Range bytes=0-99
r = client.get("/f", headers={"Range": "bytes=0-99"})
check("range 0-99 status", r.status_code, 206)
check("range 0-99 content", r.content, DATA[0:100])
check("range 0-99 content-range", r.headers["content-range"], "bytes 0-99/10240")

# Range bytes=-10
r = client.get("/f", headers={"Range": "bytes=-10"})
check("range -10 status", r.status_code, 206)
check("range -10 content", r.content, DATA[-10:])

# Range bytes=10240- (unsatisfiable)
r = client.get("/f", headers={"Range": "bytes=10240-"})
check("range 10240- status", r.status_code, 416)
check("range 10240- content-range", r.headers["content-range"], "bytes */10240")

# HEAD
r = client.head("/f")
check("HEAD status", r.status_code, 200)
check("HEAD content-length", r.headers["content-length"], "10240")
check("HEAD content empty", r.content, b"")

# If-Range with wrong etag -> full response
r_first = client.get("/f")
etag = r_first.headers["etag"]
r = client.get("/f", headers={"Range": "bytes=0-9", "If-Range": '"wrong"'})
check("if-range wrong status", r.status_code, 200)
check("if-range wrong content length", len(r.content), 10240)

# If-Range with correct etag -> ranged response
r = client.get("/f", headers={"Range": "bytes=0-9", "If-Range": etag})
check("if-range correct status", r.status_code, 206)
check("if-range correct content length", len(r.content), 10)

# Range bytes=2000-12000 (clamped end)
r = client.get("/f", headers={"Range": "bytes=2000-12000"})
check("range 2000-12000 status", r.status_code, 206)
check("range 2000-12000 content", r.content, DATA[2000:])
check("range 2000-12000 content-range", r.headers["content-range"], "bytes 2000-10239/10240")

# A file swapped after the check (different inode) is refused, not served (DeepSeek Pro review, 2026-09-15).
from dataclasses import replace as _replace
_SWAPPED = _replace(LF, inode=LF.inode + 1)


@app.get("/swapped")
def serve_swapped(request: Request):
    return media_stream.file_response(request, _SWAPPED)


check("file changed after the check is refused", client.get("/swapped").status_code, 404)

# =============================================================================
# Section 6: playback rules
# =============================================================================

H = 3_600_000

# Under a minute -> position_ms 0, played False
s = playback.record_progress(db, 1, "movie", m_ok.id, 30_000, H, "progress")
check("record 30s position_ms", s.position_ms, 0)
check("record 30s played", s.played, False)

# Over MIN_RESUME_MS -> stored
s = playback.record_progress(db, 1, "movie", m_ok.id, 1_200_000, H, "progress")
check("record 1200s position_ms", s.position_ms, 1_200_000)

# Past end (90%+) -> played True, play_count 1, position_ms 0
s = playback.record_progress(db, 1, "movie", m_ok.id, 5_000_000, H, "progress")
check("record past-end played", s.played, True)
check("record past-end play_count", s.play_count, 1)
check("record past-end position_ms", s.position_ms, 0)

# Stop event -> play_count stays 1
s = playback.record_progress(db, 1, "movie", m_ok.id, 3_400_000, H, "stop")
check("record stop play_count", s.play_count, 1)

# Duration 0 keeps the stored one; position updates
s = playback.record_progress(db, 1, "movie", m_ok.id, 1_000_000, 0, "progress")
check("duration 0 keeps duration_ms", s.duration_ms, H)
check("duration 0 position_ms", s.position_ms, 1_000_000)
check("duration 0 played stays True", s.played, True)

# set_watched False -> played False, position_ms 0
s = playback.set_watched(db, 1, "movie", m_ok.id, False)
check("set_watched False played", s.played, False)
check("set_watched False position_ms", s.position_ms, 0)

# set_watched True -> play_count increments (was 1, now 2)
s = playback.set_watched(db, 1, "movie", m_ok.id, True)
check("set_watched True play_count", s.play_count, 2)

# ValueError cases
def _raises_value_error(fn):
    try:
        fn()
        return False
    except ValueError:
        return True

check("record position -1 raises", _raises_value_error(lambda: playback.record_progress(db, 1, "movie", m_ok.id, -1, H, "progress")), True)
check("record position bool raises", _raises_value_error(lambda: playback.record_progress(db, 1, "movie", m_ok.id, True, H, "progress")), True)
check("record position nan raises", _raises_value_error(lambda: playback.record_progress(db, 1, "movie", m_ok.id, float("nan"), H, "progress")), True)
check("record event rewind raises", _raises_value_error(lambda: playback.record_progress(db, 1, "movie", m_ok.id, 0, H, "rewind")), True)
check("record kind series raises", _raises_value_error(lambda: playback.record_progress(db, 1, "series", m_ok.id, 0, H, "progress")), True)

# continue_watching
playback.record_progress(db, 1, "movie", m_ok.id, 1_500_000, H, "pause")
playback.record_progress(db, 1, "movie", m_nofile.id, 1_500_000, H, "pause")

items = playback.continue_watching(db, 1)
check("continue_watching items", [(i["kind"], i["id"]) for i in items], [("movie", m_ok.id)])
check("continue_watching href", items[0]["href"], f"/watch/movie/{m_ok.id}")
check("continue_watching progress", items[0]["progress"], round(1_500_000 / H, 3))

# states_for
states = playback.states_for(db, 1, "movie", [m_ok.id, 424242])
check("states_for keys", list(states.keys()), [m_ok.id])
check("states_for empty", playback.states_for(db, 1, "movie", []), {})

# next_episode
series = Series(tvmaze_id=1, title="S")
db.add(series)
db.commit()

e11 = Episode(series_id=series.id, season_number=1, episode_number=1, has_file=True)
e12 = Episode(series_id=series.id, season_number=1, episode_number=2, has_file=False)
e13 = Episode(series_id=series.id, season_number=1, episode_number=3, has_file=True)
e21 = Episode(series_id=series.id, season_number=2, episode_number=1, has_file=True)

for ep in [e11, e12, e13, e21]:
    db.add(ep)
db.commit()

check("next_episode e11 -> e13", playback.next_episode(db, e11).id, e13.id)
check("next_episode e13 -> e21", playback.next_episode(db, e13).id, e21.id)
check("next_episode e21 -> None", playback.next_episode(db, e21), None)

# forget_items
playback.record_progress(db, 2, "movie", m_ok.id, 1_500_000, H, "pause")
playback.forget_items(db, "movie", [m_ok.id])
db.commit()
count = db.query(PlaybackState).filter(
    PlaybackState.item_kind == "movie",
    PlaybackState.item_id == m_ok.id
).count()
check("forget_items count", count, 0)

# forget_user
playback.record_progress(db, 3, "episode", e11.id, 1_500_000, H, "pause")
playback.forget_user(db, 3)
db.commit()
count = db.query(PlaybackState).filter(PlaybackState.user_id == 3).count()
check("forget_user count", count, 0)

# =============================================================================
# Summary & cleanup
# =============================================================================

print(f"\n{len(fails)} FAILURE(S)" if fails else "\nall checks passed")

shutil.rmtree(TMP, ignore_errors=True)
sys.exit(1 if fails else 0)
