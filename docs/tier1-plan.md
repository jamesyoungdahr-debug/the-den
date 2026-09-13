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

**Done 2026-09-13 (server 0.6.4, client 0.4.9, android 0.5.6).** `blocklist` table (info hash and exact title, reason, optional expiry, 30 days by default) and `app/blocklist.py`; download records track `last_progress` / `last_progress_at` / `failure_reason`. The download check fails a torrent that reports an engine error, never resolves its magnet within 20 minutes, or makes no progress for 30 minutes with no seeders: the release is blocklisted, the torrent removed with its data, the record marked failed and "download_failed" sent; the next cycle searches again and blocklisted releases are dropped from every candidate list. Manual "blocklist and search again" on the Downloads page (live torrent rows, plus a Blocklist section with remove), the KDE Downloads page (button + confirm dialog) and the Android Downloads screen, all through `POST /downloads/by-hash/{hash}/blocklist` (also `/downloads/{id}/blocklist`, `GET /downloads/blocklist`, `DELETE /downloads/blocklist/{id}`). Expired entries are purged each cycle. Verified: a fake-engine stall probe (record failed, torrent removed with files, title and hash blocked, notification sent), `m19_smoke.sh` (manual blocklist, retry grabbed a new release, candidates exclude the title, no duplicate entries, page renders), KDE harness, Android build. Not done: the local-swarm "seeder disappears" e2e.

- Torrent engine reports stalled (no progress for N min with zero seeders) and dead
  (metadata never arrives) states; automation marks the record failed, blocklists the
  release (info-hash and title), removes the torrent and data, and re-searches.
- `blocklist` table with reason and expiry; a manual "blocklist and search again" on
  the Downloads page and both apps.
- Verify: local swarm test with a seeder that disappears.

### M20 Season packs and season actions (server, all surfaces)

**Done 2026-09-13 (server 0.6.5, client 0.4.10, android 0.5.7).** `parse_episode` / `parse_season_pack` in the parser; download records can point at a series + season instead of one episode; `importer.import_season_pack` links every SxxEyy video file in a multi-file torrent to its episode (samples skipped, unmatched files reported in the record's failure reason); the download check imports packs and updates every episode's file fields. Search: `season_query` (`Show S01`), `season_candidates` keeps only whole-season releases; automation groups missing monitored episodes by season and, when at least 60% of a season is missing and no pack is already on its way, grabs the best pack instead of single episodes. Season actions on the series page (monitor / unmonitor, season packs list, search season, mark as have) via `/series/{id}/seasons/{n}/{candidates,grab,monitor,mark-have,search}`, on the web (season header buttons), the KDE Episodes page (season header row, season-pack candidates through CandidatesPage.loadSeason) and Android (season header row, `seasons:<n>` candidates route). Verified: parser probe, fake-files pack import probe, `m20_smoke.sh` (season endpoints, series page, live pack candidates for Breaking Bad, fake-engine pack import producing Plex-named episode files), KDE harness, Android build. Not done: the local-swarm three-file pack e2e; a manual-import page for unmatched files (Tier 2).

- Importer handles multi-file torrents: each video file parsed for SxxEyy and imported
  to its episode; unmatched files listed for manual import (the seed of Tier 2's E3).
- Search: "season pack" query form (`Show S01`), preferred when >= 60% of a season is
  missing; pack results scored against the whole season.
- Season menu on the series page: monitor / unmonitor, search season, mark season
  as have. Apps get the same three actions on the Episodes page.
- Verify: local swarm with a 3-file pack.

### M21 Android: interactive search from Detail, push, deep links

**Done 2026-09-13 (server 0.6.6, android 0.6.0).** Server: every notification now carries a `theden://` deep link (`notify_event(..., link=)`; ntfy sends it as the `Click` header, the generic webhook payload gains a `link` field): `theden://requests/{id}` for request submitted / approved / declined, `theden://detail/{kind}/{tmdb}` for request available, `theden://downloads` for grabbed / imported / upgraded / download failed, `theden://discover` for health warnings. Android: new `push/` package -- `PushPrefs` (per-device on/off, ntfy server, topic, last message id), `NtfySubscriber` (streaming `GET {server}/{topic}/json?since=`, reconnect with backoff), `PushChannels` (one notification channel per event), `PushService` (special-use foreground service, START_STICKY, brought back by `BootReceiver` after a reboot), `DeepLinks.routeFor` (link -> navigation route); MainActivity is `singleTask` with a `theden` scheme intent filter and navigates to the pending link once the session is up; a "Push notifications" panel on the account page asks for POST_NOTIFICATIONS and starts or stops the service. Detail: admins get a Releases button on tracked movies and can tap a tracked season to open its season-pack candidates (both reuse CandidatesScreen). Verified: `m21_smoke.sh` and `m21_req.py` (Click header and webhook link on the direct path and the real request_approved path against the ntfy / webhook mock), `PushTest` (5 JVM tests: route mapping, rejects, offer, ntfy stream decode, since URL), `assembleDebug`. Not done: manual test on the Fold and the S25 (0.6.0 not installed yet); the phone subscriber sends no Authorization header, so a private ntfy server needs a readable topic (token support is a follow-up); (token support is a follow-up).

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
- Version plan: server stays on 0.x (0.6.x through M21, 0.7.x after); no 1.0.0 until
  Liam calls the product finished. Client 0.4.x -> 0.5.x; Android 0.6.x.
