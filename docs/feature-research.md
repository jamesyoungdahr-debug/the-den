# Feature research: what The Den still needs, and what would be nice (2026-09-12)

The Den replaces Sonarr, Radarr, Prowlarr and the request layer (Overseerr/Jellyseerr, now
merged into Seerr) with one app plus a KDE client and an Android app. This compares what
those tools and their companion apps offer today against what The Den has after M13, and
sorts the gaps into "needed to be a credible replacement" and "nice to have". Each item
names the surfaces it touches: server, web, KDE, Android.

Sources: Prowlarr's indexer stats and health model, Seerr's request and discovery feature
set, TRaSH-style quality profile and custom-format practice for Sonarr/Radarr, and the
nzb360 / LunaSea companion apps (links at the bottom).

## Where The Den stands

Done: indexers with presets and native public trackers, quality profiles, release parsing
and scoring, built-in torrent client, hard-link import with Plex-style names, TVmaze/TMDB
metadata, calendar, Discord notifications, Plex login and library scan, requests with
quotas and approval, accounts and API tokens, a Glass UI on all three surfaces.

## Tier 1: needed (people will hit these in the first week of real use)

| # | Feature | Why it matters | Surfaces |
|---|---|---|---|
| N1 | **Upgrades**: re-grab when a better release than the one on disk appears (profile has a cutoff; "upgrade until" quality). Today a title with a file is never searched again. | Core Sonarr/Radarr behaviour; without it a 720p first grab is permanent. | server (automation, scoring), web/KDE/Android (show "upgradable") |
| N2 | **Custom formats / release preferences**: prefer or avoid by keyword and regex (HDR, x265, group names, language, "remux"), with a score that feeds the picker. | TRaSH-guide users expect it; also the only way to express "no CAM/TS", "English audio only". | server (scoring, profiles), web (profile editor), KDE/Android (read-only view) |
| N3 | **Failed-download handling**: detect stalled or dead torrents (no peers after N minutes, seeder count zero), blocklist the release, and search again automatically. | Public trackers hand out dead magnets constantly; today a dead grab sits forever. | server (automation, torrent engine), all clients (status badge) |
| N4 | **Interactive search everywhere**: the manual release list with size, seeders, age, quality and a one-click grab, reachable from every title on every surface. Web and KDE have it; Android has Releases but not from Discover. | The single most-used screen in nzb360/LunaSea. | Android (Detail -> Releases), KDE (Detail), web (detail page) |
| N5 | **Notification agents beyond Discord**: ntfy and generic webhook first (both are one HTTP POST), then Telegram and Pushover. Events: grabbed, imported, upgraded, request submitted/approved/available, health warning. | Discord-only excludes most self-hosters; ntfy is the current default in this space. | server (notifier, settings), web (settings), KDE/Android (settings) |
| N6 | **Health checks and an indexer stats page**: per-indexer success rate, average response time, last error; app-level warnings (library folder missing, torrent port not reachable, Chromium absent, Plex token expired) surfaced on the Discover page and in the apps. | Prowlarr's headline feature; also the only way a user learns a tracker died. | server (stats table, `/health` detail), web (Indexers page), KDE/Android (Indexers, banner) |
| N7 | **Season and series-level actions**: monitor/unmonitor a season, "search whole season", season pack grabs (one torrent covering S01) with per-episode import. | Every TV user needs season packs; per-episode only is 5x the traffic and misses packs entirely. | server (importer for multi-file torrents, search), web/KDE/Android (season menu) |
| N8 | **Push notifications on Android**: request approved / available and download finished, via the notification agent (ntfy app on the phone is the zero-infrastructure route; FCM later). | The reason people install a companion app. | server (N5), Android (subscribe to ntfy topic, deep links) |
| N9 | **Real-world shakedown**: plex.tv, real indexer grabs, Plex-watched import folder, Cloudflare solver on a residential connection. Not a feature, but it gates everything above. | Every item here is untested against real services. | all |

## Tier 2: expected by *arr users (second month)

