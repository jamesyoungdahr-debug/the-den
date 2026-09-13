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

**Done 2026-09-12 (server 0.6.1, client 0.4.6, android 0.5.3).** `indexer_stats` (per indexer, per UTC day: searches / successes / failures / total ms / last error, written by `search_all`) and `health_issues` tables, `app/health.py` (folders exist and writable, torrent engine running, Cloudflare solver present when a Cloudflare preset is enabled, Plex token valid vs plex.tv unreachable, any indexer with 3+ searches and no success today) run at the end of every automation cycle; issues are reconciled (new ones fire `health_warning`, cleared ones are deleted). `/health` returns `checks`; `GET /indexers/stats?days=7`; `PATCH /indexers/{id}` (enable / rename). Discover banner and Indexers stats line + enable/disable on the web, the KDE client and Android. Verified: `m16_smoke.sh` (stats populated, issues appear and clear, health_warning posted to the ntfy mock, PATCH), KDE harness 13 pages clean, Android build. Not done: the "torrent port reachable from outside" check (needs a public reflector); the health check runs on the automation cadence only, not on demand.

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

**Done 2026-09-12 (server 0.6.2, client 0.4.7, android 0.5.4).** `custom_formats` (name, JSON rules of {field, op, value, negate} over title / quality / source / codec / hdr / audio / group / language) and `profile_format_scores`; `quality_profiles.min_format_score`. `parse_release` in `app/parser.py` (source, codec, HDR/DV, audio, languages, group). `app/formats.py`: 16 built-in formats seeded at startup with default scores (Remux 60 … CAM -1000, foreign-language-only -200), `score_title`, `validate_rules`. `best_release` ranks by allowed quality, then format score, then seeders and rejects below the profile floor; candidates carry `score` and `formats`. `/api/formats` (CRUD, builtin rename/delete refused), `/api/formats/profiles` + PATCH (qualities, cutoff, floor, per-format scores), `/api/formats/test`. Web: Settings "Quality & formats" section (profile editor, format list with inline scores, rule dialog, title tester, `app/static/formats.js`), Releases page shows score and format chips. KDE and Android Releases pages show score and formats. Verified: `tests/test_formats.py` (20 titles + scoring), `m17_smoke.sh` API sweep, live candidates for The Matrix (290 releases scored), settings page in the browser, KDE harness, Android build. Not done: no TRaSH import; one profile only (the editor targets the first profile); the KDE/Android apps do not edit formats.

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

**Done 2026-09-12 (server 0.6.3, client 0.4.8, android 0.5.5).** Profiles gain `upgrade_until_score`; movies and episodes record `file_quality`, `file_score`, `file_path` and `last_upgrade_search`; download records carry `quality`, `score`, `upgrade`. `is_upgradable` (below the cutoff quality, or below the score target) and `beats_current` (strictly better allowed quality, or same quality and +10 score) in `app/scoring.py`. The grabber records the release's quality and score and marks a grab for a title that already has a file as an upgrade; the importer links the new file beside the old one, swaps it in atomically and removes the old file; the download check stores the file fields and fires "upgraded". `automation._upgrade_titles` re-searches each upgradable title at most once a day and grabs only a candidate that beats the file on disk. `/movies` and `/series/{id}/episodes` return `file_quality`, `file_score`, `upgradable`. Web: library "Upgradable" filter and badge, series detail badge, "Find releases" on upgradable titles, settings field for the score target. KDE and Android: badges and the Find/Releases button on upgradable titles. Verified: helper probes, an on-disk swap probe (same-name file replaced, no leftovers), `m18_smoke.sh` (flags, filter page, profile field), KDE harness, Android build. Not done: the local-swarm two-release e2e; the "upgraded" path was not exercised against the real torrent engine.

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
