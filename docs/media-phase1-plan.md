# Plan: media server Phase 1, direct play in the web UI (M49)

Drafted 2026-09-15. Parent plan: docs/media-server-plan.md (phases P0 to P9). M49 is P1 plus the parts of P0 it needs. Transcoding (P2), remux (P3), the KDE and Android players and signed stream URLs (P4) come later.

## Goal
Any signed-in user can play a movie or episode file from The Den's library in the browser, with subtitles, resume and watched state, when the browser can play the file as it is. When it cannot, the page says why and that transcoding arrives in a later phase.

## Decisions
- Direct play only; no ffmpeg transcoding in M49.
- ffprobe (and ffmpeg for embedded text subtitles) run as subprocesses with argument lists and timeouts. The PKGBUILD depends on ffmpeg; the server still works without it (no probe data, no embedded subtitles) so development machines without ffmpeg keep running.
- The web player uses the session cookie (same origin). Apps may call the same API with X-Api-Key. Signed short-lived URLs wait for P4, when the first player that cannot send cookies or headers arrives.
- POST endpoints rely on the SameSite=lax session cookie, like the rest of the web UI.
- Every file is opened through one module written by Claude (app/media_stream.py): the item id is resolved to its stored path, the real path must sit inside a configured library folder (compared by path components, symlinks resolved), no folders configured means nothing plays, only video extensions, the file is opened and checked again with fstat, and subtitle sidecars are addressed by track id, never by file name.
- Byte ranges are served by The Den itself because Starlette 0.38.6 FileResponse has no Range support: single ranges, suffix ranges, 416 with "bytes */size", If-Range, multi-range answered with the whole file.
- Progress: clients report start, progress every 10 seconds, pause, seek and stop. Positions are clamped to the duration. An item counts as played past 90 per cent; a resume point under 60 seconds is dropped; play_count rises when an item becomes played.
- SQLite reuses the highest row id, so playback state is deleted whenever a movie, series, episode or user is deleted.

## Units and who writes them
- U1a probe and cache: app/media_probe.py (4090)
- U1b codec strings and direct-play notes: app/playability.py (4080)
- U2 models and migration: app/models.py, migrations/versions (4090)
- U3 playback state service: app/playback.py (Strix Halo)
- U3b delete hooks: routers movies, series, ui, users (4080)
- U4 file access, sidecars and byte ranges: app/media_stream.py (Claude, security)
- U5a sidecar SRT to WebVTT: app/subtitle_tracks.py (4090)
- U5b embedded text subtitles to WebVTT with a hash-named cache: app/subtitle_tracks.py (4090)
- U6 play API and wiring: app/routers/play.py, app/main.py (4090, reviewed closely)
- U7a watch page and basic player: app/routers/ui.py, templates/watch.html, static/player.js (4090)
- U7b resume, progress reporting and next episode: static/player.js (4090)
- U7c Play buttons, progress and watched badges, Continue watching rail: library.html, series_detail.html, discover.html, den.css (4090 or Strix Halo)
- U8 PKGBUILD depends ffmpeg and version 0.8.2a (4080)
- U9 offline checks tests/test_media.py and a live test script (4090)
- U10a this plan; U10b STATUS.md, CONTEXT.txt and HANDOFF.md at the end (local models)

## API
List: GET /api/play/{kind}/{id} (play info), GET and HEAD /api/play/{kind}/{id}/file, GET /api/play/{kind}/{id}/subtitles/{track_id}.vtt, POST /api/play/{kind}/{id}/progress, POST /api/play/{kind}/{id}/watched, GET /api/play/continue. kind is movie or episode. Page: GET /watch/{kind}/{id}.

## Tests
- Offline (tests/test_media.py): probe parsing from fixture JSON, codec strings and notes, progress rules on an in-memory database, SRT to WebVTT, range parsing edge cases, the path guard with temporary folders and a symlink escape, delete hooks with id reuse.
- Live in WSL: python -m app against a temporary library, a fake ffprobe script returning fixture JSON (WSL has no ffmpeg), a small VP8 WebM clip made with Playwright's bundled ffmpeg, curl range checks, and a browser run in the in-app Browser pane.
- Live in the holtos-test VM with the real ffmpeg 9.0.1 (Liam approved on 2026-09-15 through the HoltOS session): probe real files and extract an embedded subtitle. Pattern: a home folder, a spare port such as 40291, nothing under /opt or /etc, no reboot, offline, and message the HoltOS session before and after.

## Done when
The offline checks pass; in the browser a file plays, seeks, shows a subtitle, resumes where it stopped, shows as watched after the end, and appears in Continue watching while half watched; an unplayable file shows its reasons; a path outside the library folders is refused; the VM run probes real files.
