"""M49 check with the real ffmpeg: generate small test files, probe them, and extract an embedded subtitle.

Run on a machine with ffmpeg and ffprobe on PATH (the holtos-test VM), from the repo root, with the server's Python:
    python tests/vm_media_check.py
Offline: the test media come from ffmpeg's own lavfi sources. Everything lives in a temporary folder that is removed at the end."""

import os, re, subprocess, sys, tempfile, shutil, time
from datetime import datetime, timezone

REPO = os.getcwd()
sys.path.insert(0, REPO)

TMP = tempfile.mkdtemp(prefix="den-m49-vm-")
os.environ["STATE_DIR"] = os.path.join(TMP, "state")
os.environ["MOVIES_ROOT"] = os.path.join(TMP, "no-movies")
os.environ["TV_ROOT"] = os.path.join(TMP, "no-tv")
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "unused.db")

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.db import Base
from app import media_probe, media_stream, playability, subtitle_tracks
from app.models import MediaFile, MediaProbe, Movie, RootFolder


failures = []


def check(name, got, want):
    if got == want:
        print(f"  ok   {name}")
    else:
        msg = f"  FAIL {name}  got={got!r} want={want!r}"
        print(msg)
        failures.append(msg)


def run(cmd):
    # stdin closed: under `ssh ... 'bash -s' <<EOF` ffmpeg would otherwise read the rest of the script
    return subprocess.run(cmd, capture_output=True, timeout=300, stdin=subprocess.DEVNULL)