| # | Feature | Surfaces |
|---|---|---|
| E1 | **Import lists**: auto-add from a TMDB list, Trakt list or Plex watchlist; the Seerr "watchlist -> request" flow. | server, web (settings), KDE/Android (toggle) |
| E2 | **Root folders per profile / multiple libraries**: e.g. Kids movies vs Movies, 4K vs 1080p libraries with their own folders and profiles. | server (models, importer), web, clients (chooser on add) |
| E3 | **Manual import / unmatched downloads**: a queue of finished torrents The Den could not match, with "assign to title" and "import as-is". | server, web (Downloads), KDE/Android |
| E4 | **Rename existing files** to the Plex convention on demand, with a preview (M13 only renames new imports). | server, web (library actions) |
| E5 | **Blocklist and history**: every grab, import, failure and removal with timestamps; per-title history on the detail page; "blocklist this release". | server (table), web/KDE/Android (history tab) |
| E6 | **Subtitles**: Bazarr-style OpenSubtitles fetch per language preference. | server, settings on all surfaces |
| E7 | **Usenet download client**: the presets already list 13 Newznab indexers, but there is no NZB downloader (SABnzbd/NZBGet integration, or a built-in one). Until then the usenet presets only work for people who also run an NZB client. | server (downloader abstraction), settings |
| E8 | **Request comments and reasons**: decline with a note (exists) plus a user-visible thread; "request 4K" as a variant. | server, web, Android |
| E9 | **Per-user notification settings** for request outcomes (email or ntfy per user). | server, web (profile), Android |
| E10 | **Backup and restore** of the SQLite database and settings from the web UI, and an export of the indexer list. | server, web |

## Tier 3: nice to have

| # | Feature | Surfaces |
|---|---|---|
| W1 | Light theme (both clients and web are dark-only). | design tokens, all |
| W2 | Torrent polish: per-torrent file selection, sequential download, IP filter, proxy, a session stats line (all exposed by libtorrent; none wired). | server, web Downloads, clients |
| W3 | Multiple Plex servers, or Jellyfin/Emby as the media server (Seerr's differentiator). | server (plex_scan abstraction), settings |
| W4 | Trakt scrobble / watched-state sync back to Discover ("continue watching"). | server, Discover |
| W5 | Android: home-screen widget for the calendar or pending requests; Wear OS approve/decline; app shortcuts. | Android |
| W6 | KDE: system tray icon with download progress, KRunner integration ("den: <title>"), Plasma notification badges. | KDE |
| W7 | Wake-on-LAN and local/remote address switching in the apps (nzb360 feature). | Android, KDE |
| W8 | Language and country preferences for Discover (TMDB region for "on the air", original-language filter). | server, web, clients |
| W9 | Anime handling: absolute episode numbering, Nyaa as the default indexer for anime-typed series, fansub group preference. | server (parser, TVmaze), clients (series type) |
| W10 | Music (Lidarr) and books (Readarr) are out of scope; note it in the README so nobody asks. | docs |

## Suggested order

Tier 1 is the next milestone group. The dependency chain is: N9 (shakedown) first so the
rest is built against reality; N5 (notification agents) before N8 (push) and before N3
(failures need somewhere to report); N2 (custom formats) before N1 (upgrades need a
score to compare); N7 (season packs) needs the importer to handle multi-file torrents,
which E3 (manual import) reuses. A plausible sequence: N9, N5, N6, N2, N1, N3, N7, N4, N8.

Everything in Tier 1 touches all three clients at least for display, so each milestone
should end with the client work, the way M12 did, rather than leaving the apps behind.

## Decisions to make before starting

1. Usenet: build a downloader in (E7) or declare The Den torrent-only and drop the
   usenet presets to a "bring your own NZB client" note? The presets are cheap to keep
   but currently promise more than the app delivers.
2. Push: ntfy topic per server (simple, self-hostable, no Google account) versus FCM
   (needs a Firebase project and a Play-signed build). ntfy fits HoltOS's self-hosted
   stance.
3. Custom formats: import TRaSH-guide JSON as-is (users bring their own, huge surface)
   versus a small curated set (HDR, x265, remux, language, group blocklist) with a plain
   UI. The curated set matches the "one app, no config sprawl" brief.

## Sources

- Prowlarr indexer stats and health: https://www.techgeeks.org/prowlarr-setup-indexer-management-sonarr-radarr/ and https://bytesized-hosting.com/guides/prowlarr-guide-one-indexer-manager-for-all-your-arr-apps
- Seerr (Overseerr + Jellyseerr merge) feature set: https://docs.seerr.dev/blog/seerr-release/ and https://helmarr.com/blog/jellyseerr-vs-overseerr-vs-seerr-merge-2026
- Quality profiles, custom formats, upgrade behaviour: https://trash-guides.info/Sonarr/sonarr-setup-quality-profiles/ and https://helmarr.com/blog/sonarr-quality-profiles-custom-formats-a-practical-setup-guide
- Notification agents in current Sonarr/Radarr: https://v3.quickbox.io/articles/sonarr-v4-radarr-2026-setup-guide
- Companion apps (nzb360, LunaSea): https://nzb360.com/ and https://wiki.servarr.com/useful-tools
