"""M49 live check: run `python -m app` against a temporary library and exercise the play API over HTTP.

Run in WSL from the repo root with the server venv: python tests/live_media.py <jpeg-folder> [--keep]
It makes a 90-second VP8 WebM from the JPEGs with Playwright's bundled ffmpeg (WSL has no system ffmpeg),
uses a fake ffprobe that returns fixture JSON, and signs in with the test admin token from
/root/the-den-test/e2e-token.txt (read, never printed). --keep leaves the server running for the browser check."""

import glob
import http.client
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time

# ---------------------------------------------------------------------------
# Constants (from environment with defaults)
# ---------------------------------------------------------------------------
REPO = os.getcwd()
sys.path.insert(0, REPO)  # the app package, when run as tests/live_media.py
WORK = os.environ.get("M49_WORK", "/root/m49-live")
PORT = int(os.environ.get("M49_PORT", "40292"))
GEN_FFMPEG = os.environ.get(
    "M49_GEN_FFMPEG", "/root/.cache/ms-playwright/ffmpeg-1011/ffmpeg-linux"
)
BASE_DB = os.environ.get("M49_BASE_DB", "/root/m36-mig/den.db")
TOKEN_FILE = "/root/the-den-test/e2e-token.txt"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
failures: list[str] = []


def check(name: str, got, want) -> None:
    if got == want:
        print(f"  ok   {name}")
    else:
        print(f"  FAIL {name}  got={got!r} want={want!r}")
        failures.append(name)


