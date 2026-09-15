# Media server for The Den: research and plan

Update 2026-09-15: Liam set the goal of replacing Plex completely. The milestone order now lives in docs/plex-replacement-plan.md; this document stays as the research behind it. Phase 1 (direct play in the web UI) is done as M49, see docs/media-phase1-plan.md.

Researched 2026-09-15. Sources: four research reports on Plex's feature set, what Plex users wish Plex had, Jellyfin and Emby, and media-server architecture. No code has been written. This document is a plan for Liam to decide on, not a commitment.

## 1. Summary and recommendation

The Den already tracks a library, downloads media and talks to Plex. The idea is to let The Den play that library itself, so a household does not need Plex, Jellyfin or Emby next to it.

### Recommendation

- Build it as an optional part of The Den ("Den Media"), reusing its library, accounts, device tokens, pinned HTTPS (M35/M39/M40) and router remote access (M36). The existing Plex integration stays for people who keep Plex.
- Never paywall anything and never require a cloud account or send telemetry. Plex charges for remote streaming, hardware transcoding, downloads and intro skipping; Emby charges for hardware transcoding, DVR, downloads and intro skipping. Free versions of those are The Den's clearest advantage.
- Streaming design: ffmpeg run as a separate process; direct play first, then remux, then transcode, decided from what each device reports it can play; HLS with fMP4 segments; hardware encoding detected at startup with a software fallback.
- The Den's own API comes first. Compatibility layers come second: OpenSubsonic for music early (small, stable, many existing apps), and a narrow Jellyfin 12.x API slice later (Infuse and Findroid first).
- Features that set it apart, from what users ask for: offline downloads converted on the server, built-in intro and credits skipping, watch-together invite links, sharing without a cloud account (with SSO and two-factor sign-in later), removing items from Continue Watching, an admin view that can stop a stream and message a user, importing watch history from Plex, and requesting, downloading and playing from one place.

### Decisions Liam needs to make before building

1. Licence. The Den has no LICENSE file (PKGBUILD says license=('unknown')). Jellyfin is GPL-2.0; Intro Skipper and Navidrome are GPL-3.0. Copying or porting their code would make The Den GPL. Reimplementing behaviour, public APIs and file formats is fine under any licence. Running ffmpeg as a separate program does not affect The Den's licence.
2. Casting and certificates. Chromecast, DLNA TVs and Roku refuse self-signed HTTPS, and third-party apps cannot pin The Den's certificate. Options: a LAN-only plain-HTTP media port that accepts only short-lived signed URLs, or a publicly trusted certificate, which needs a domain.
3. KDE player: Qt's own media player (may not support certificate pinning) or libmpv. Needs a small prototype.
4. Hardware target: without a GPU a typical server manages only one or two simultaneous transcodes.

The later sections cover: Plex's feature set, what users wish Plex had, Jellyfin and Emby, architecture, the phased plan, and risks.

## 2. Plex's feature set (what to match)

This section summarises the capabilities of Plex Media Server and its companion applications, as documented in the research report *Plex Media Server and apps: feature inventory* (September 2026). Features marked **[PP]** require a Plex Pass subscription; those marked **[RWP]** are also unlocked by the Remote Watch Pass.

### Libraries and metadata

Plex organises media into typed libraries: Movies, TV Shows, Music, Photos, and Other Videos (home videos). Each library is backed by one or more folders, a scanner that matches file names to items, and a metadata agent that fetches artwork and details. Scans run on a schedule, on detected file changes, or manually; "empty trash" removes missing items after each scan.

Naming conventions are well defined: `Movies/Title (Year)/Title (Year).ext` for films, `Show (Year)/Season 01/Show - s01e01.ext` for television, and `Artist/Album/NN - Track.ext` for music with embedded tags preferred. Plex also handles multi-episode files, date-based shows, specials in Season 00, split parts, and optional `{tmdb-…}`, `{imdb-tt…}` or `{tvdb-…}` identifiers to force a match.

| Capability | Notes |
|---|---|
| Multiple versions per title | Several files (e.g. 4K and 1080p) in one folder become one item with selectable versions. |
| Editions | `{edition-Director's Cut}` creates a separate edition on the same title *(verify whether still [PP])*. |
| Local extras | Subfolders named `Trailers`, `Behind The Scenes`, etc., or suffixes such as `-trailer`. **[PP]** Automatic online trailers and extras. |
| Local assets | Posters, fanart, banners, theme music, sidecar subtitles, embedded metadata, NFO files. |

