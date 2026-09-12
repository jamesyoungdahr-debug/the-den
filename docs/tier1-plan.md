# Plan: Tier 1 milestones M14 to M21 (drafted 2026-09-12)

Turns the "needed" tier of [feature-research.md](feature-research.md) into milestones,
in dependency order. Same rules as every milestone so far: one at a time, each verified
against a running backend before the next starts, each ends with the client work so the
KDE and Android apps never fall behind the server.

## Decisions taken (override any of these before M15 starts)

| Decision | Default | Why |
|---|---|---|
| Usenet | **Torrent-only for now.** The 13 usenet presets stay, marked "needs an NZB client you run yourself"; a usenet downloader is a Tier 2 milestone. | The built-in client is torrent; a second download path doubles the importer surface before the first has seen real use. |
| Push | **ntfy.** The server posts to an ntfy topic (self-hosted or ntfy.sh); the Android app subscribes with the ntfy app or its own subscriber. No Firebase, no Play dependency. | Self-hosted fits HoltOS; works with the sideloaded APK. |
| Custom formats | **Curated set, plain UI.** Built-in formats (HDR, DV, x265/HEVC, remux, web-dl vs webrip, language, release group) each with a score per profile, plus a free-text "avoid" list. No TRaSH JSON import in this pass. | One app, no config sprawl; the JSON importer can come later if asked for. |

## Milestones

### M14 Shakedown (no code unless it finds bugs)

Real plex.tv sign-in and library scan on the HoltOS box, one real grab from Knaben or
TPB into the built-in client, the Plex-style import landing in a Plex-watched folder,
the built-in Cloudflare solver against 1337x on a residential line, the KDE icon.
Output: a list of defects, fixed as they appear. Gate for everything below.

### M15 Notifications (server, web, KDE, Android)

**Done 2026-09-12 (server 0.6.0, client 0.4.5, android 0.5.2).** `notification_agents` table, `app/notifier.py` with Discord / ntfy / webhook / Telegram / Pushover senders and `notify_event` fan-out, `/api/notifications/*` (kinds, events, agents CRUD, test), agent lists with add/edit/test in the web settings page, the KDE settings page and the Android settings screen. Verified: API smoke (validation, secret blanking, edit keeps secret, delete), event sweep through `tests/mock_webhook.py` (9/9 ntfy, 2/2 Telegram by subscription), KDE harness 13 pages clean, Android build. Not yet: Pushover against the real service, the "upgraded" / "download_failed" / "health_warning" events have no emitter until M16, M18, M19.


- `app/notifier.py` becomes agent-based: Discord (existing), **ntfy** (topic URL,
  optional token, priority), **generic webhook** (JSON POST), Telegram, Pushover.
- Event catalogue with per-agent toggles: grabbed, imported, upgraded, download failed,
  request submitted / approved / declined / available, health warning.
- Settings -> Notifications on all three surfaces: agent list, add/test/remove.
- Verify: `tests/mock_webhook.py` grows an ntfy-shaped endpoint; e2e sends every event.

### M16 Health and indexer stats (server, web, KDE, Android)

- `indexer_stats` table: per indexer, per day, searches / successes / failures /
  average ms / last error. Written by `app/indexers.search_all`.
- Health checks run each automation cycle: library folders writable, downloads folder
  writable, torrent port reachable, Chromium present when a Cloudflare preset is
  enabled, Plex token valid, any indexer failing 100% for 24 h. Stored with a level
  (warning / error) and cleared when the condition goes away.
- `/health` gains `checks`; Discover shows a banner; Indexers page gets a stats column
  and a "disable failing" action. Both apps: banner plus stats on the Indexers page.
- Verify: e2e with an unreachable indexer and a missing folder.

### M17 Custom formats (server, web; apps read-only)

- Tables `custom_formats` (name, rules: JSON list of {field: title|group|language,
  op: contains|regex, value, negate}) and `profile_format_scores` (profile, format,
  score). Seeded with the curated set at first run; user-editable.
- `app/scoring.py`: release score = quality rank + sum of matched format scores; a
  negative score below a profile threshold rejects the release. Parser gains group,
  HDR/DV, source (remux/web-dl/webrip/bluray) and audio-language detection.
- Web: profile editor with the format list and a per-format score; Releases page shows
  matched formats and the score. KDE/Android: show the score and formats on Releases.
- Verify: parser unit tests on 40 real release titles; scoring tests.

### M18 Upgrades (server, all surfaces)

- Profile gains `cutoff` (quality) and `upgrade_until_score`. A title with a file is
  "upgradable" while below either. `DownloadRecord` records the score of what is on
  disk.
- Automation searches upgradable titles at a lower cadence (daily), grabs only when the
  new score beats the current one by a margin, imports over the old file (hard-link
  swap, old file removed after the new one is verified), and sends "upgraded".
- Library pages show an "upgradable" badge and a filter; detail pages show current
  quality and score. Apps: badge only.
- Verify: e2e with two seeded releases of different quality.

### M19 Failed-download handling (server, all surfaces)

- Torrent engine reports stalled (no progress for N min with zero seeders) and dead
  (metadata never arrives) states; automation marks the record failed, blocklists the
  release (info-hash and title), removes the torrent and data, and re-searches.
- `blocklist` table with reason and expiry; a manual "blocklist and search again" on
  the Downloads page and both apps.
- Verify: local swarm test with a seeder that disappears.

### M20 Season packs and season actions (server, all surfaces)

- Importer handles multi-file torrents: each video file parsed for SxxEyy and imported
  to its episode; unmatched files listed for manual import (the seed of Tier 2's E3).
- Search: "season pack" query form (`Show S01`), preferred when >= 60% of a season is
  missing; pack results scored against the whole season.
- Season menu on the series page: monitor / unmonitor, search season, mark season
  as have. Apps get the same three actions on the Episodes page.
- Verify: local swarm with a 3-file pack.

### M21 Android: interactive search from Detail, push, deep links

- Detail -> Releases for tracked titles (reuse CandidatesScreen), grab from the phone.
- ntfy subscriber (topic + server from Settings), notification channels per event,
  tapping opens the request or download.
- Verify: LiveBackendTest additions; manual on the Fold and the S25.

## Sizing (working sessions, one milestone each unless noted)

| M14 | M15 | M16 | M17 | M18 | M19 | M20 | M21 |
|---|---|---|---|---|---|---|---|
| 1, box-side | 1 | 1 | 2 | 1 | 1 | 2 | 1 |

## Working method

- Every code unit goes to the local model (4090 bridge first, 4080 as overflow), one
  file or function per request; Claude specs, reviews, tests, commits. Small units work
  best with the current coder models.
- Each milestone: plan doc row -> server -> web -> KDE -> Android -> docs
  (STATUS, ROADMAP, CONTEXT.txt) -> commit, tag, push. HoltOS vendor manifest bump
  after each server or client tag.
- Version plan: server 0.6.x through M20, 1.0.0 when M21 lands and the shakedown is
  clean; client 0.5.x; Android 0.6.x.