# ---------------------------------------------------------------------------
def main() -> None:
    # ---- 1. Args ----------------------------------------------------------
    if len(sys.argv) < 2:
        print("Usage: python tests/live_media.py <jpeg-folder> [--keep]")
        sys.exit(2)
    jpeg_folder = sys.argv[1]
    keep = "--keep" in sys.argv

    # ---- 2. Workspace -----------------------------------------------------
    shutil.rmtree(WORK, ignore_errors=True)
    MOVIES = os.path.join(WORK, "library", "movies")
    TV = os.path.join(WORK, "library", "tv")
    OUTSIDE = os.path.join(WORK, "outside")
    BIN = os.path.join(WORK, "bin")
    STATE = os.path.join(WORK, "state")

    for d in [MOVIES, TV, OUTSIDE, BIN, STATE]:
        os.makedirs(d, exist_ok=True)
    os.makedirs(os.path.join(MOVIES, "Clip (2026)"), exist_ok=True)
    os.makedirs(os.path.join(MOVIES, "Old Sample (1999)"), exist_ok=True)
    os.makedirs(os.path.join(TV, "Show", "Season 01"), exist_ok=True)

    # ---- 3. Generate clip -------------------------------------------------
    jpgs = sorted(
        glob.glob(os.path.join(jpeg_folder, "*.jpg"))
        + glob.glob(os.path.join(jpeg_folder, "*.jpeg"))
    )[:5]
    if not jpgs:
        print(f"No .jpg/.jpeg files found in {jpeg_folder}")
        sys.exit(2)

    CLIP = os.path.join(WORK, "clip.webm")
    # Playwright's ffmpeg build has no pipe protocol, so the JPEG stream goes through a file.
    frames_path = os.path.join(WORK, "frames.mjpeg")
    with open(frames_path, "wb") as f:
        f.write(b"".join(open(jpgs[i % len(jpgs)], "rb").read() for i in range(90)))

    result = subprocess.run(
        [
            GEN_FFMPEG, "-hide_banner", "-v", "error",
            "-f", "image2pipe", "-framerate", "1", "-c:v", "mjpeg",
            "-i", frames_path,
            "-vf", "scale=640:360,format=yuv420p",
            "-c:v", "libvpx", "-b:v", "400k",
            "-y", CLIP,
        ],
        capture_output=True,
        timeout=300,
    )
    if result.returncode != 0:
        print(f"ffmpeg failed:\n{result.stderr.decode(errors='replace')}")
        sys.exit(2)

    # Copy clip to library locations
    shutil.copy(CLIP, os.path.join(MOVIES, "Clip (2026)", "Clip (2026).webm"))
    shutil.copy(CLIP, os.path.join(MOVIES, "Old Sample (1999)", "Old Sample (1999).avi"))
    shutil.copy(CLIP, os.path.join(TV, "Show", "Season 01", "Show - S01E01.webm"))
    shutil.copy(CLIP, os.path.join(TV, "Show", "Season 01", "Show - S01E02.webm"))
    shutil.copy(CLIP, os.path.join(OUTSIDE, "Escape.webm"))

    # Write subtitle file
    srt_content = (
        "1\n"
        "00:00:01,000 --> 00:00:30,000\n"
        "Hello from The Den\n"
        "\n"
        "2\n"
        "00:00:31,000 --> 00:01:00,000\n"
        "Second line\n"
    )
    with open(os.path.join(MOVIES, "Clip (2026)", "Clip (2026).en.srt"), "w") as f:
        f.write(srt_content)

    # ---- 4. Fake ffprobe --------------------------------------------------
    probe_webm = {
        "format": {
            "format_name": "matroska,webm",
            "duration": "90.000000",
            "bit_rate": "400000",
        },
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "vp8",
                "width": 640,
                "height": 360,
                "pix_fmt": "yuv420p",
                "disposition": {"default": 1},
            }
        ],
        "chapters": [],
    }
    probe_avi = {
        "format": {
            "format_name": "avi",
            "duration": "90.000000",
        },
        "streams": [
            {
                "index": 0,
                "codec_type": "video",
                "codec_name": "mpeg4",
                "width": 640,
                "height": 360,
                "pix_fmt": "yuv420p",
            },
            {
                "index": 1,
                "codec_type": "audio",
                "codec_name": "mp3",
                "channels": 2,
                "disposition": {"default": 1},
            },
        ],
        "chapters": [],
    }

    with open(os.path.join(WORK, "probe-webm.json"), "w") as f:
        json.dump(probe_webm, f)
    with open(os.path.join(WORK, "probe-avi.json"), "w") as f:
        json.dump(probe_avi, f)

    ffprobe_script = f"""#!/bin/sh
for a in "$@"; do last="$a"; done
case "$last" in
  *.avi) cat "{WORK}/probe-avi.json" ;;
  *) cat "{WORK}/probe-webm.json" ;;
esac
"""
    ffprobe_path = os.path.join(BIN, "ffprobe")
    with open(ffprobe_path, "w") as f:
        f.write(ffprobe_script)
    os.chmod(ffprobe_path, 0o755)

    # ---- 5. Database ------------------------------------------------------
    db_path = os.path.join(WORK, "den.db")
    shutil.copy(BASE_DB, db_path)
    DB_URL = "sqlite:///" + db_path

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO,
        env={**os.environ, "DATABASE_URL": DB_URL},
        check=True,
    )

    os.environ["DATABASE_URL"] = DB_URL
    os.environ["STATE_DIR"] = STATE

    from sqlalchemy import create_engine  # noqa: E402
    from sqlalchemy.orm import sessionmaker  # noqa: E402
    from app.models import (  # noqa: E402
        Episode,
        Movie,
        PlaybackState,
        RootFolder,
        Series,
    )

    engine = create_engine(DB_URL)
    Session = sessionmaker(bind=engine)
    session = Session()

    rf_movies = RootFolder(name="Live movies", media_type="movie", path=MOVIES, is_default=False)
    rf_tv = RootFolder(name="Live TV", media_type="tv", path=TV, is_default=False)
    session.add_all([rf_movies, rf_tv])

    clip_path = os.path.join(MOVIES, "Clip (2026)", "Clip (2026).webm")
    old_path = os.path.join(MOVIES, "Old Sample (1999)", "Old Sample (1999).avi")
    escape_path = os.path.join(OUTSIDE, "Escape.webm")
    e1_path = os.path.join(TV, "Show", "Season 01", "Show - S01E01.webm")
    e2_path = os.path.join(TV, "Show", "Season 01", "Show - S01E02.webm")

    clip = Movie(
        tmdb_id=990001, title="Clip", year=2026, has_file=True,
        file_path=clip_path, file_quality="WEBRip-360p", file_score=0,
    )
    old = Movie(
        tmdb_id=990002, title="Old Sample", year=1999, has_file=True,
        file_path=old_path, file_score=0,
    )
    escape = Movie(
        tmdb_id=990003, title="Escape", year=2026, has_file=True,
        file_path=escape_path, file_score=0,
    )
    show = Series(tvmaze_id=990001, title="Show", year=2026)

    session.add_all([clip, old, escape, show])
    session.flush()

    e1 = Episode(
        series_id=show.id, season_number=1, episode_number=1, has_file=True,
        file_path=e1_path, file_score=0, monitored=True,
    )
    e2 = Episode(
        series_id=show.id, season_number=1, episode_number=2, has_file=True,
        file_path=e2_path, file_score=0, monitored=True,
    )
    session.add_all([e1, e2])
    session.commit()

    clip_id = int(clip.id)
    old_id = int(old.id)
    escape_id = int(escape.id)
    series_id = int(show.id)
    e1_id = int(e1.id)
    e2_id = int(e2.id)

    ids = {
        "clip": clip_id,
        "old": old_id,
        "escape": escape_id,
        "series": series_id,
        "e1": e1_id,
        "e2": e2_id,
    }
    with open(os.path.join(WORK, "ids.json"), "w") as f:
        json.dump(ids, f)

    # ---- 6. Start server --------------------------------------------------
    env = dict(os.environ)
    env.pop("FFMPEG", None)
    env.pop("FFPROBE", None)
    env.update(
        DATABASE_URL=DB_URL,
        STATE_DIR=STATE,
        WEB_HOST="127.0.0.1",
        WEB_PORT=str(PORT),
        TORRENT_PORT="6893",
        PATH=BIN + ":" + env.get("PATH", ""),
    )

    log_path = os.path.join(WORK, "server.log")
    proc = subprocess.Popen(
        [sys.executable, "-m", "app"],
        cwd=REPO,
        env=env,
        stdout=open(log_path, "w"),
        stderr=subprocess.STDOUT,
    )

    # Wait for server to be ready
    started = False
    deadline = time.time() + 60
    while time.time() < deadline:
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=5)  # a fresh connection per try
        try:
            conn.request("GET", "/health")
            resp = conn.getresponse()
            resp.read()
            if resp.status == 200:
                started = True
                break
        except (OSError, http.client.HTTPException):
            pass
        finally:
            conn.close()
        time.sleep(0.5)

    if not started:
        proc.terminate()
        print("Server did not start in time")
        sys.exit(2)

    # ---- 7. HTTP helpers --------------------------------------------------
    TOKEN = open(TOKEN_FILE).read().strip()

    def call(method, path, body=None, headers=None, auth=True):
        conn = http.client.HTTPConnection("127.0.0.1", PORT, timeout=30)
        hdrs = dict(headers) if headers else {}
        if body is not None and isinstance(body, dict):
            hdrs["Content-Type"] = "application/json"
            raw_body = json.dumps(body).encode()
        elif body is not None:
            raw_body = body
        else:
            raw_body = None
        if auth:
            hdrs["X-Api-Key"] = TOKEN
        conn.request(method, path, body=raw_body, headers=hdrs)
        resp = conn.getresponse()
        data = resp.read()
        resp_headers = {k.lower(): v for k, v in resp.getheaders()}
        return (resp.status, resp_headers, data)

    def js(data):
        return json.loads(data)

    # ---- 8. Checks --------------------------------------------------------
    CLIP_BYTES = open(CLIP, "rb").read()
    SIZE = len(CLIP_BYTES)

    # a. Unauthenticated access -> 401
    status, hdrs, body = call("GET", f"/api/play/movie/{clip_id}", auth=False)
    check("a: unauth 401", status, 401)

    # b. Authenticated play info
    status, hdrs, body = call("GET", f"/api/play/movie/{clip_id}")
    check("b: play 200", status, 200)
    if status == 200:
        info = js(body)
        check("b: type webm", info["type"].startswith("video/webm"), True)
        check("b: probed", info["probed"], True)
        check("b: notes empty", info["notes"], [])
        sub_ids = [s["id"] for s in info["subtitles"]]
        check("b: subtitle ids", sub_ids, ["x0"])
        check("b: subtitle lang", info["subtitles"][0]["language"], "en")
        check("b: position_ms 0", info["state"]["position_ms"], 0)
        check("b: next None", info["next"], None)
        check("b: duration_ms 90000", info["duration_ms"], 90000)

    # c. Range bytes=0-99 -> 206
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/file", headers={"Range": "bytes=0-99"}
    )
    check("c: range 206", status, 206)
    check("c: range body", body, CLIP_BYTES[:100])
    check("c: content-range", hdrs.get("content-range"), f"bytes 0-99/{SIZE}")

    # d. Range bytes=-10 -> last 10 bytes
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/file", headers={"Range": "bytes=-10"}
    )
    check("d: suffix range 206", status, 206)
    check("d: suffix body", body, CLIP_BYTES[-10:])

    # e. Range bytes=SIZE- -> 416
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/file", headers={"Range": f"bytes={SIZE}-"}
    )
    check("e: unsatisfiable 416", status, 416)
    check("e: content-range */{size}", hdrs.get("content-range"), f"bytes */{SIZE}")

    # f. HEAD -> 200 with correct content-length
    status, hdrs, body = call(
        "HEAD", f"/api/play/movie/{clip_id}/file"
    )
    check("f: head 200", status, 200)
    check("f: content-length", hdrs.get("content-length"), str(SIZE))

    # g. GET without Range -> full file
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/file"
    )
    check("g: full 200", status, 200)
    check("g: full size", len(body), SIZE)
    check("g: content-type webm", hdrs.get("content-type", "").startswith("video/webm"), True)

    # h. Subtitle x0.vtt -> valid VTT
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/subtitles/x0.vtt"
    )
    check("h: subtitle 200", status, 200)
    check("h: vtt content-type", hdrs.get("content-type", "").startswith("text/vtt"), True)
    check("h: vtt header", body[:6], b"WEBVTT")
    check("h: vtt cue", b"00:00:01.000 --> 00:00:30.000" in body, True)

    # i. Subtitle x9.vtt -> 404
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/subtitles/x9.vtt"
    )
    check("i: subtitle x9 404", status, 404)

    # j. Subtitle e3.vtt -> 404
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/subtitles/e3.vtt"
    )
    check("j: subtitle e3 404", status, 404)

    # k. Subtitle zz.vtt -> 404
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{clip_id}/subtitles/zz.vtt"
    )
    check("k: subtitle zz 404", status, 404)

    # l. Escape movie (outside library) -> 404
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{escape_id}"
    )
    check("l: escape play 404", status, 404)
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{escape_id}/file"
    )
    check("l: escape file 404", status, 404)

    # m. Old sample (AVI) -> notes about unsupported format
    status, hdrs, body = call(
        "GET", f"/api/play/movie/{old_id}"
    )
    check("m: old play 200", status, 200)
    if status == 200:
        info = js(body)
        check("m: avi type", info["type"], "video/x-msvideo")
        notes = info.get("notes", [])
        check(
            "m: avi container note",
            any("The avi container does not play in web browsers." in n for n in notes),
            True,
        )
        check(
            "m: mpeg4 codec note",
            any("Video codec mpeg4 does not play in web browsers." in n for n in notes),
            True,
        )

    # n. POST progress -> 200, position_ms 1500000, played False
    status, hdrs, body = call(
        "POST", f"/api/play/movie/{clip_id}/progress",
        body={"position_ms": 1500000, "duration_ms": 3000000, "event": "progress"},
    )
    check("n: progress 200", status, 200)
    if status == 200:
        info = js(body)
        check("n: position_ms", info["position_ms"], 1500000)
        check("n: played False", info["played"], False)

    # o. Continue contains clip
    status, hdrs, body = call(
        "GET", "/api/play/continue"
    )
    check("o: continue 200", status, 200)
    if status == 200:
        items = js(body)["items"]
        kinds = [(i["kind"], i["id"]) for i in items]
        check("o: clip in continue", ("movie", clip_id) in kinds, True)

    # p. POST stop -> played True, play_count 1, position_ms 0
    status, hdrs, body = call(
        "POST", f"/api/play/movie/{clip_id}/progress",
        body={"position_ms": 2900000, "duration_ms": 3000000, "event": "stop"},
    )
    check("p: stop 200", status, 200)
    if status == 200:
        info = js(body)
        check("p: played True", info["played"], True)
        check("p: play_count 1", info["play_count"], 1)
        check("p: position_ms reset", info["position_ms"], 0)

    # q. Continue no longer contains clip
    status, hdrs, body = call(
        "GET", "/api/play/continue"
    )
    if status == 200:
        items = js(body)["items"]
        kinds = [(i["kind"], i["id"]) for i in items]
        check("q: clip not in continue", ("movie", clip_id) in kinds, False)

    # r. POST watched with played=false -> played False
    status, hdrs, body = call(
        "POST", f"/api/play/movie/{clip_id}/watched",
        body={"played": False},
    )
    check("r: watched 200", status, 200)
    if status == 200:
        info = js(body)
        check("r: played False", info["played"], False)

    # s. Negative position -> 422
    status, hdrs, body = call(
        "POST", f"/api/play/movie/{clip_id}/progress",
        body={"position_ms": -5, "duration_ms": 1000, "event": "progress"},
    )
    check("s: negative position 422", status, 422)

    # t. Progress for escape movie -> 404
    status, hdrs, body = call(
        "POST", f"/api/play/movie/{escape_id}/progress",
        body={"position_ms": 1000, "duration_ms": 3000, "event": "progress"},
    )
    check("t: escape progress 404", status, 404)

    # u. Episode play info
    status, hdrs, body = call(
        "GET", f"/api/play/episode/{e1_id}"
    )
    check("u: episode 200", status, 200)
    if status == 200:
        info = js(body)
        check("u: subtitle S01E01", info["subtitle"], "S01E01")
        check(
            "u: next href",
            info["next"]["href"],
            f"/watch/episode/{e2_id}",
        )
        check(
            "u: back_href",
            info["back_href"],
            f"/ui/series/{series_id}",
        )

    # v. Watch page for clip
    status, hdrs, body = call(
        "GET", f"/watch/movie/{clip_id}", headers={"Accept": "text/html"}
    )
    check("v: watch 200", status, 200)
    expected_info_url = f'data-info-url="/api/play/movie/{clip_id}"'.encode()
    check("v: info-url in body", expected_info_url in body, True)

    # w. Library and series pages
    status, hdrs, body = call(
        "GET", "/library", headers={"Accept": "text/html"}
    )
    check("w: library 200", status, 200)
    expected_watch_link = f"/watch/movie/{clip_id}".encode()
    check("w: clip link in library", expected_watch_link in body, True)

    status, hdrs, body = call(
        "GET", f"/ui/series/{series_id}", headers={"Accept": "text/html"}
    )
    check("w: series 200", status, 200)
    expected_ep_link = f"/watch/episode/{e1_id}".encode()
    check("w: episode link in series", expected_ep_link in body, True)

    # x. Series play endpoint -> 404 or 422
    status, hdrs, body = call(
        "GET", "/api/play/series/1"
    )
    check("x: series play rejected", status in (404, 422), True)

    # ---- 9 / 10. Cleanup --------------------------------------------------
    if keep:
        print(f"server kept running on http://127.0.0.1:{PORT} (pid {proc.pid}); ids in {WORK}/ids.json")
    else:
        # Create a state row first
        call(
            "POST", f"/api/play/movie/{clip_id}/progress",
            body={"position_ms": 1500000, "duration_ms": 3000000, "event": "pause"},
        )

        # Delete the movie
        status, hdrs, body = call(
            "DELETE", f"/movies/{clip_id}"
        )
        check("10: delete status", status in (200, 204), True)

        # Verify playback_states row is gone
        conn_db = sqlite3.connect(db_path)
        cur = conn_db.cursor()
        cur.execute(
            "SELECT COUNT(*) FROM playback_states WHERE item_kind='movie' AND item_id=?",
            (clip_id,),
        )
        count = cur.fetchone()[0]
        conn_db.close()
        check("10: playback_states cleared", count, 0)

        # Terminate server
        proc.terminate()
        deadline = time.time() + 20
        while time.time() < deadline:
            ret = proc.poll()
            if ret is not None:
                break
            time.sleep(0.5)

    # ---- Summary ----------------------------------------------------------
    print(f"\n{'=' * 60}")
    if failures:
        print(f"FAILED {len(failures)} check(s): {', '.join(failures)}")
        sys.exit(1)
    else:
        print("All checks passed.")
        sys.exit(0)


if __name__ == "__main__":
    main()