def main():
    # Step 1: Check ffmpeg/ffprobe availability
    ffmpeg = media_probe.ffmpeg_path()
    ffprobe = media_probe.ffprobe_path()
    if not ffmpeg or not ffprobe:
        print("ffmpeg and ffprobe must be on PATH")
        sys.exit(2)

    ver_out = run([ffprobe, "-version"]).stdout.decode(errors="replace").splitlines()
    print(ver_out[0] if ver_out else "no version output")

    encoders = run([ffmpeg, "-hide_banner", "-encoders"]).stdout.decode(errors="replace")
    has_x264 = "libx264" in encoders
    has_x265 = "libx265" in encoders
    if not has_x264:
        print("libx264 encoder not available, cannot run tests")
        sys.exit(2)

    # Step 2: Generate test media
    MEDIA = os.path.join(TMP, "media")
    os.makedirs(MEDIA, exist_ok=True)

    SRT = os.path.join(MEDIA, "subs.srt")
    with open(SRT, "w") as f:
        f.write("1\n00:00:01,000 --> 00:00:05,000\nHello from the VM\n\n2\n00:00:06,000 --> 00:00:09,000\nSecond cue\n")

    base = [
        ffmpeg, "-v", "error", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=640x360:rate=24",
        "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000",
        "-i", SRT,
        "-t", "90",
        "-map", "0:v", "-map", "1:a", "-map", "2:s",
        "-metadata:s:a:0", "language=eng",
        "-metadata:s:s:0", "language=eng",
    ]

    # MP4
    mp4_dir = os.path.join(MEDIA, "Real (2026)")
    os.makedirs(mp4_dir, exist_ok=True)
    MP4 = os.path.join(mp4_dir, "Real (2026).mp4")
    r = run(base + ["-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "mov_text", MP4])
    check("generate mp4", r.returncode, 0)
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace"))

    # MKV
    mkv_dir = os.path.join(MEDIA, "Real Mkv (2026)")
    os.makedirs(mkv_dir, exist_ok=True)
    MKV = os.path.join(mkv_dir, "Real Mkv (2026).mkv")
    r = run(base + ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-c:s", "srt", MKV])
    check("generate mkv", r.returncode, 0)
    if r.returncode != 0:
        print(r.stderr.decode(errors="replace"))

    # HEVC (only if libx265 available)
    hevc_dir = os.path.join(MEDIA, "Hevc (2026)")
    os.makedirs(hevc_dir, exist_ok=True)
    HEVC = os.path.join(hevc_dir, "Hevc (2026).mkv")
    hevc_generated = False
    if has_x265:
        r = run(base + ["-c:v", "libx265", "-pix_fmt", "yuv420p10le", "-c:a", "aac", "-c:s", "srt", HEVC])
        check("generate hevc", r.returncode, 0)
        if r.returncode != 0:
            print(r.stderr.decode(errors="replace"))
        else:
            hevc_generated = True

    # Step 3: Set up database and models
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    root = RootFolder(name="VM", media_type="movie", path=MEDIA, is_default=True)
    db.add(root)

    mp4_movie = Movie(tmdb_id=1, title="Real", has_file=True, file_path=MP4, file_score=0)
    mkv_movie = Movie(tmdb_id=2, title="Real Mkv", has_file=True, file_path=MKV, file_score=0)
    db.add(mp4_movie)
    db.add(mkv_movie)

    hevc_movie = None
    if hevc_generated:
        hevc_movie = Movie(tmdb_id=3, title="Hevc", has_file=True, file_path=HEVC, file_score=0)
        db.add(hevc_movie)

    db.commit()

    # M50a: playback resolves media_files rows, so record what the scan would have found.
    stamp = datetime.now(timezone.utc)
    files = [
        MediaFile(media_type="movie", movie_id=mp4_movie.id, path=MP4, matched=True, added_at=stamp, last_seen_at=stamp),
        MediaFile(media_type="movie", movie_id=mkv_movie.id, path=MKV, matched=True, added_at=stamp, last_seen_at=stamp),
    ]
    if hevc_movie is not None:
        files.append(MediaFile(media_type="movie", movie_id=hevc_movie.id, path=HEVC, matched=True, added_at=stamp, last_seen_at=stamp))
    db.add_all(files)
    db.commit()

    # Step 4: MP4 checks
    try:
        lf = media_stream.resolve_item_file(db, "movie", mp4_movie.id)
        s = media_probe.probe(db, lf.path)

        check("mp4 probed", s is not None, True)
        if s is None:
            print("  (skipping remaining MP4 checks)")
        else:
            check("mp4 container", "mp4" in s["container"], True)
            check("mp4 video codec", s["video"]["codec"], "h264")
            check("mp4 video profile", s["video"]["profile"], "High")
            check("mp4 level is a number", isinstance(s["video"]["level"], int) and s["video"]["level"] > 0, True)
            check("mp4 duration about 90 s", 89000 <= s["duration_ms"] <= 91000, True)
            check("mp4 audio aac", s["audio"][0]["codec"], "aac")
            check("mp4 audio language", s["audio"][0]["language"], "eng")
            check("mp4 subtitle mov_text", s["subtitles"][0]["codec"], "mov_text")
            check("mp4 subtitle is text", s["subtitles"][0]["kind"], "text")

            bt = playability.browser_type(s, ".mp4")
            print(f"  browser type: {bt}")
            check("mp4 browser type", bool(re.fullmatch(r'video/mp4; codecs="avc1\.6400[0-9A-F]{2},mp4a\.40\.2"', bt)), True)

            check("mp4 plays directly", playability.direct_play_notes(s), [])

            # Cache
            rows_before = db.query(MediaProbe).count()
            s2 = media_probe.probe(db, lf.path)
            check("probe cache hit", s2 == s, True)
            check("one cache row", db.query(MediaProbe).count(), rows_before)

            # Touch
            st = os.stat(MP4)
            os.utime(MP4, ns=(st.st_atime_ns, st.st_mtime_ns + 5_000_000_000))
            media_probe.probe(db, lf.path)
            row = db.query(MediaProbe).filter(MediaProbe.file_path == lf.path).one()
            db.refresh(row)
            check("cache refreshed after the file changed", row.mtime_ns, st.st_mtime_ns + 5_000_000_000)

    except Exception as exc:
        msg = f"step 4 crashed: {exc}"
        print(f"  FAIL {msg}")
        failures.append(msg)

    # Step 5: MKV checks
    try:
        lf = media_stream.resolve_item_file(db, "movie", mkv_movie.id)
        s = media_probe.probe(db, lf.path)

        check("mkv subtitle subrip", s["subtitles"][0]["codec"], "subrip")

        playable, unavailable = subtitle_tracks.embedded_track_lists(s)
        check("mkv one embedded text track", len(playable), 1)
        track_id = playable[0]["id"]

        t0 = time.time()
        vtt = subtitle_tracks.webvtt_for_embedded(lf, s, track_id)
        print(f"  extraction took {time.time() - t0:.3f} seconds")

        check("extracted WebVTT header", vtt.startswith("WEBVTT"), True)
        check("extracted cue text", "Hello from the VM" in vtt, True)

        index = int(track_id[1:])
        check("subtitle cached", media_stream.subtitle_cache_path(lf, index).is_file(), True)

        check("cached copy returned", subtitle_tracks.webvtt_for_embedded(lf, s, track_id), vtt)

        bad = None
        try:
            subtitle_tracks.webvtt_for_embedded(lf, s, "e99")
        except HTTPException as exc:
            bad = exc.status_code
        check("unknown embedded track 404", bad, 404)

        check("mkv browser type", playability.browser_type(s, ".mkv").startswith('video/x-matroska; codecs="avc1.'), True)

    except Exception as exc:
        msg = f"step 5 crashed: {exc}"
        print(f"  FAIL {msg}")
        failures.append(msg)

    # Step 6: HEVC checks (only if generated)
    try:
        if hevc_generated and hevc_movie is not None:
            lf = media_stream.resolve_item_file(db, "movie", hevc_movie.id)
            s = media_probe.probe(db, lf.path)

            check("hevc codec", s["video"]["codec"], "hevc")
            check("hevc profile", s["video"]["profile"], "Main 10")
            check("hevc bit depth", s["video"]["bit_depth"], 10)
            check("hevc codec string", (playability.video_codec_string(s["video"]) or "").startswith("hvc1.2.4.L"), True)
            notes = playability.direct_play_notes(s)
            check("hevc note", "HEVC video plays only in browsers with hardware HEVC decoding." in notes, True)
        else:
            print("libx265 not available, HEVC checks skipped")

    except Exception as exc:
        msg = f"step 6 crashed: {exc}"
        print(f"  FAIL {msg}")
        failures.append(msg)

    # Cleanup
    shutil.rmtree(TMP, ignore_errors=True)

    # Summary
    if failures:
        print(f"\n{len(failures)} failure(s):")
        for f in failures:
            print(f"  - {f}")
    else:
        print("\nAll checks passed.")

    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
