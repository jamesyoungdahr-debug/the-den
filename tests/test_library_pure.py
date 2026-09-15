"""M50a/M50b checks that need no database: the title normaliser, the year window, the movie name parser and the folder walker. Run from the repo root: python tests/test_library_pure.py"""
import os, shutil, sys, tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.library_match import _close_year
from app.library_scan import SKIP_DIR_NAMES, VIDEO_EXTENSIONS, _norm, walk_videos
from app.parser import parse_movie

fails = []


def check(name, got, want):
    ok = got == want
    print(("  ok   " if ok else "  FAIL ") + name + ("" if ok else f"  got={got!r} want={want!r}"))
    if not ok:
        fails.append(name)


# ---- _norm ---------------------------------------------------------------------------

check("_norm lowercases", _norm("Blade Runner 2049"), "blade runner 2049")
check("_norm collapses punctuation", _norm("Spider-Man: No Way Home"), "spider man no way home")
check("_norm strips a trailing year bracket", _norm("The Matrix (1999)"), "the matrix 1999")
check("_norm of None", _norm(None), "")
check("_norm of empty", _norm(""), "")

# ---- _close_year ---------------------------------------------------------------------

check("year equal", _close_year(1999, 1999), True)
check("year off by one", _close_year(2000, 1999), True)
check("year off by one the other way", _close_year(1998, 1999), True)
check("year off by two", _close_year(2001, 1999), False)
check("candidate year unknown", _close_year(None, 1999), True)
check("wanted year unknown", _close_year(1999, None), True)
check("both years unknown", _close_year(None, None), True)

# ---- parse_movie ---------------------------------------------------------------------

check("parse_movie bracketed year", parse_movie("The Matrix (1999).mkv"), ("The Matrix", 1999))
check("parse_movie keeps a number in the title", parse_movie("Blade Runner 2049 (2017).mkv"), ("Blade Runner 2049", 2017))
check("parse_movie dotted year", parse_movie("The.Matrix.1999.mkv"), ("The Matrix", 1999))
check("parse_movie drops the release noise", parse_movie("The Matrix.1999.1080p.mkv"), ("The Matrix", 1999))
check("parse_movie without a year", parse_movie("The Matrix.mkv"), ("The Matrix", None))
check("parse_movie with no title", parse_movie("1999.mkv"), None)
check("parse_movie of empty", parse_movie(""), None)

# ---- walk_videos ---------------------------------------------------------------------

TMP = tempfile.mkdtemp(prefix="den-libpure-")
try:
    keep = [
        "Film (2020).mkv",
        os.path.join("Sub", "Other.mp4"),
        "Clip.webm",
    ]
    skip = [
        "notes.txt",
        ".hidden.mkv",
        os.path.join("Sample", "sample.mkv"),
        os.path.join("Proof", "proof.mkv"),
        os.path.join("Extras", "deleted.mkv"),
        os.path.join("Featurettes", "making-of.mkv"),
        os.path.join("Trailers", "trailer.mkv"),
    ]
    for rel in keep + skip:
        path = os.path.join(TMP, rel)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as handle:
            handle.write(b"x")

    found = {os.path.relpath(p, TMP) for p in walk_videos(TMP)}
    check("walk_videos keeps the video files", sorted(found), sorted(keep))
    check("walk_videos skips a non-video file", "notes.txt" in found, False)
    check("walk_videos skips a dot file", ".hidden.mkv" in found, False)
    check("walk_videos prunes a sample folder", os.path.join("Sample", "sample.mkv") in found, False)
    check("walk_videos prunes Proof", os.path.join("Proof", "proof.mkv") in found, False)
    check("walk_videos prunes Extras", os.path.join("Extras", "deleted.mkv") in found, False)
    check("walk_videos prunes Featurettes", os.path.join("Featurettes", "making-of.mkv") in found, False)
    check("walk_videos prunes Trailers", os.path.join("Trailers", "trailer.mkv") in found, False)

    check("walk_videos of a missing folder", walk_videos(os.path.join(TMP, "nope")), [])
    check("VIDEO_EXTENSIONS holds mkv", ".mkv" in VIDEO_EXTENSIONS, True)
    check("SKIP_DIR_NAMES holds sample", "sample" in SKIP_DIR_NAMES, True)
finally:
    shutil.rmtree(TMP, ignore_errors=True)

print(f"\n{len(fails)} FAILURE(S)" if fails else "\nall checks passed")
sys.exit(1 if fails else 0)