The modern agents (Plex Movie, Plex Series, Plex Music) are backed by Plex's own metadata service, built on TMDB, TVDB, IMDb and similar sources. Legacy third-party agents have been retired; the replacement is a custom metadata provider API in beta since December 2025 ([How-To Geek](https://www.howtogeek.com/plex-is-overhauling-custom-metadata-providers/)). An official NFO agent (compatible with Kodi's format) requires server 1.43.1 or later ([support](https://support.plex.tv/articles/using-nfo-metadata-files-with-plex/)).

Collections can be created manually, automatically from metadata (e.g. franchises), or as smart collections (saved filters). Playlists support both manual and smart variants for video, music and photos, per user. Ratings include critic scores (Rotten Tomatoes, IMDb, TMDB), user star ratings, and content ratings (MPAA/TV-PG). Browsing is supported by genres, moods, labels (admin tags also used for sharing restrictions), and people pages spanning the library and Discover.

Discover provides universal search across personal libraries, free Plex content, and "where to watch" availability on other services. A cross-service Watchlist, activity feed, friends, profiles, reviews, and watch history are synced to plex.tv. New social features added in June 2026 include Discussions (comments per title), shareable Lists, Match Score and Alerts ([TechCrunch](https://techcrunch.com/2026/06/03/plex-launches-new-social-features-amid-a-major-price-hike/)).

**[PP]** Automatic object and place tagging for photos *(verify)*. **[PP]** Lyrics (LyricFind) and sonic analysis for music.

### Playback and transcoding

Plex supports three playback modes:

* **Direct Play:** the client plays the file as-is, with no server processing.
* **Direct Stream:** the container is repackaged or incompatible audio is transcoded while video passes through untouched; minimal CPU cost.
* **Transcoding:** Plex's own FFmpeg fork writes HLS/DASH segments. Software transcoding is free. **[PP]** Hardware transcoding supports Intel Quick Sync (Windows and Linux), NVIDIA NVENC/NVDEC, VAAPI on Linux (Intel/AMD), VideoToolbox on macOS, and some NAS and ARM chips. **[PP]** HEVC hardware encoding left preview in January 2025; output defaults to H.264 with HEVC optional.

**[PP]** HDR tone mapping converts HDR10/HLG/Dolby Vision profile 8 to SDR when transcoding, using algorithms including linear, gamma, clip, reinhard and hable ([support](https://support.plex.tv/articles/hdr-to-sdr-tone-mapping/)). In practice this requires hardware transcoding.

Clients have separate home and remote quality settings (Original down to low kbps) with automatic adjustment. The server sets the internet upload speed, a per-user remote bitrate cap, and LAN ranges treated as local.

Subtitles are supported via sidecar files (`.srt`, `.ass`, `.ssa`, `.vtt`, `.smi`, `.sub/.idx`), embedded text and image tracks (PGS/VobSub). Image subtitles or styled ASS usually force a burn-in transcode. OpenSubtitles search and download is available inside the app, with per-user language preferences and "show only forced" modes.

Audio features include track selection, per-user preferred language, stereo downmix, "boost voices", loudness options *(verify)*, and passthrough of AC3/EAC3/DTS/TrueHD/Atmos when the client supports it.

| Feature | Tier |
|---|---|
| Skip intro **[PP]** | Server fingerprints each season's shared opening segment (mainly audio). Intros under 20 seconds or past the halfway point are ignored ([support](https://support.plex.tv/articles/skip-content/)). |
| Skip credits **[PP]** | Detected during scheduled maintenance or on demand via "Analyze", using audio and visual analysis ([support](https://support.plex.tv/articles/credits-detection/)). Community tools like [MarkerEditorForPlex](https://github.com/danrahn/MarkerEditorForPlex) can edit markers. |
| Preview thumbnails ("trickplay") | BIF-style image strips generated during maintenance; free *(verify)*. Chapter thumbnails from embedded chapters also supported. |

Resume position, Continue Watching / On Deck hubs, per-user watched state, "mark watched", and a completion threshold setting are all provided. Watch state and ratings for Plex-matched items sync through plex.tv across servers and streaming services ("Sync My Watch State and Ratings"). Third-party trackers (Trakt, Letterboxd) connect via webhooks or integrations *(verify)*.

### Clients and casting

Plex is available on a wide range of platforms:

* **Web app:** `app.plex.tv` and the server's built-in web client.
* **Desktop:** dedicated apps for Windows and macOS (the older Plex Media Player was retired).
* **Mobile:** iOS/iPadOS and Android; playback has been free since April 2025 ([MacRumors](https://www.macrumors.com/2025/03/19/plex-price-increase/)).
* **TVs and boxes:** Apple TV, Roku, Android TV/Google TV, Fire TV, Samsung Tizen, LG webOS, Vizio, Hisense VIDAA, Xbox, PlayStation. Some apps are "classic" and some the redesigned "new experience".

Casting is supported via Chromecast (from mobile or web), AirPlay (from iOS or system-level), and "Plex Companion" which lets a phone remote-control another Plex client. The server also acts as a DLNA/UPnP media server for smart TVs and consoles, with per-device profiles; there is no resume or state sync over DLNA.

**Plexamp** (music) has been free since 2023 ([feature list](https://www.plex.tv/plexamp/)). Free features include gapless playback, loudness leveling, "sweet fades" crossfade, pre-caching, smart playlists and stations, visualizers, UltraBlur, CarPlay/Android Auto, Chromecast/AirPlay, and Siri. **[PP]** Sonic analysis builds a musical feature vector per track to find sonically similar content; radio and mix features (track/album radio, artist/album mix builders, Sonic Adventure, Guest DJ modes, Sonic Sage LLM playlist builder); listening extras including downloads, lyrics, a 10-band EQ, sample-rate matching, and headless Plexamp on Raspberry Pi.

A standalone **Plex Photos** app provides timeline view, camera upload (auto-backup from phone to library), and memories. Music and photo libraries are returning to the main app after an earlier split ([How-To Geek](https://www.howtogeek.com/plex-photos-music-returning-to-core-app/)).

### Users and sharing

The server is claimed to a plex.tv account; tokens (`X-Plex-Token`) come from that service. Unclaimed or LAN-only access is possible with "allowed without auth" networks. Two-factor sign-in is available. A significant data breach in September 2025 exposed emails, usernames, hashed passwords and authentication data ([BleepingComputer](https://www.bleepingcomputer.com/news/security/plex-tells-users-to-reset-passwords-after-new-data-breach/)).

**Plex Home** supports up to 15 members as either full Plex accounts or managed users (no email or password). Fast user switching and optional four-digit PINs per profile are included. Some Home features (e.g. downloads for Home members) ride on the admin's Plex Pass.

Libraries can be shared with friends, who appear under their own accounts; sharing is configurable per library or per server with selected libraries. **[PP]** Parental controls set a content rating ceiling per managed or shared user (movies and TV separately), plus allow/exclude labels. Plex Pass also allows sharing download permission and extra restrictions ([MacRumors](https://www.macrumors.com/2026/05/19/lifetime-plex-pass-price-increase/)).

### Remote access

Automatic UPnP/NAT-PMP or manual port forwarding (default 32400) is supported. `*.plex.direct` hostnames use Plex-issued TLS certificates, with custom server URLs also available. The **Relay** fallback proxies traffic through Plex servers at a capped bitrate (about 1 Mbps free, 2 Mbps with Plex Pass *(verify)*). Secure-connection settings can be Required, Preferred or Disabled.

Since 2025, remote playback of personal media requires a paid pass: either the server owner has Plex Pass (covering everyone they share with), or the viewer buys a Remote Watch Pass **[RWP]**. Enforcement began on Roku on 26 November 2025 ([Privacy Guides](https://www.privacyguides.org/news/2025/11/26/plex-begins-enforcing-new-restrictions-on-remote-streaming-this-week/)); other TV platforms and third-party API clients follow through 2026. Streaming inside the home network remains free.

### Extras: skip intro, downloads, DVR and live TV

**Downloads [PP]:** offline copies on mobile and desktop, in original or transcoded quality with a server-side transcode queue. Requires Plex Pass on the downloading account or the Home admin's. Planned for 2026: grouping by show and automatically downloading new episodes ([support](https://support.plex.tv/articles/downloads-sync-faq/), [MacRumors](https://www.macrumors.com/2026/05/19/lifetime-plex-pass-price-increase/)).

**Live TV and DVR [PP]:** supported tuners include HDHomeRun and other network tuners, USB/PCIe tuners (Hauppauge), and ATSC 3.0 on some devices. The server does the tuning; clients get a guide grid. EPG data is supplied by Plex for supported countries; elsewhere an XMLTV file can be provided. Recording rules support new episodes only, all episodes, or by channel, with padding, retention (keep N episodes), and duplicate avoidance. Commercial detection with optional removal, conversion on record, and live-TV time-shifting are included ([support](https://support.plex.tv/articles/225877347-live-tv-dvr/)).

**Watch Together:** synchronised co-watching with friends was dropped from mobile and TV apps on 25 February 2025; it remains in the web app "for the foreseeable future" ([PCWorld](https://www.pcworld.com/article/2619590/plex-is-dropping-a-popular-feature-from-its-new-streaming-apps.html)).

**Free ad-supported content (FAST):** thousands of on-demand films and shows from studios including Warner, Lionsgate and MGM, plus 600+ live channels. No server or pass needed; region dependent ([Plex](https://www.plex.tv/watch-free-tv/)). A movie rental store launched in February 2024 (US) ([TechCrunch](https://techcrunch.com/2024/02/07/streamer-plex-launches-its-long-promised-movie-rentals-store)).

### Music and Plexamp

Plexamp is the dedicated music application, free since 2023. Free features include gapless playback, loudness leveling, "sweet fades" (smart crossfade), pre-caching, smart playlists and stations, visualizers, UltraBlur backgrounds, CarPlay/Android Auto support, Chromecast/AirPlay casting, and Siri integration ([feature list](https://www.plex.tv/plexamp/)).

**[PP]** Sonic analysis is the flagship premium feature: the server builds a musical feature vector per track to power radio and mix features (track and album radio, artist and album mix builders), Sonic Adventure (a path between two tracks), Guest DJ modes, and Sonic Sage (an LLM playlist builder). Additional premium listening extras include offline downloads, lyrics, a 10-band EQ, sample-rate matching, and headless Plexamp on Raspberry Pi.

### Admin and dashboards

The server dashboard shows now-playing sessions with the stream decision for each (direct play, direct stream or transcode, and why), and allows killing a stream with a message. **[PP]** Bandwidth and CPU/RAM graphs plus per-user and per-device history are available; Tautulli is the community stats tool.

Settings areas cover General, Remote Access, Agents/Library, Network (LAN ranges, custom URLs, IPv6, secure connections), Transcoder, Languages, DLNA, Extras, Scheduled Tasks, Alerts/notifications, and Authorised devices.

**Scheduled Tasks ("Butler")** run inside a maintenance window: database backup (keeps the last N copies, every 3 days by default) and optimisation, metadata refresh, removal of old bundles and cache, analysis (loudness, sonic, intro and credits markers, preview and chapter thumbnails), and server auto-update.

"Optimize versions" pre-transcodes items into "Optimized for mobile/TV/original" versions stored beside the original; Plex has de-emphasised this *(verify)*.

**[PP]** Webhooks send HTTP POST (multipart with JSON payload and thumbnail) for events including play, pause, resume, stop, scrobble, rate, library new, admin database backup/corruption, device new, and playback started. Set up per account on plex.tv.

The **Plex Media Server HTTP API** returns XML by default (JSON with `Accept: application/json`), authenticated via `X-Plex-Token`. Endpoints cover libraries (`/library/sections`), metadata, search, hubs, playback decisions and transcode sessions (`/video/:/transcode/universal`), timeline/progress (`/:/timeline`, `/:/scrobble`), playlists, collections, butler and preferences. Official docs are at [developer.plex.tv](https://developer.plex.tv/); the community OpenAPI spec is at [plexapi.dev](https://plexapi.dev/Intro). The **plex.tv API** covers accounts, PIN-based device linking (`/api/v2/pins`), resources/server discovery (`/api/v2/resources`), friends and sharing, Home users, watchlist, and the Discover and metadata service. Local network discovery uses the GDM (G'Day Mate) multicast protocol.

Backups: Butler backs up only the SQLite database. A full backup requires copying the "Plex Media Server" data folder while the server is stopped; there is no built-in restore UI. Docker images (`plexinc/pms-docker`) and NAS packages (Synology, QNAP, unRAID) are provided for self-hosting. **[PP]** Plex Dash is a mobile app for administering the server.

### Plex Pass and pricing

Plex Pass is the paid tier that unlocks hardware transcoding, remote streaming, downloads, skip intro/credits, Live TV/DVR, parental controls, automatic online trailers and extras, lyrics and sonic analysis in Plexamp, photo auto-tagging *(verify)*, server dashboard graphs, webhooks, Plex Dash, early-access builds, and a Relay bitrate bump *(verify)*.

| Plan | Price (from April 2025) |
|---|---|
| Monthly | $6.99 per month |
| Yearly | $69.99 per year |
| Lifetime | $249.99 (raised to $749.99 on 1 July 2026) |

Prices increased from $4.99/$39.99/$119.99 on **29 April 2025** ([MacRumors](https://www.macrumors.com/2025/03/19/plex-price-increase/)). The lifetime price rose again to $749.99 on **1 July 2026** ([MacRumors](https://www.macrumors.com/2026/05/19/lifetime-plex-pass-price-increase/), [TechCrunch](https://techcrunch.com/2026/06/03/plex-launches-new-social-features-amid-a-major-price-hike/)).

The **Remote Watch Pass** is a cheaper alternative for viewers who do not want full Plex Pass. It launched at $1.99/month or $19.99/year, rising to **$2.99/month or $29.99/year on 1 June 2026** ([How-To Geek](https://www.howtogeek.com/plex-remote-watch-pass-gets-a-price-increase/)).

The one-time fee to unlock playback in the iOS and Android apps was dropped alongside the April 2025 price increase; mobile playback is now free.

## 3. What people wish Plex had

### Main complaints

**Paywalls and price rises.** By far the most covered grievance. On 2025-03-19, Plex announced its first price rise in a decade: Plex Pass went from $4.99 to $6.99 per month, $39.99 to $69.99 per year, and $119.99 to $249.99 lifetime. Remote playback of users' own media stopped being free, with a new Remote Watch Pass at $1.99 per month or $19.99 per year for non-owners. Enforcement began on the Roku app in late November 2025, with other TV apps and third-party clients following in 2026. On 2026-05-19 (effective 2026-07-01), the lifetime pass tripled again from $249.99 to $749.99, with a new five-year pass at $249.99. AppleInsider called it "Ludicrous". Hardware transcoding remains behind Plex Pass. Sources: [Plex blog](https://www.plex.tv/blog/important-2025-plex-updates/), [MacRumors](https://www.macrumors.com/2025/03/19/plex-price-increase/), [AlternativeTo](https://alternativeto.net/news/2025/3/plex-raises-subscription-prices-up-to-75-and-locks-remote-streaming-behind-a-paywall), [Engadget](https://www.engadget.com/entertainment/streaming/plex-starts-paywalling-remote-streaming-to-tvs-beginning-withits-roku-app-160535590.html), [Privacy Guides](https://www.privacyguides.org/news/2025/11/26/plex-begins-enforcing-new-restrictions-on-remote-streaming-this-week/), [Plex blog (lifetime)](https://www.plex.tv/blog/new-lifetime-plex-pass-pricing/), [AppleInsider](https://appleinsider.com/articles/26/05/19/ludicrous-plex-lifetime-pass-increase-to-74999-is-too-expensive-for-watching-your-owned-media).

**App redesigns and removed features.** The mobile app rewrite, previewed in November 2024 and rolled out on 2025-03-31, drew mixed reviews with reports of bugs, missing features and accessibility problems. Watch Together was dropped from the new apps in February 2025; the request to bring it back is now the second-most-voted Plex feature suggestion at 2,862 votes. Photos and music were split into separate apps around September 2024, then reversed in July 2025 after complaints that the unified app was lost and standalone apps were unavailable on smart TVs. A long-time user thread from 2025-08-14 noted that playlists, Watch Together, downloads and casting had been stripped from mobile and TV apps despite promises they would return by early 2025. The Roku 8.6.4 redesign in September 2025 replaced the sidebar with top navigation; users reported broken playback controls and no rollback option. Plex restored the collapsible side menu in August 2026 after months of backlash. Older removals still cited include plugins, Watch Later, Recommended and Cloud Sync (2018), plus podcasts and web shows (April 2022). Sources: [TechCrunch](https://techcrunch.com/2025/03/31/streaming-service-plex-rolls-out-a-revamped-mobile-app), [Mobile Syrup](https://mobilesyrup.com/2025/04/01/plex-update-rolls-out-for-mobile-reviews-are-mixed/), [Android Authority](https://www.androidauthority.com/plex-watch-together-removed-3529939/), [How-To Geek](https://www.howtogeek.com/plex-photos-music-returning-to-core-app/), [Plex forum thread](https://forums.plex.tv/t/disappointed-long-time-user-features-gone-price-up-still-no-fix/929233), [PiunikaWeb](https://piunikaweb.com/2025/09/17/plex-roku-update-backlash/), [XDA Developers](https://www.xda-developers.com/after-months-backlash-plex-rolling-back-controversial-big-screen-app-redesign/).

**Privacy, social features and telemetry.** In November 2023, the Discover Together "Week in Review" emails sent watch history to people on users' Plex friends lists — anyone a library had been shared with was added as a friend automatically. A forum thread titled it "a MASSIVE breach of privacy and trust". On 2025-01-22, public profiles and reviews were introduced; profiles are findable by default, drawing headlines that Plex "has no idea what users want". Background: in 2017, a privacy policy change removed the opt-out from data collection; Plex backtracked after backlash. Sources: [TechHive](https://www.techhive.com/article/2157803/plex-discover-together-privacy-concerns.html), [Plex forum thread](https://forums.plex.tv/t/discover-together-and-week-in-review-emails-are-a-massive-breach-of-privacy-and-trust/860302), [404 Media](https://www.404media.co/plex-users-fear-discover-together-week-in-review-feature-will-leak-porn-habits-to-their-friends-and-family/), [Engadget](https://www.engadget.com/entertainment/streaming/plex-update-adds-public-reviews-and-profiles-140050631.html), [Android Authority](https://www.androidauthority.com/plex-social-media-pivot-not-what-users-want-3674315/).

**Cloud account dependence, outages and breaches.** A data breach on 2025-09-08 saw emails, usernames, hashed passwords and authentication data stolen; a near-identical breach occurred in August 2022. An outage on 2026-07-14 took down the plex.tv API, guide data and Discover; How-To Geek reported local servers were inaccessible "even on your home network", though readers disputed this for properly configured LAN setups. A recurring theme among switchers is that when Plex's authentication service goes down, users cannot watch their own files. Sources: [BleepingComputer](https://www.bleepingcomputer.com/news/security/plex-tells-users-to-reset-passwords-after-new-data-breach/), [TechCrunch (breach)](https://techcrunch.com/2025/09/09/plex-urges-users-to-change-passwords-after-data-breach/), [How-To Geek](https://www.howtogeek.com/your-plex-server-is-inaccessible-right-now-even-on-your-home-network/).

**Ads, free streaming and Discover clutter.** Plex Pass does not remove ads from Plex's free movies or Live TV, and there is no paid way to remove them. Lifetime-pass users ask to hide the Live TV, On Demand and Discover buttons. "Fully disable Discover & search results from streaming services" has 1,000 votes on the feature-suggestion board (tagged implemented) yet remains a common complaint. Plex's 2023 layoffs of 20 per cent of staff were blamed on the ad market; users read this as the company prioritising ad streaming over personal media. Sources: [Plex support](https://support.plex.tv/articles/frequently-asked-questions-vod/), [Plex forum feature suggestions](https://forums.plex.tv/c/general/feature-suggestions/8/l/votes), [TechCrunch (layoffs)](https://techcrunch.com/2023/06/29/plex-layoffs-advertising-slowdown).

**Metadata and anime.** Forum threads from 2025 describe modern Plex metadata agents as "not fit for purpose", with the new TV agent mixing TMDB and TVDB data within one season, causing episodes to become unmatched after a refresh. Anime users fall back on `.plexmatch` files or community agents. Sources: [Plex forum (metadata)](https://forums.plex.tv/t/yet-another-example-of-why-the-modern-plex-metadata-agents-are-not-fit-for-purpose/932669), [Plex forum (TMDB/TVDB mix)](https://forums.plex.tv/t/plex-series-agent-incorrectly-mixes-tmdb-and-tvdb-data-within-same-season/934586).

**Subtitles.** Forum-level complaints include styled "signs and songs" subtitles out of sync in the new experience, server 1.43.0 putting subtitles out of sync on Apple TV (fixed by downgrading), embedded subtitles running seconds early with the old player (December 2025), and subtitle burn-in forcing CPU-heavy transcodes. Sources: [Plex forum](https://forums.plex.tv/t/subtitles-out-of-sync/908957), [Plex forum (1.43.0)](https://forums.plex.tv/t/subtitles-out-of-sync-plexmediaserver-1-43-0-10492-121068a07/936340).

**Music.** ReplayGain normalisation reportedly "just doesn't seem to work" for third-party clients. Advanced Plexamp features (downloads, Sonic Sage, mixes) are paywalled. Long-standing votes include tag support for robust music organisation (866), multiple-artist support (519), and CUE sheets for FLAC (506). Sources: [Symfonium support](https://support.symfonium.app/t/loudness-normalisation-for-plex/9016), [Plex forum feature suggestions](https://forums.plex.tv/c/general/feature-suggestions/8/l/votes).

**Transcoding and formats.** HEVC hardware encoding reached Plex Pass holders only on 2025-01-22. AV1 playback support is uneven across clients. Dolby Vision to SDR tone mapping using DV metadata remains a feature request. AMD VCE/VCN encoding has 848 votes. Sources: [Plex support](https://support.plex.tv/articles/115002178853-using-hardware-accelerated-streaming/), [Plex forum (Dolby Vision)](https://forums.plex.tv/t/tone-map-hdr-to-sdr-with-dolby-vision-100-nit-l2-trim/863515).

### Most wanted features

The table below lists the most requested features across Plex and Jellyfin communities, using live vote counts where available. Figures come from the [Plex forum feature suggestions](https://forums.plex.tv/c/general/feature-suggestions/8/l/votes) (sorted by votes) and the [Jellyfin feature tracker](https://features.jellyfin.org/) ("most wanted" view).

| Feature | What users want | Votes / strength of signal |
|---|---|---|
| Comics, books and PDF reader | A built-in reader for comics, books and PDFs in the library | 3,180 (Plex) |
| Watch Together | Bring back shared watching sessions removed from new apps | 2,862 (Plex) |
| Offline mode on Android | Download content for offline playback on mobile | 1,812 (Jellyfin) |
| Google Home integration | Cast and control playback via Google Home devices | 2,461 (Plex) |
| Audiobook support | First-class audiobook metadata, playback and organisation | 2,261 (Plex); 855 (Jellyfin) |
| Remove from Continue Watching | Let users dismiss items they do not want to resume | 1,714 (Jellyfin) |
| Watchlist | A user-curated list of titles to watch later | 1,287 (Jellyfin) |
| Better playlists | Improved playlist creation and management | 1,425 (Plex) |
| OIDC/OAuth SSO | Single sign-on via external identity providers | 1,181 (Jellyfin) |
| Maximum quality by default | All clients stream at the highest available quality without manual adjustment | 1,289 (Plex) |
| Two-factor authentication | 2FA on user accounts for security | 1,095 (Jellyfin) |
| Disable Discover & streaming results | Remove third-party content from the home screen and search | 1,000 (Plex, tagged implemented but still complained about) |
| Pre-transcoding | Transcode files ahead of time for weak clients | 978 (Jellyfin) |
| Watched history management | Import, export and control of viewing history | 828 (Jellyfin); also a recurring theme across all three platforms |
| Offline sync | Sync downloaded content across devices | 813 (Jellyfin) |
| Music tag support | Robust music organisation via ID3 tags | 866 (Plex) |
| AMD VCE encoding | Hardware encoding on AMD GPUs | 848 (Plex) |
| Smart playlists | Dynamic playlists based on rules and metadata | 587 (Jellyfin) |
| Automatic subtitle synchronisation | Fix out-of-sync subtitles without manual intervention | 687 (Plex) |
| PseudoTV (virtual channels) | Generate virtual TV channels from personal library content | 623 (Plex) |
| Gapless playback | Seamless transitions between tracks in music libraries | 645 (Jellyfin) |
| Personal ratings | User-specific star or score ratings on items | 450 (Jellyfin) |

### Where The Den can do better

The report maps user wishes to concrete opportunities for a new server. Each bullet below turns a documented complaint or request into a specific Den feature:

- **Never paywalled, never phones home.** Remote streaming, hardware transcoding and downloads are all free. No telemetry, no social features, no ads. This promise should be stated explicitly — each Plex incident sends users looking for exactly it.
- **Zero-configuration secure remote access with no cloud account.** Relay-grade ease of setup, using existing device tokens and certificate pinning as a base. QR or code pairing (as in Jellyfin's Quick Connect request) plus invite links would cover the gap that keeps users on Plex.
- **Local accounts with OIDC and 2FA.** Reuse the existing request and quota user system so "sharing without third-party accounts" comes almost free. Invite or sign-up flows let library owners control who joins.
- **Offline downloads, including transcoded downloads, done well from the start.** This is the number-one Jellyfin request (1,812 votes) and was stripped from Plex's new apps — a gap The Den can own.
- **Management tightly joined to playback.** A unique advantage of this product: a request becomes a watchlist entry, then a download, then a notification. Pre-transcoding on import for weak clients. Missing-episode display carried over from the Sonarr-style monitor. Correct versions and editions since the manager already knows the release. Anime absolute ordering preserved from the import mapping.
- **Viewer-level controls.** Remove items from Continue Watching (1,714 Jellyfin votes), personal ratings (450 Jellyfin votes), per-user hide, watch-history import and export supporting Trakt, Plex and Jellyfin formats so users can migrate without losing history.
- **Admin tools Plex ignores.** Kill a user's stream (402 Jellyfin votes), message users from the server (1,202 Plex votes), per-user bitrate and stream limits tied to existing quotas, and default quality settings (1,289 Plex votes).
- **Watch-together invite links** in the web client. Watch Together is the second-most-voted Plex feature at 2,862 votes; Jellyfin users want SyncPlay invite links at 263 votes. The Den can offer this natively.
- **Audiobooks, podcasts and books/comics.** The top Plex vote (3,180 for comics/books/PDFs; 2,261 for audiobooks) plus strong Jellyfin support (855 for audiobooks). Podcasts were removed from Plex in April 2022.
- **Music done properly.** Gapless playback (645 Jellyfin votes), ReplayGain volume normalisation, multi-artist tag support (519 Plex votes), smart playlists (587 Jellyfin votes), and CUE sheet handling for FLAC (506 Plex votes).
- **Format handling that works.** Correct Atmos, DTS:X and DTS-HD MA track labels (700 Plex votes), automatic subtitle synchronisation (687 Plex votes), Dolby Vision-aware tone mapping to SDR, AV1 support, and AMD VCE/VCN encoding (848 Plex votes).
- **Stable, customisable interface.** Let users choose what the home screen shows. Do not force redesigns or remove features without warning — Plex's 2024–2026 redesign reversals are the cautionary tale.

## 4. Jellyfin and Emby

### Current versions and licences

| | Jellyfin | Emby |
|---|---|---|
| Latest stable | **v12.1** (tagged 2026-09-15); v12.0 on 2026-09-08; last 10.x was 10.11.11 (2026-06-06) | **4.10.0.40** (2026-09-08); before that 4.9.5.0 (2026-05-18) |
| Runtime | C#, **.NET 10** in 12.0 | C#, .NET 8 since 4.9.1.80 (Sept 2024) |
| Licence | GPL-2.0 (server) | Proprietary since 3.5.3 / 4.x (Dec 2018) |

Jellyfin changed its version numbering: 12.0 comes straight after 10.11, with no 10.12. The Emby Server 4.10 release is mostly home-screen and UI polish ("Spotlight" and "Dynamic Media" sections), plus better HDR hardware transcoding.

Sources: [Jellyfin tags](https://github.com/jellyfin/jellyfin/tags), [Jellyfin blog](https://jellyfin.org/posts/), [Emby.Releases](https://github.com/MediaBrowser/Emby.Releases/releases), [Emby 4.10.0.40 thread](https://emby.media/community/topic/149571-new-emby-server-410040-released/)

### Features and what is paid

**Jellyfin** has no paywall at all. Its core covers movies, shows, music, music videos, home videos, photos, books (native since 12.0), live TV and DLNA (moved to a first-party plugin in 10.9). Transcoding uses jellyfin-ffmpeg (8.1 in 12.0) with hardware support for NVENC, QSV, VA-API, AMF, VideoToolbox and RKMPP, plus HDR tone mapping via 3D LUT. Trickplay thumbnails are built in since 10.9; SyncPlay is room-based watch-together. Offline downloads depend entirely on the client — there is no server-side sync job.

However, several commonly expected features still require a third-party or separate plugin: intro and credits detection ([intro-skipper](https://github.com/intro-skipper/intro-skipper) or [TheIntroDB](https://github.com/TheIntroDB/jellyfin-plugin)), SSO/OIDC, Subsonic API, webhooks and notifications, OpenSubtitles, TVDB and AniDB metadata, playback reporting, InfuseSync for Infuse's library mode, and DLNA (first-party but no longer in the core). Plugins break on every major version: all 10.11 plugins must be rebuilt for .NET 10 before they load on 12.0.

**Emby Premiere** costs **$4.99 a month, $54 a year or $119 lifetime**, for up to 30 devices (bigger tiers sold separately; often discounted to $99 lifetime). ([Premiere page](https://emby.media/premiere.html))

Premiere unlocks: hardware transcoding, DVR, offline downloads and conversion, Cinema Intros, backup and restore, Folder Sync, CarPlay and Android Auto, voice assistants, the cover-art plugin, intro skip, and "the latest Emby TV app". Since December 2024, TV apps can play free on up to **5 TV devices per server**; beyond that needs Premiere. ([blog](https://emby.media/community/blogs/entry/582-new-free-playback-and-increased-device-limits/)) Mobile playback, iOS in particular, still needs Premiere or an in-app unlock. Charging for hardware transcoding is the most-cited complaint.

Emby's transcoding engine is weaker than Jellyfin's: a February 2026 forum thread measured about 30 fps on Emby against about 80 fps on Jellyfin on the same hardware, reporting FFmpeg 5.1 versus 7.x, CPU tone mapping and unnecessary AAC audio transcodes. Emby staff answered that their ffmpeg fork carries backports and a new build was coming to beta in July 2026. The user's numbers are not independently verified. ([thread](https://emby.media/community/topic/146152-hard-comparison-why-is-embys-transcoding-engine-so-far-behind-jellyfin-and-why-im-switching-back/))

### Architecture lessons

**EF Core over SQLite regressions.** Jellyfin used raw SQLite calls up to 10.10, with a separate `jellyfin.db` (EF Core for users and activity) and `library.db` (hand-written SQL). Version 10.11 moved the library to EF Core, banning raw SQL including in plugins, adding versioned migrations and aggressive in-memory caching. The growing pains were severe:

- Scans became about 10x slower in 10.11.0 ([#15070](https://github.com/jellyfin/jellyfin/issues/15070)).
- The home screen became slow ([#15097](https://github.com/jellyfin/jellyfin/issues/15097)), as did folder-based libraries ([#15141](https://github.com/jellyfin/jellyfin/issues/15141)).
- In 12.0, a single `GET /UserViews` on a 311k-item library allocated about 600 MB/s until the server was killed for running out of memory — an EF Core query loading several related collections into one huge join ([#17871](https://github.com/jellyfin/jellyfin/issues/17871), opened 2026-09-08).
- Speeding up the scanner has been pushed back to 13.0 ([State of the Fin May 2026](https://jellyfin.org/posts/state-of-the-fin-2026-05-24/)).

**Lesson for The Den:** an ORM over SQLite needs deliberate query shaping for large libraries. Long-standing "database is locked" errors were mostly caused by a scheduler bug launching too many parallel scan writes; 10.11 fixed that and added optional locking modes (NoLock default, Optimistic with Polly retries, Pessimistic with ReaderWriterLockSlim), though lock errors persisted in 10.11.0 ([#15057](https://github.com/jellyfin/jellyfin/issues/15057), [#15166](https://github.com/jellyfin/jellyfin/issues/15166)).

**DeviceProfile and PlaybackInfo flow.** The client sends a DeviceProfile (containers, codecs and profile/level conditions it can play) to `POST /Items/{id}/PlaybackInfo`. The server replies with MediaSources stating DirectPlay, DirectStream (remux) or Transcode, with a TranscodingUrl. Playback then goes through `/Videos/{id}/stream` (range requests) or HLS `master.m3u8`, using segmented fMP4 or TS from jellyfin-ffmpeg. Clients report progress through `/Sessions/Playing`, `/Progress` and `/Stopped`, plus a WebSocket for remote control and SyncPlay. Buggy device profiles are a major source of needless transcodes — for example, Android TV 0.19.2 marked HEVC and DTS as unsupported ([#5093](https://github.com/jellyfin/jellyfin-androidtv/issues/5093)).

**Plugin fragility.** Jellyfin plugins are .NET assemblies loaded in-process from a repository manifest. They are tied to the server's ABI and break on every major version, which is why all 10.11 plugins needed rebuilding for .NET 10 before loading on 12.0.

### Clients and weak spots

| Platform | Jellyfin official | Jellyfin third-party | Emby |
|---|---|---|---|
| Web | jellyfin-web ("Modern" layout default in 12.0); Jellyfin Vue (beta) | – | Web app (free) |
| Android | Jellyfin Android 2.7 (webview shell plus native player, Android Auto) | **Findroid** (native video), **Finamp** (music; redesign in beta), Streamyfin, Fladder, Moonfin (paid) | Emby for Android (Premiere or unlock) |
| Android TV / Fire TV | Jellyfin Android TV 0.19.x (0.20 waiting on 12.0) | **Wholphin**, Moonfin | Free on 5 TV devices |
| iOS | Jellyfin iOS 1.7 (webview), **Swiftfin** | Streamyfin, **Infuse** (paid), Fladder | Premiere or unlock |
| Apple TV | **Swiftfin tvOS reached the App Store only on 2026-07-16** ([discussion](https://github.com/jellyfin/Swiftfin/discussions/1294)) | **Infuse** (the long-standing de facto choice), Moonfin | Free |
| Roku | Jellyfin Roku 3.x (3.0 in Mar 2025) | Moonfin | Free |
| webOS / Tizen | Official apps (Tizen now in Samsung's store for Tizen 6+) | Moonfin, Wholphin (webOS) | Free |
| Xbox | Jellyfin Xbox 0.9.x | – | Emby Theater |
| Desktop | **Jellyfin Desktop 2.0** (Qt6 + mpv, Dec 2025); a Chromium Embedded Framework rewrite with native HDR is under way | Jellyfin MPV Shim, Feishin and Supersonic (music), jftui | Emby Theater |
| Kodi | Jellyfin for Kodi, JellyCon | – | Emby for Kodi |

**Jellyfin weak spots:** Apple TV (Swiftfin tvOS only two months old at time of writing; Infuse fills the gap); official Android TV app direct-play regressions; official mobile apps wrapping the web UI; desktop client rewritten twice. The best clients are often third-party ([XDA](https://www.xda-developers.com/tried-every-jellyfin-client-these-best-ones-each-platform/)).

**Emby weak spots:** Apps are more consistent across platforms, but mobile playback is paywalled.

### Strengths and common complaints

**Jellyfin strengths:**
- Free, with no accounts or phone-home.
- Better hardware transcoding and tone mapping than Emby, on a current ffmpeg.
- Active releases, and a large third-party client ecosystem.
- Books and comics in the core (12.0).

**Jellyfin complaints:**
1. **Client quality is inconsistent.** People often recommend third-party clients over the official ones. Swiftfin tvOS was very late, and device-profile bugs cause needless transcodes.
2. **Performance and stability after the EF Core move:** slow scans and slow home screen in 10.11; out-of-memory crashes on huge libraries in 12.0; lock errors; one-way migrations (12.0 cannot be rolled back without restoring a backup); mandatory full rescan after upgrading.
3. **Breaking API churn in 12.0:** legacy auth headers and `?api_key=` disabled by default; `/emby/` and `/mediabrowser/` route prefixes removed; endpoints removed (EasyPassword, CriticReviews, NetworkShares and others); `GetItems` recursion changed. Many third-party tools broke: Homepage widgets ([#7113](https://github.com/gethomepage/homepage/issues/7113)), Music Assistant ([#6369](https://github.com/music-assistant/support/issues/6369)) and Seerr ([PR #3502](https://github.com/seerr-team/seerr/pull/3502)). Enforcement was briefly reverted during 12.0 testing because official clients were not ready yet.
4. **Music is second-class.** Large music libraries slow things down, and Subsonic support comes only from community plugins ([selfhosting.sh](https://selfhosting.sh/compare/navidrome-vs-jellyfin/)).
5. Plugins are fragile across versions; there is no native intro detection; remote access is do-it-yourself (reverse proxy, no relay).
6. Many small files in /config (images, trickplay, chapter images) hurt performance when /config is not on an SSD.

**Emby strengths:**
- Polished, consistent UI.
- Built-in intro skip and server-side sync and conversion.
- Low lifetime price compared with Plex.
- Emby Connect makes remote login easier.

**Emby complaints:**
- Core features such as hardware transcoding sit behind the paywall.
- Closed source and a small development team.
- Older ffmpeg and slower transcoding (unverified user measurements).
- Few visible big features: 4.10 is mostly home-screen work.
- A defensive forum culture.
- Device-limit confusion.

### Their APIs as compatibility targets

#### Jellyfin API: feasible, but aim at a narrow slice of 12.x

**Documentation and stability.** Documentation is decent (OpenAPI/ReDoc at api.jellyfin.org, plus generated SDKs), but the API is **not versioned or frozen**. Version 12.0 was a deliberate cleanup; the team says further breaking changes are held for **13.0**, giving clients roughly a year of stability. The TypeScript SDK changelog for 12.0 notes "a lot of APIs renamed or moved." Much of the real contract is undocumented behaviour: which fields clients actually read, DeviceProfile semantics, WebSocket messages and the quirks of each client.

**Target the modern form only.** Use header `Authorization: MediaBrowser Client="", Device="", DeviceId="", Version="", Token=""`. The server allows **one access token per DeviceId** ([auth gist](https://gist.github.com/nielsvanvelzen/ea047d9028f676185832e51ffaf12a6f)). No `/emby` prefix. Older third-party clients may still send `X-Emby-Token`, so accept both for compatibility.

**Minimum surface for the video clients** (Findroid, Swiftfin, Streamyfin, Infuse Direct Mode). Endpoint names below come from the API as known; verify each against the 12.x OpenAPI before building:
- Discovery and login: `GET /System/Info/Public`; `POST /Users/AuthenticateByName` (and optionally Quick Connect); `GET /Users/Me`.
- Browsing: `/UserViews` (library views); `GET /Items` with `ParentId`, `IncludeItemTypes`, `Recursive`, `SortBy`, `Fields`, `StartIndex`/`Limit` and filters; `GET /Items/{id}`; `/Shows/{id}/Seasons`, `/Shows/{id}/Episodes`, `/Shows/NextUp`, `/UserItems/Resume`, `/Items/Latest`; images: `/Items/{id}/Images/{type}`.
- Playback: `POST /Items/{id}/PlaybackInfo` (DeviceProfile negotiation); `/Videos/{id}/stream` with range requests; optionally HLS `master.m3u8` for transcodes; subtitle streams.
- State: `/Sessions/Playing`, `/Progress`, `/Stopped`; played and favourite toggles; `/MediaSegments/{id}` for intro skip.
- A WebSocket at `/socket` is expected by some clients; stubbing keep-alives may be enough.
- LAN auto-discovery: Jellyfin answers a UDP broadcast on port 7359 (unverified).

**Precedents.** All are young and small. None proves wide client compatibility:
- [jellyfin-rs](https://github.com/dydydd/jellyfin-rs) (Rust, GPL-2.0): about 268 commits and 3 stars. Implements auth, browsing, playback, sessions, images, collections and `/emby` prefixes. **Transcoding and HLS are not implemented**, and it names no tested clients.
- [jellyrin](https://github.com/alseif0x/jellyrin) (Rust): serves the stock jellyfin-web.
- [Stremfin](https://github.com/hfip/Stremfin) (**Python/FastAPI**, MIT, 8 commits): emulates the subset that **Infuse and VidHub** need — `/System/Info/Public`, `AuthenticateByName`, `/Items`, stream redirect, image and subtitle proxies. States that season navigation and playback are "under continuous optimization", and accepts any password. It is the closest architectural match to The Den and shows a small subset can satisfy Infuse.
- Plugins such as [Subfin](https://github.com/williamkray/subfin-plugin) and [jellysub](https://github.com/nvllsvm/jellysub) go the other way, translating Subsonic to Jellyfin. They are useful as a mapping reference.

**Risks specific to The Den:**
1. **Pinned self-signed HTTPS.** Third-party clients generally expect a publicly trusted certificate or plain HTTP on the LAN; they have no way to pin The Den's certificate. Test Swiftfin and Infuse (Apple ATS rules) and Findroid (Android network security config) early. Expect to need a LAN HTTP listener or a trusted-certificate option for the compatibility port.
2. **Transcoding.** Without DeviceProfile-aware transcoding, compatibility is really "direct play only". That is workable for Infuse, which decodes almost everything locally, but weak for Swiftfin, Roku and web.
3. **Moving target.** Pin to a specific server version reported by `/System/Info/Public` (clients check it; Android requires 10.10+) and add contract tests using recorded traffic from each client.
4. **Auth mapping.** Map The Den's device tokens onto Jellyfin's one-token-per-DeviceId model, and keep quotas separate from API tokens.

**Verdict:** worth doing as a separate compatibility layer with Infuse and Findroid as first targets, then Swiftfin, and web last. Do not treat it as The Den's primary API.

#### OpenSubsonic: the easier win for music

- The Subsonic 1.16.1 base is frozen.
- **OpenSubsonic** adds optional, discoverable extensions through `getOpenSubsonicExtensions`, API-key auth, JSON, lyrics, transcoding decisions, playback reporting and an OpenAPI schema. It is collaboratively maintained and backward-compatible by design. ([OpenSubsonic docs](https://opensubsonic.netlify.app/docs/))
- **Many precedents:** at least 11 servers (Navidrome, gonic, Ampache, LMS, Nextcloud Music, Supysonic and others) and many mature clients (Symfonium, Feishin, Amperfy, Supersonic, Tempus, and more listed by [Navidrome](https://www.navidrome.org/apps/)).
- The surface is small and read-mostly: browsing by ID3 tags, `stream`, `getCoverArt`, `scrobble`, playlists, `search3`.
- Clients tolerate partial implementations, and CarPlay and Android Auto come for free through those clients.
- For The Den, which is video-first, OpenSubsonic gives a better music experience than trying to satisfy Finamp through the Jellyfin API.

### Licensing

**Emby's closure and the Jellyfin fork.** Emby started as the GPL project Media Browser, renamed Emby in 2015. People found likely GPL violations in 2017: closed components sat inside a GPL codebase. On **2018-12-08** Emby announced that 4.x would be closed, relicensed from 3.5.3. Luke Pulverenti's reason was paid third-party additions they could not open. Jellyfin forked the last GPL code the same week and released **3.5.2 on 2018-12-30**, then 10.0.0 in January 2019. ([Jellyfin about](https://jellyfin.org/docs/general/about/), [Wikipedia](https://en.wikipedia.org/wiki/Jellyfin))

**What GPL-2.0 means for The Den.** (This is not legal advice.)
- **Copying Jellyfin server code** (C#) into The Den would make that work GPL-2.0 when distributed. Porting it to Python counts as a derivative work too. Reimplementing from behaviour and the public API docs is the safer path.
- **Talking to the API** or **implementing a compatible API** does not make The Den a derivative of Jellyfin. The same applies to a server that clients talk to. Use your own route and schema code, not generated server stubs copied from GPL source.
- The OpenAPI JSON is generated from GPL code, so keep any vendored copy as reference data and ask for legal review if The Den is proprietary. If The Den is itself open source, GPL-compatible licences remove most of the worry.
- **Client SDKs** are LGPL-3.0 (Kotlin) and MPL-2.0 (TypeScript). The Den's own KDE and Android apps could use them without being forced into GPL. For the Kotlin SDK, LGPL still requires that it can be relinked or replaced.
- Two community Rust servers, [jellyfin-rs](https://github.com/dydydd/jellyfin-rs) and [jellyrin](https://github.com/alseif0x/jellyrin), chose GPL-2.0.

### Side-by-side summary

| | Jellyfin | Emby | Plex (context) |
|---|---|---|---|
| Cost | Free | Hardware transcoding, DVR, sync and intro skip need Premiere ($119 lifetime) | Pass, higher since 2025; remote playback paywalled |
| Source | GPL-2.0 | Closed since Dec 2018 | Closed, cloud account required |
| Transcoding | Best of the three on current ffmpeg (8.1); hardware tone mapping | Older ffmpeg fork; reported slower | Strong; Pass needed for hardware |
| Intro skip | Core segment API plus third-party detection | Built in (Premiere) | Built in (Pass) |
| Offline | Per client (Android 2.7, iOS 1.7, Findroid) | Server-side sync and convert | Downloads (Pass) |
| Weakest point | Client quality, 10.11/12.0 performance regressions, API churn | Paywall, slow development, transcoding | Account and cloud dependence, price |
| API as a target | Documented OpenAPI; broke in 12.0, held stable until 13.0; a few tiny precedents | Legacy-compatible but stale docs; closed | Proprietary; not a realistic target |
| Music | Second-class; Subsonic only via plugins | Adequate | Plexamp is strong |

## 5. Architecture

### Library scanning and probing

The server discovers media by running `ffprobe` as a subprocess at import time:

```
ffprobe -show_streams -show_format -show_chapters -of json <file>
```

The JSON output is stored in SQLite so that every item carries its stream list, format metadata, chapter marks and HDR type. Running ffprobe externally means a probe failure cannot crash the FastAPI process. PyAV 17.x (BSD-3-Clause) may be used for small in-process tasks such as reading keyframe positions or grabbing single frames, but it must not handle live transcoding ([PyAV docs](https://pyav.basswood-io.com/docs/stable/overview/installation.html)).

The database model follows the report's recommendations. A `playback_state` table tracks per-user progress:

```
playback_state(user_id, item_id, position_ms, duration_ms, played bool,
               play_count, last_played_at, updated_at, device_id)
```

Clients emit `start`, periodic `progress` (roughly every 10 seconds and on pause or seek), and `stop`. An item is marked as played once playback passes approximately 90 per cent or the credits segment begins. Resume points under roughly 2 per cent or 60 seconds are cleared. Conflicts resolve by last-write-wins on `updated_at`, which suffices for a single household. Offline Android plays queue events with client timestamps and replay them when connectivity returns.

### Playback decision engine

The server selects the best delivery mode in order of preference:

1. **Direct play:** serve the original file via HTTP Range requests (FastAPI `FileResponse` handles this). Used when container, video codec profile/level/bit depth/HDR, audio codec and channels, subtitle format and bitrate all fit the client's capabilities.
2. **Direct stream / remux:** copy the video stream, transcode audio if necessary (for example DTS or TrueHD to AAC or Opus), repackage into HLS fMP4 segments.
3. **Full transcode:** encode to H.264 8-bit for universal compatibility, or HEVC/AV1 when the client supports it and the GPU can encode it.

Client capability profiles follow Jellyfin's `DeviceProfile` shape: `DirectPlayProfiles` (container plus codecs), `TranscodingProfiles` (ordered targets), `CodecProfiles` (conditions on level, bit depth, width, VideoRangeType) and `SubtitleProfiles` (external, embed, encode, hls). The server walks these profiles in order to pick the best mode ([DeviceProfile.cs](https://github.com/jellyfin/jellyfin/blob/master/MediaBrowser.Model/Dlna/DeviceProfile.cs), [stream selection overview](https://deepwiki.com/jellyfin/jellyfin/3.3-dlna-and-stream-selection)). Web clients detect support with `MediaSource.isTypeSupported` and `MediaCapabilities.decodingInfo`; Android builds the profile from `MediaCodecList`; the KDE app uses a static profile based on its FFmpeg backend.

Bandwidth adaptation starts simple: one rendition per transcode, chosen from a client-reported or measured bitrate, with a quality menu that restarts the job. True ABR (a multivariant playlist with parallel encodes) multiplies GPU and CPU cost and is deferred unless demand arises.

### Transcoding pipeline

ffmpeg runs as an external subprocess via `asyncio.create_subprocess_exec`, not in-process through PyAV. This isolates crashes, makes killing a job on seek or stop a matter of terminating the process, ensures hardware filters work exactly as documented, and keeps GPL-3.0 code separate from The Den's own licence. Arch's ffmpeg 2:9.0.1-4 (GPL-3.0-only) covers VAAPI, QSV, NVENC, libplacebo tone mapping and more ([Arch package](https://archlinux.org/packages/extra/x86_64/ffmpeg/)).

HLS is the streaming format; DASH adds nothing The Den needs. Segments use fMP4 (CMAF) via `-hls_segment_type fmp4`, which HEVC in HLS basically requires. MPEG-TS remains a fallback for older televisions.

The on-demand segmentation strategy writes a VOD playlist up front with fixed-length segments (for example 6 seconds) covering the whole duration, then starts ffmpeg at the segment the client requests. When a seek lands far ahead of the encoder, the server kills ffmpeg and restarts it with `-ss <segment_start>`, `-start_number N`, `-output_ts_offset` and forced keyframes (`-force_key_frames expr:gte(t,n_forced*6)`), so cuts align with the playlist. The pipeline throttles or pauses ffmpeg when it gets too far ahead of the player and cleans up segments behind the playhead.

Remux is problematic because `-c:v copy` can only cut on source keyframes, which are irregular. An accurate playlist requires first scanning keyframe positions (via PyAV or `ffprobe -skip_frame nokey`). Jellyfin still has open bugs here: remux plus mid-file seek desynchronises the playlist from ffmpeg's cuts and stalls playback ([#17966](https://github.com/jellyfin/jellyfin/issues/17966)). Jellyfin logs "Current HLS implementation doesn't support non-keyframe breaks". Budget real time for this.

Audio downmix uses `-ac 2` with a proper `pan=stereo|FL<…` or `aresample=matrix_encoding=dplii`; plain `-ac 2` from 5.1 often makes dialogue too quiet, so a centre-channel boost option is recommended. Encoders are ffmpeg's native `aac` (free to distribute) or `libopus`. Surround passthrough (AC3/EAC3) occurs only when the client profile permits it.

### Hardware acceleration and HDR tone mapping

Jellyfin recommends QSV for Intel, VA-API for AMD and NVENC for NVIDIA ([Jellyfin HW accel docs](https://jellyfin.org/docs/general/post-install/transcoding/hardware-acceleration/)). Frames should stay on the GPU: decode, scale, tone-map and encode there (for example `-hwaccel vaapi -hwaccel_output_format vaapi … scale_vaapi … h264_vaapi`; `-hwaccel cuda … scale_cuda … h264_nvenc`; `-hwaccel qsv … vpp_qsv … h264_qsv`). Any CPU filter in the middle (subtitle burn-in, some tone mapping) forces a download and upload at significant cost.

The server probes hardware at startup by running `vainfo`, `ffmpeg -hide_banner -encoders` and a one-second test encode per candidate, storing what actually works before falling back to libx264 `-preset veryfast`. FFmpeg 8.0 added Vulkan compute encoders (AV1) ([Phoronix](https://www.phoronix.com/news/FFmpeg-8.0-Released)), which are promising but not yet a baseline.

HDR-to-SDR tone mapping options include `tonemap_vaapi` / `vpp_qsv` (Intel), `libplacebo` on Vulkan (AMD/NVIDIA/Intel; best quality), `tonemap_opencl`, or the CPU chain `zscale=t=linear…,tonemap=hable,zscale=…` (very slow at 4K). Dolby Vision profile 5 needs special handling. Jellyfin still has libplacebo trouble: dark output on AMD because the peak setting is ignored on the Vulkan path ([#17996](https://github.com/jellyfin/jellyfin/issues/17996)), and general libplacebo failures ([jellyfin-ffmpeg #546](https://github.com/jellyfin/jellyfin-ffmpeg/issues/546)). Expect per-GPU tuning.

### Subtitles

Text subtitles (SRT, embedded mov_text/SubRip) are converted to WebVTT with ffmpeg, cached and served as a sidecar file or an HLS subtitle rendition. ASS/SSA styling is lost in WebVTT; the options are burn-in via the `subtitles=` filter through libass (CPU only, forces a transcode), or client-side rendering with JASSUB (libass in WASM) on the web. Media3 and Qt can accept ASS directly.

PGS/VobSub (image-based subtitles) require burn-in with `overlay` (CPU, or `overlay_vaapi` / `overlay_cuda` after conversion). The web alternative is a PGS renderer in JavaScript. Burn-in is the most common reason a direct-playable file ends up transcoded.

### Intro and credits detection, media segments, trickplay

Intro detection follows the Intro Skipper approach: take the first roughly 25 per cent (capped at around 10 minutes) of each episode's audio in a season, fingerprint it with Chromaprint (`-f chromaprint -fp_format raw` muxer in ffmpeg, `fpcalc`, or pyacoustid — MIT; Chromaprint is LGPL-2.1), compare episode pairs by sliding one fingerprint over the other and counting matching 32-bit hashes by Hamming distance, find the longest shared run of 15 seconds or more, then snap to nearby silence (`silencedetect`) or chapter marks. Writing this independently is a few hundred lines of numpy and needs no GPL code ([Chromaprint](https://github.com/acoustid/chromaprint), [pyacoustid](https://github.com/beetbox/pyacoustid)).

Credits detection checks chapter names ("Credits", "End Credits"), then black frames (`blackdetect` / `blackframe`) near the end, then audio fingerprinting of the last N minutes. Accuracy is expected at roughly 80-90 per cent on television and much less on films; users must be able to correct segments in the UI.

Chapters use embedded data from `ffprobe -show_chapters`; otherwise they are synthesised every 5-10 minutes with a thumbnail per chapter from `ffmpeg -ss T -frames:v 1`.

Trickplay generates tiled JPEG sprite sheets at a fixed interval:

```
ffmpeg -skip_frame nokey -i f -vf "fps=1/10,scale=320:-2,tile=10x10" -q:v 5 out_%03d.jpg
```

A small JSON manifest (interval, tile size, sheet count) is stored alongside the sprites. Generation runs in a background queue at low CPU priority (`nice`/`ionice`) after import. Roku requires BIF format, which can be generated from the same JPEGs.

Media segments — typed ranges such as Intro, Outro, Recap, Preview and Commercial — are stored per item following Jellyfin's data model ([docs](https://jellyfin.org/docs/general/server/metadata/media-segments/)).

### Players per client and pinning concerns

**Web:** hls.js v1.7.3 (released 2026-09-11) for Chrome, Firefox and Edge; Safari/iOS use native HLS ([hls.js](https://github.com/video-dev/hls.js/)). iOS 17.1+ has Managed Media Source, which hls.js supports. HEVC on Linux Chrome is hardware-only via VA-API; Chrome has no software HEVC decoder ([StaZhu guide](https://github.com/StaZhu/enable-chromium-hevc-hardware-decoding)), so default web transcodes to H.264. Subtitles use `<track>` WebVTT or hls.js subtitle renditions.

**Android:** Media3 ExoPlayer 1.11.0 (July 2026) with `HlsMediaSource` ([release notes](https://developer.android.com/jetpack/androidx/releases/media3)). The app passes its existing pinned OkHttp client through `OkHttpDataSource.Factory`, so segment requests reuse the pinned certificate and an auth header — no query token is needed. ASS, PGS and SSA subtitles work; direct play covers most MKV files. Also supports Android TV and Fire TV with a D-pad/leanback UI.

**KDE (Qt 6 QML):** QtMultimedia `MediaPlayer` on the FFmpeg backend. Qt 6.11 bundles FFmpeg 7.1.3; VA-API hardware decoding exists but GPU texture conversion is off by default ([advanced FFmpeg config](https://doc.qt.io/qt-6/advanced-ffmpeg-configuration.html)). It is unverified whether custom HTTP headers or self-signed TLS pinning can be set for network media in QtMultimedia. Likely workarounds are a signed query-string URL (see "Stream security" below), a local loopback proxy in the client that performs the pinned fetch, or libmpv through a QML item (mpv is GPL/LGPL and handles subtitles and HDR better). This should be prototyped early; mpv is the more capable desktop player.

### Casting and certificate problems

**Chromecast:** the free Default Media Receiver (app ID `CC1AD845`) plays HLS/MP4 with WebVTT and needs no registration. A styled or custom receiver costs $5 for one-time developer console registration ([Cast registration](https://developers.google.com/cast/docs/registration)), which would break the "no paid" rule, so stick to the default receiver. The hard blocker is that Cast devices reject self-signed HTTPS — Jellyfin users hit exactly this ([jellyfin #1725](https://github.com/jellyfin/jellyfin/issues/1725), [CastVideos-chrome #24](https://github.com/googlecast/CastVideos-chrome/issues/24)). The receiver also needs CORS headers on the playlist and segments. Options include a LAN-only plain-HTTP media listener on a second non-80/443 port restricted to signed short-lived URLs and RFC 1918 addresses, or a real certificate (Let's Encrypt DNS-01 on a domain Liam owns). The Cast Web SDK sender runs only in Chrome; Android needs the Play Services Cast framework (proprietary but free).

**DLNA/UPnP AV:** pushing to televisions (DMR control) uses `async-upnp-client` (Apache-2.0, used by Home Assistant), which has a DLNA DMR profile ([repo](https://github.com/StevenLooman/async_upnp_client)). The Den sends a URL to a TV with SetAVTransportURI. Being a full DLNA server (ContentDirectory) would require hand-writing SSDP plus SOAP XML, and televisions are notoriously picky about DLNA.ORG_PN flags and time-seek headers — no mature Python library does this. Both casting paths share the same security problem: plain HTTP over the LAN with no tokens.

**TV platforms:** Android TV / Fire TV reuse the Android app with a leanback Compose UI. Roku (BrightScript/SceneGraph) has free developer mode and sideloading; publishing needs a free developer account plus certification ([Roku developer mode](https://developer.roku.com/dev/docs/developer-mode)). The GPL-2.0 [jellyfin-roku](https://github.com/jellyfin/jellyfin-roku) is a reference. Roku has no custom TLS pinning, so it needs a proper certificate or the signed-URL approach. webOS/Tizen hosted-web-app wrappers of the web UI are deferred until later, if at all.

### Music and OpenSubsonic

Music streams originals (FLAC, MP3, AAC) by Range request first, transcoding second: Opus via `libopus -b:a 128k` in Ogg or WebM; AAC via `aac -b:a 256k` in fMP4 for Safari/iOS. Safari 18.4+ plays Opus in Ogg but not Opus in MP4, and plays FLAC in HLS only as fMP4. Gapless playback on the web uses Web Audio / MSE with pre-buffering of the next track; Android Media3 playlists are gapless for MP3 (with LAME/Xing info), AAC (with iTunSMPB), Opus and FLAC. Transcoding must preserve encoder delay and padding metadata — Opus handles this best.

Loudness reads existing ReplayGain tags with `mutagen` (GPL-2.0+, a licence consideration) or ffprobe tags, scans untagged files with the `ebur128` filter (track and album gain, target -18 LUFS ReplayGain 2.0), serves gain values in the API and lets clients apply them. Do not bake `loudnorm` into transcodes because that breaks album gain.

Implementing OpenSubsonic brings Symfonium, Feishin, Tempo, Substreamer, DSub and others for free. Core endpoints include `ping`, `getLicense`, `getMusicFolders`, `getArtists`, `getArtist`, `getAlbum`, `getSong`, `getAlbumList2`, `search3`, `stream`, `download`, `getCoverArt`, `scrobble`, `star`/`unstar`, `getPlaylists`/`createPlaylist`, `getOpenSubsonicExtensions`. Legacy Subsonic auth (`t=md5(password+salt)&s=salt`) requires storing a recoverable plaintext password — do not use it. Instead implement the OpenSubsonic `apiKeyAuthentication` extension (`apiKey=` query parameter) and map it to a Den device token ([OpenSubsonic](https://opensubsonic.netlify.app/docs/), [apiKeyAuth](https://opensubsonic.netlify.app/docs/extensions/apikeyauth/)). Also support `transcodeOffset` for seeking in transcoded streams. Navidrome's server (GPL-3.0) is the reference implementation ([Navidrome notes](https://www.navidrome.org/docs/developers/subsonic-api/)).

### Stream security

Where HTTP headers work — Media3 with OkHttp, hls.js via `xhrSetup`/`fetchSetup`, The Den's own apps — send `Authorization: Bearer den_…` on the playlist and every segment.

Where headers do not work (`<video src>`, Safari native HLS, Chromecast, DLNA, Roku, Qt MediaPlayer), never put the long-lived device token in a URL. It ends up in logs, Referer headers and browser history, and it cannot be scoped. Instead:

1. **Session endpoint:** the authenticated client calls `POST /api/play/sessions` with the header token and receives a `play_session_id` plus a short-lived capability.
2. **Signed URLs:** every playlist and segment URL carries `?exp=<unix>&sig=<HMAC-SHA256(server_secret, user_id|item_id|session_id|path|exp)>`, created with Python's `hmac` + `secrets` and verified with `hmac.compare_digest`. Scope the signature to a path prefix (`/stream/<session>/`) so segment lists do not need one signature per file. TTL of a few hours, renewed through the session.
3. **Session control:** tie the session to a heartbeat. Revoking the device token or ending the session kills the signatures because the server checks that the session is live. Rate-limit and log it.
4. Header-based players can use the same session path.

Cookies work for the web UI (`HttpOnly; Secure; SameSite=Lax`) but not for casting or other apps. Use cookies for the web UI and signed URLs for everything else. Additional rules: never serve arbitrary file paths (resolve by item id only to prevent path traversal), cap concurrent transcodes per user, keep ffmpeg arguments as arrays never shell strings, treat subtitle and filename metadata as untrusted (ASS/libass has had CVEs), and add brute-force protection around token checks since the UPnP-exposed port makes streaming endpoints internet-facing.

### Licensing notes

Jellyfin server is GPL-2.0-or-later; jellyfin-ffmpeg is built as GPL ([LICENSE.md](https://github.com/jellyfin/jellyfin-ffmpeg/blob/jellyfin/LICENSE.md)); the Intro Skipper plugin is GPL-3.0 and now targets Jellyfin 12.0+ ([intro-skipper](https://github.com/intro-skipper/intro-skipper)). The Den currently has no licence — there is no LICENSE or COPYING file, and `PKGBUILD` says `license=('unknown')`.

Reading Jellyfin's code and reimplementing ideas (DeviceProfile schema, StreamBuilder decision order, ffmpeg argument patterns, trickplay tile layout) is allowed without licence effects: ideas and file formats are not copyrightable. Running jellyfin-ffmpeg or Arch's GPL ffmpeg as a separate program is also allowed. Copying or translating Jellyfin or Intro Skipper source into The Den is not allowed unless The Den adopts a GPL-compatible licence — that would make its code GPL-2.0+ (Jellyfin) or GPL-3.0 (Intro Skipper), excluding MIT/Apache-only licensing. The decision for Liam is to keep The Den under his own terms with clean-room reimplementation, or license it GPL-3.0-or-later and borrow freely. Given that everything around it is free software, GPL-3.0 is the low-friction option, but it remains his call.

H.264, HEVC and AAC are patent-encumbered (Via LA AVC/AAC and Access Advance HEVC pools; active HEVC litigation in 2026 ([Access Advance](https://accessadvance.com/licensing-programs/hevc-advance/))). Private home use carries low practical risk, but distributing a product that encodes HEVC is where pools charge. Never use `libfdk_aac` (non-free, cannot be distributed with GPL ffmpeg); the native `aac` encoder is fine. Prefer Opus and AV1 where clients allow.

## 6. Phased plan

### P0 Foundations

**Goal.** Establish the database, scanning pipeline, security primitives, job manager, and licence before any feature work begins.

**Main work.**

- Run `ffprobe -show_streams -show_format -show_chapters -of json` at import time to capture streams, chapters, HDR type and other metadata; store results in SQLite.
- Probe hardware capabilities at startup (`vainfo`, `ffmpeg -hide_banner -encoders`, one-second test encode per candidate) and record what actually works so the server can fall back to libx264 `-preset veryfast`.
- Create the `playback_state` table (`user_id`, `item_id`, `position_ms`, `duration_ms`, `played`, `play_count`, `last_played_at`, `updated_at`, `device_id`) and the progress API (start, periodic heartbeat every ~10 s, stop; played rule at ~90% or credits start).
- Implement the signed-URL/session module: a session endpoint (`POST /api/play/sessions`), HMAC-SHA256 signatures scoped to path prefixes with short TTLs, and heartbeat-driven revocation.
- Build the job manager for ffmpeg subprocess lifecycle (heartbeat kill on idle or ping timeout, temporary directory with size cap).
- Decide The Den's licence before any GPL code is copied in.

**Done when.** Library items are scanned into SQLite with full stream metadata; hardware capabilities are recorded at startup; playback state persists and syncs across clients; signed URLs work for header-less players; the job manager can start, monitor and kill ffmpeg processes reliably; a licence has been chosen.

**Dependencies.** None — this is the base on which every other phase depends.

---

### P1 Direct play in the web UI

**Goal.** Serve original files to the browser without any transcoding for compatible content.

**Main work.**

- HTTP Range file serving via FastAPI `FileResponse`.
- Convert SRT and embedded text subtitles (mov_text/SubRip) to WebVTT sidecars, cached on disk and served alongside the video.
- Resume and watched-state display in the web UI using the `playback_state` table from P0.

**Done when.** Most H.264/AAC MP4 files play directly in Chrome, Firefox, Edge and Safari through a native `<video>` element with Range requests (hls.js is not needed yet); subtitles render as WebVTT; playback position persists across sessions.

**Dependencies.** P0 (database, playback state).

---

### P2 HLS transcoding

**Goal.** Transcode incompatible files to H.264 HLS fMP4 for the web UI.

**Main work.**

- Implement a DeviceProfile schema (DirectPlayProfiles, TranscodingProfiles, CodecProfiles, SubtitleProfiles) modelled on Jellyfin's `DeviceProfile.cs`.
- Build the decision engine that walks profiles in order and picks direct play, remux or full transcode.
- On-demand fMP4 HLS (`-hls_segment_type fmp4`) with restart-on-seek: write a VOD playlist up front with fixed-length segments (e.g. 6 s), start ffmpeg at the requested segment, kill and restart with `-ss`, `-start_number`, `-output_ts_offset` and forced keyframes when seeking far ahead; throttle when ffmpeg gets too far ahead of the player.
- H.264 encoding via VAAPI/NVENC/QSV with libx264 fallback.
- Stereo downmix (`pan=stereo|FL<…` or `aresample=matrix_encoding=dplii`, not plain `-ac 2`).
- Integrate hls.js v1.7.3 in the web UI for Chrome/Firefox/Edge; Safari uses native HLS.

**Done when.** A file that cannot direct play is transcoded to H.264 HLS, plays smoothly with seeking, and falls back to CPU encoding if hardware paths are unavailable.

**Dependencies.** P0 (job manager, signed URLs), P1 (web UI baseline). This is the hardest phase — budget real time for seek/segment alignment and orphaned-process bugs.

---

### P3 Remux (direct stream)

**Goal.** Copy video and transcode only audio when possible, avoiding a full re-encode.

**Main work.**

- Video copy (`-c:v copy`) with audio transcoded to AAC or Opus if the client cannot decode the original codec (e.g. DTS/TrueHD).
- Repackage into HLS fMP4 segments.
- Build keyframe-accurate playlists: scan source keyframe positions first (PyAV or `ffprobe -skip_frame nokey`), then construct the playlist so cuts land on real keyframes rather than forcing artificial ones.

**Done when.** Files with incompatible audio but compatible video are served as remuxes without re-encoding the video stream; seeking works correctly within the remuxed HLS stream.

**Dependencies.** P2 (HLS pipeline, decision engine). Jellyfin still has open bugs here (remux plus mid-file seek desyncs the playlist — [#17966](https://github.com/jellyfin/jellyfin/issues/17966)); expect to debug this carefully.

---

### P4 Android and KDE players

**Goal.** Native playback on Android phones/tablets and on the KDE desktop app.

**Main work.**

- **Android:** Media3 ExoPlayer 1.11.0 with `HlsMediaSource`; pin the existing OkHttp client through `OkHttpDataSource.Factory` so segment requests reuse the pinned certificate and auth header; support ASS, PGS and SSA subtitles natively; direct play for most MKV files; leanback UI for Android TV/Fire TV.
- **KDE (Qt 6 QML):** prototype with QtMultimedia `MediaPlayer` on the FFmpeg backend; test whether custom HTTP headers or self-signed TLS pinning are possible; evaluate libmpv through a QML item as a more capable alternative (handles subtitles and HDR better, but is GPL/LGPL).

**Done when.** Both clients can play direct-play files and HLS transcoded streams; authentication works (headers on Android, signed URLs or proxy on KDE); subtitle formats render correctly.

**Dependencies.** P0 (signed URLs), P2 (HLS pipeline). Qt TLS/header support must be verified early — it is an unverified risk.

---

### P5 Intro and credits skipping, trickplay thumbnails

**Goal.** Let users skip intros and credits; show a seek-preview thumbnail strip.

**Main work.**

- **Intro detection:** fingerprint the first ~25% (capped at ~10 minutes) of each episode's audio with Chromaprint (`ffmpeg -f chromaprint -fp_format raw` or pyacoustid); compare episode pairs by sliding one fingerprint over the other, counting matching 32-bit hashes by Hamming distance; find the longest shared run of ≥15 s; snap to nearby silence (`silencedetect`) or chapter marks.
- **Credits detection:** check chapter names ("Credits", "End Credits"), then black frames (`blackdetect`/`blackframe`) near the end, then audio fingerprinting of the last N minutes. Expect 80–90% accuracy on TV and less on films; always allow manual correction in the UI.
- **Chapters:** use embedded chapters from `ffprobe -show_chapters`; otherwise synthesise every 5–10 minutes with a thumbnail per chapter (`ffmpeg -ss T -frames:v 1`).
- **Trickplay:** generate tiled JPEG sprite sheets at a fixed interval (`ffmpeg -skip_frame nokey … fps=1/10,scale=320:-2,tile=10x10`); store a small JSON manifest (interval, tile size, sheet count) alongside the sprites; run in a background queue at low CPU priority (`nice`/`ionice`) after import.
- **UI:** skip-button overlay and trickplay preview on seek.

**Done when.** Intros and credits are detected automatically with reasonable accuracy, users can correct segments manually, and trickplay thumbnails appear during seeking.

**Dependencies.** P0 (database for media-segment storage), P1 or later (web UI to display controls). Accuracy tuning is ongoing — ship the first pass and iterate.

---

### P6 HDR tone mapping and burned-in subtitles

**Goal.** Transcode HDR content to SDR and burn in image-based or styled subtitles when required.

**Main work.**

- **Tone mapping:** implement per-GPU paths — `libplacebo` on Vulkan (best quality, AMD/NVIDIA/Intel), `tonemap_vaapi`/`vpp_qsv` (Intel), `tonemap_opencl`, and the CPU chain (`zscale=t=linear…,tonemap=hable,zscale…`) as a slow fallback. Handle Dolby Vision profile 5 specially.
- **Subtitle burn-in:** ASS/SSA via `subtitles=` filter through libass (CPU only, forces a transcode); PGS/VobSub via `overlay` (CPU) or `overlay_vaapi`/`overlay_cuda` after conversion. Keep frames on the GPU where possible — any CPU filter in the middle forces download and upload at significant cost.
- Build a test matrix across GPUs to catch per-driver quirks (e.g. Jellyfin's libplacebo dark-output bug on AMD Vulkan [#17996](https://github.com/jellyfin/jellyfin/issues/17996)).

**Done when.** HDR files play correctly as SDR on clients that cannot do tone mapping; ASS and PGS subtitles render visibly in the transcoded output.

**Dependencies.** P2 (HLS transcode pipeline), hardware acceleration working at least partially. This is fiddly per driver — expect iteration.

---

### P7 Music and OpenSubsonic

**Goal.** Serve music libraries natively and expose an OpenSubsonic API so third-party apps work immediately.

**Main work.**

- **Music schema:** artists, albums, tracks tables; scan with ffprobe for format metadata.
- **Streaming:** serve originals (FLAC, MP3, AAC) by Range request; transcode to Opus (`libopus -b:a 128k` in Ogg or WebM) or AAC (`aac -b:a 256k` in fMP4 for Safari/iOS).
- **Gapless playback:** preserve encoder delay and padding metadata (Opus handles this best); web gapless via Web Audio/MSE pre-buffering; Android gapless via Media3 playlists.
- **Loudness:** read existing ReplayGain tags with ffprobe or `mutagen` (GPL-2.0+, licence consideration); scan untagged files with the `ebur128` filter (track and album gain, target −18 LUFS); serve gain values in the API for client-side application — do not bake `loudnorm` into transcodes as that breaks album gain.
- **OpenSubsonic API:** implement core endpoints (`ping`, `getLicense`, `getMusicFolders`, `getArtists`, `getArtist`, `getAlbum`, `getSong`, `getAlbumList2`, `search3`, `stream`, `download`, `getCoverArt`, `scrobble`, `star`/`unstar`, `getPlaylists`/`createPlaylist`, `getOpenSubsonicExtensions`). Use the OpenSubsonic `apiKeyAuthentication` extension (`apiKey=` query parameter mapped to a Den device token) rather than legacy Subsonic auth. Support `transcodeOffset` for seeking in transcoded streams.

**Done when.** Music plays with gapless playback and ReplayGain normalisation; third-party apps (Symfonium, Feishin, Tempo, etc.) can browse and stream via OpenSubsonic.

**Dependencies.** P0 (database), P2 or later (transcode pipeline for music). High value because it brings many existing clients for free.

---

### P8 Offline downloads converted on the server, watch-together invite links, Plex watch-history import

**Goal.** Support offline playback, social watching, and migration from existing libraries.

**Main work.**

- **Offline downloads:** convert files on the server to a device-compatible format (e.g. H.264/AAC MP4) for download; track downloaded items per device.
- **Watch-together invite links:** generate short-lived signed URLs that grant temporary playback access to a specific item; shareable via link.
- **Plex watch-history import:** read Plex's metadata (or its export format) and populate `playback_state` with existing progress, play counts and watched flags.

**Done when.** Users can download content for offline playback on Android; invite links allow temporary shared viewing; Plex history is imported correctly into The Den's database.

**Dependencies.** P0 (signed URLs), P4 (Android client for downloads).

---

### P9 TVs and casting, and a narrow Jellyfin 12.x API compatibility layer

**Goal.** Reach TV platforms and third-party apps that expect a Jellyfin-like API.

**Main work.**

- **Chromecast:** use the free Default Media Receiver (app ID `CC1AD845`); serve HLS/MP4 with WebVTT; resolve the self-signed certificate blocker via a LAN-only plain-HTTP media listener on a second port restricted to signed short-lived URLs and RFC 1918 addresses, or by obtaining a real certificate (Let's Encrypt DNS-01). Ensure CORS headers are present on playlist and segment endpoints.
- **DLNA push:** use `async-upnp-client` (Apache-2.0) to send playback URLs to TVs via SetAVTransportURI.
- **Android TV/Fire TV:** reuse the Android app with a leanback Compose UI — cheapest win for TV platforms.
- **Roku:** BrightScript/SceneGraph channel; developer mode and sideloading are free; publishing needs a (free) developer account plus certification. Use signed URLs or a real certificate since Roku has no custom TLS pinning. The GPL-2.0 [jellyfin-roku](https://github.com/jellyfin/jellyfin-roku) is a reference implementation.
- **Jellyfin 12.x API compatibility layer:** implement a narrow subset of the Jellyfin REST/WebSocket API sufficient for Infuse and Findroid to connect — library browsing, playback initiation with device profiles, and progress reporting. This avoids full API parity while unlocking two important third-party clients.

**Done when.** Chromecast casting works from Chrome/Android; DLNA push sends content to TVs; Android TV UI is functional; a Roku channel can play content; Infuse and Findroid can browse the library and initiate playback through the compatibility layer.

**Dependencies.** P0 (signed URLs), P2 (HLS pipeline), P4 (Android app for TV reuse). Casting is blocked by the self-signed certificate — this design decision must be made before P4.

---

## 7. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| **CPU cost of software transcoding** | One 1080p libx264 veryfast transcode uses roughly 2–4 modern cores; a 4K HEVC HDR to 1080p H.264 transcode with software tone mapping may not reach real time at all. Without a working GPU path the server can only sustain one or two simultaneous transcodes. | Enforce per-user concurrent-transcode limits; probe hardware capabilities at startup and prefer GPU paths (QSV, VAAPI, NVENC); fall back to libx264 `-preset veryfast` only when necessary; throttle ffmpeg when it gets too far ahead of the player. |
| **GPU and driver quirks** | Hardware acceleration depends on the server's GPU: Intel QSV/VAAPI is best value; AMD VAAPI works but H.264 encode quality is weaker; consumer NVIDIA NVENC has a concurrent-session cap; Mesa's VAAPI HEVC/H.264 encode availability depends on how Arch packages are built (some distros strip patented codecs). libplacebo has known bugs on AMD Vulkan (dark output, [#17996](https://github.com/jellyfin/jellyfin/issues/17996)). | Probe at startup with `vainfo`, encoder listing and one-second test encodes; store what actually works; build a per-GPU test matrix for tone mapping; keep libx264 as a reliable fallback. |
| **Codec patents (HEVC, AAC)** | H.264, HEVC and AAC are patent-encumbered via the Via LA AVC/AAC and Access Advance HEVC pools, with active HEVC litigation in 2026. Private home use carries low practical risk, but distributing a product that encodes these codecs is where patent pools charge fees. | The Den calls the system ffmpeg rather than bundling an encoder, which keeps it low risk for home use; it does ship through HoltOS images and tags, so review codec licensing before any wider or commercial distribution. Never use `libfdk_aac` (non-free). Prefer Opus and AV1 where clients allow them. If The Den were ever distributed commercially, a licensing review would be required. |
| **Keyframe alignment when remuxing** | With `-c:v copy`, cuts can only fall on source keyframes, which are irregular. The HLS playlist cannot be accurate unless keyframe positions are scanned first and the playlist is built from them. Jellyfin still has open bugs here (remux plus mid-file seek desyncs — [#17966](https://github.com/jellyfin/jellyfin/issues/17966)). | Scan source keyframes with PyAV or `ffprobe -skip_frame nokey` before building the remux playlist; force cuts only at real keyframe boundaries; budget extra time for debugging seek alignment in remuxed streams. |
| **Long tail of device-specific playback bugs** | Jellyfin keeps a dedicated ffmpeg fork and many per-device workarounds because "this file on this TV stutters" is endemic. Container, codec profile/level/bit depth/HDR, audio channels and subtitle format all interact with client capabilities in unpredictable ways. | Keep scope to The Den's own clients first (web, Android, KDE); implement a DeviceProfile schema so playback decisions are explicit and debuggable; log the decision path for every play request; add workarounds incrementally as real users report issues. |
| **Self-signed certificates versus casting and third-party apps** | Chromecast devices reject self-signed HTTPS entirely ([#1725](https://github.com/jellyfin/jellyfin/issues/1725)); DLNA, Roku and possibly Qt MediaPlayer also cannot pin custom certificates. This blocks P9 casting and may affect P4 KDE playback. | Provide a LAN-only plain-HTTP media listener on a second non-standard port, restricted to signed short-lived URLs and RFC 1918 addresses; alternatively obtain a real certificate (Let's Encrypt DNS-01 works without ports 80/443 but requires a domain). Decide before P4. |
| **Jellyfin API churn** | Jellyfin's API is not versioned or frozen. 12.0 removed legacy auth headers, route prefixes and endpoints, breaking many third-party tools; further breaking changes are held for 13.0, roughly a year away. A compatibility layer built against one version may break when the API changes. | Implement only the narrow subset needed for Infuse and Findroid; keep the compatibility layer isolated from core code so it can be updated independently; monitor Jellyfin release notes for breaking changes. |
| **GPL contamination if code is copied** | The Den has no licence yet. Copying Jellyfin (GPL-2.0-or-later), Intro Skipper (GPL-3.0) or mutagen (GPL-2.0+) source would make The Den a derivative work, requiring GPL licensing and excluding MIT/Apache-only terms. Running `jellyfin-ffmpeg` as a separate subprocess does not contaminate the server code. | Decide the licence before any borrowing: either keep The Den under its own terms with clean-room reimplementation of ideas (DeviceProfile schema, StreamBuilder logic), or license it GPL-3.0-or-later and borrow freely. Never copy source without resolving this first. |
| **SQLite performance on large libraries** | SQLite is a single-writer database; Jellyfin's EF Core regressions have caused noticeable slowdowns on large media libraries under concurrent access. The Den uses SQLite for the media database, playback state and sessions. | Use connection pooling with WAL mode; keep indexes lean (on `user_id`, `item_id`, `updated_at`); batch writes where possible; monitor query times as the library grows; consider a migration path to PostgreSQL if write contention becomes a problem. |
| **Subtitle burn-in forces transcoding** | Burn-in is the most common reason a direct-playable file ends up transcoded. ASS styling requires libass (CPU only); PGS/VobSub requires overlay filters. This multiplies CPU/GPU load and eliminates direct play for many files. | Offer client-side rendering where possible: JASSUB (libass in WASM) on the web, native ASS support in Media3 and Qt; reserve burn-in for clients that cannot render subtitles themselves. |
| **Qt MediaPlayer TLS and header limitations** | Qt 6 docs do not confirm whether custom HTTP headers or self-signed TLS pinning can be set for network media. If neither works, KDE playback of signed-URL streams may fail entirely. | Prototype early in P4; if Qt cannot handle authentication, fall back to libmpv through a QML item (more capable but GPL/LGPL) or use a local loopback proxy that performs the authenticated fetch. |
| **Intro/credits detection accuracy** | Fingerprint-based intro detection and black-frame/audio-based credits detection will not be perfect — expect 80–90% on TV series and much less on films. Incorrect segments frustrate users. | Always provide manual segment editing in the UI; allow users to mark episodes as "skip detection"; tune thresholds per season rather than globally; treat accuracy tuning as an ongoing process, not a one-off task. |
| **Hardware decode availability on the server** | The HoltOS server's GPU is unknown at design time. Without hardware acceleration, transcoding capacity drops dramatically and power/thermal costs rise. | Probe at startup and adapt; document tested hardware for real-time 1080p transcoding (one libx264 veryfast 1080p transcode uses roughly 2–4 modern cores); prefer an Intel iGPU if building or upgrading the server. |
