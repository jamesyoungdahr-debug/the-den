# Plan: replace Plex completely (M50 to M61)

Drafted 2026-09-15. Parents: docs/media-server-plan.md (research) and docs/media-phase1-plan.md (M49, direct play in the web UI, done).

## Goal and constraints

Liam has set the goal on 2026-09-15 to remove Plex Media Server and its apps and web player completely. The Den runs only on HoltOS; which machine hosts it does not change the plan. Viewers are the household and remote friends. Internet is 4 Gbit symmetric fibre, so upload bandwidth is not the limit; the server's own throughput and device compatibility are. Devices in use today include web browsers, Android phones and tablets, TV boxes or smart TVs (platforms still to be listed), and Chromecast casting. The cutover approach is Liam's choice: run Plex and The Den side by side for a while, then switch Plex off, then remove the Plex code. Standing rules still apply: never ports 80 or 443, no downloads while testing, push only when Liam says, tag only tested work.

## What The Den still takes from Plex

| Dependency | Where in the code | Replacement |
|---|---|---|
| Titles The Den did not download: Plex library scan into the PlexMedia table, merged into the Movies and TV pages | app/plex_scan.py, app/library_service.py | The Den's own library scanner (M50a, M50b) |
| Request availability | app/requests_service.py uses plex_scan.plex_index | Availability from The Den's own library (M50b) |
| Sign-in: Plex PIN sign-in, and some users have no Den password | app/routers/auth.py, app/plex_access.py | Den sign-in for every user plus a migration view (M51) |
| Watch history and ratings: only in Plex | — | Repeatable sync while both run (M52) |
| Plex watchlist import lists | app/import_lists.py kind plex_watchlist | The Den's own watchlist (M51) |
| Server display name from Plex | app/discovery.py | The name set in The Den (M60) |
| Plex health checks | app/health.py | Removed with the code (M61) |
| Players: Plex web, Android, TV and casting | — | The Den's players (M49 done for the web; M53 to M58) |
| File naming follows Plex's conventions (Title (Year), Show - S01E02); that is only a convention and stays | — | No change required |

## Milestones in order

### G0 Serving gate

**Goal:** Benchmark The Den sending large files over HTTPS, including several parallel high-bitrate range streams, to measure throughput and CPU usage. Decide before M54 and M56 whether transfers stay in Python or are handed to a reverse proxy with X-Accel-Redirect after The Den's checks.

**Main work:** Design and run the benchmark suite; analyse results against performance targets.

**Done when:** A written decision is made on serving architecture, documented for future reference.

**Depends on:** M49.

### M50a Library scanner, files

**Goal:** Walk the configured library folders, parse movie and episode file names, record every file (several versions of one title allowed, which changes the data model from one file_path per movie or episode to a media files table), probe with ffprobe in the background, and notice added, changed and removed files on scheduled rescans. Update app/media_stream.py to serve a chosen file row.

**Main work:** Implement the folder walker, filename parser, database schema migration for the media files table, background ffprobe worker, change detection logic, and updates to the streaming endpoint.

**Done when:** Every file in the library folders is recorded with metadata, and app/media_stream.py can serve any chosen file row.

**Depends on:** M49.

### M50b Library scanner, matching

**Goal:** Match files to TMDB and TVmaze with the existing parser, provide an unmatched queue with manual matching, build collections from TMDB, and derive request availability from The Den's own library instead of the Plex scan.

**Main work:** Integrate the file list from M50a with the existing title-matching logic, implement the unmatched queue UI, collection generation, and update app/requests_service.py to use the new data source.

**Done when:** The Movies and TV pages show the whole collection with Plex's scan switched off.

**Depends on:** M50a.

### M51 Accounts without Plex

**Goal:** Ensure every Plex-linked user can get a Den sign-in (invite or set-password link created by an admin), provide per-user library access, offer a migration view listing users who can still only sign in with Plex, and replace the Plex watchlist import list with The Den's own watchlist. Plex sign-in keeps working during the parallel period.

**Main work:** Implement invite and password-reset flows, per-user access controls, the migration admin view, and the native watchlist feature. Retain existing Plex authentication paths throughout.

**Done when:** All users can authenticate via The Den, the migration view is available to admins, and the watchlist import from Plex is no longer needed.

**Depends on:** Nothing new.

### M52 Plex history sync

**Goal:** Map Plex accounts to Den users, import watched state, resume points and ratings, make the process repeatable while both servers run, and perform a final sync at switch-off.

**Main work:** Build the account mapping logic, implement the data importer for watch progress and ratings, schedule repeatable runs, and provide an admin interface to trigger manual syncs.

**Done when:** Watch history and ratings are fully mirrored in The Den and can be refreshed on demand while both servers operate.

**Depends on:** M50b and M51.

### M53 Android player prototype

**Goal:** Build a Media3 ExoPlayer using the app's pinned OkHttp client for direct play, reporting what the device can decode to the server.

**Main work:** Implement the ExoPlayer integration, configure OkHttp with The Den's certificate handling, and add capability reporting back to the server.

**Done when:** A prototype Android player can directly stream content from The Den and report its decoding capabilities.

**Depends on:** M49.

### M54a Remux and audio

**Goal:** Provide HLS fMP4 with the video copied and DTS or TrueHD audio converted, using keyframe-aware playlists.

**Main work:** Implement the remux pipeline, audio conversion for incompatible codecs, and playlist generation aligned to keyframes.

**Done when:** Devices that cannot decode the original audio can play content via the remuxed HLS stream without quality loss in video.

**Depends on:** G0 and M53 (real device capabilities).

### M54b Transcoding

**Goal:** Offer full transcodes chosen from device profiles, detect hardware encoders at startup with a software fallback, support restart on seek, and include HDR tone mapping.

**Main work:** Implement the transcoding engine, device profile selection logic, hardware encoder detection, seek handling, and HDR tone mapping.

**Done when:** Any device in the inventory can play any file through an appropriate transcode, with smooth seeking and correct colour output.

**Depends on:** M54a.

### M55 Android TV and Fire TV

**Goal:** Provide a leanback interface in the same Android app for television use.

**Main work:** Implement the leanback UI, navigation patterns suitable for remote controls, and integrate with the existing player infrastructure.

**Done when:** The Android app runs on TV devices with an appropriate interface and full playback functionality.

**Depends on:** M53 and M54a.

### M48 Trusted certificate (already planned)

**Goal:** Obtain a Cloudflare DNS-01 certificate; this is now a hard prerequisite for casting and third-party players.

**Main work:** Configure the DNS-01 challenge with Cloudflare, obtain and install the certificate, and ensure The Den presents it correctly.

**Done when:** The server holds a trusted certificate valid for all required domains.

**Depends on:** Nothing new (already planned).

### M56 Casting

**Goal:** Support Chromecast with the Default Media Receiver, using signed short-lived stream URLs for players that cannot send headers.

**Main work:** Implement the casting discovery and control protocol, generate signed URLs with appropriate expiry times, and integrate with the Default Media Receiver.

**Done when:** Content can be cast from The Den to Chromecast devices reliably.

**Depends on:** M48 and M54a.

### M57 KDE player

**Goal:** Build a KDE desktop player using QtMultimedia or libmpv, starting with a short prototype first.

**Main work:** Evaluate both frameworks, implement the initial prototype, integrate authentication and streaming from The Den.

**Done when:** A functional desktop player can stream content on KDE-based systems.

**Depends on:** M54a.

### M58 Other TV platforms

**Goal:** Support whichever platforms the household uses (Roku, LG webOS, Samsung Tizen, Apple TV), each as its own app.

**Main work:** Develop platform-specific applications for each identified device type, integrating with The Den's streaming and authentication infrastructure.

**Done when:** Every TV platform in the household inventory has a working native application.

**Depends on:** M54b and the device inventory.

### M59 Parity extras before cutover

**Goal:** Implement only those features the household uses: skip intro and credits, trickplay thumbnails, offline downloads, music, photos, live TV.

**Main work:** Identify which of these features are actually used by the household, then implement each one to parity with the Plex experience.

**Done when:** All requested features are functional in The Den.

**Depends on:** M50b (library data), M54a or M54b (streaming capability as applicable).

### M60 Switch-off

**Goal:** Perform the final history sync, set the server name from The Den, turn off Plex integration but keep its code dormant for one release as a rollback path. Gate: M48, M50b, M51 with zero Plex-only users, M52, every device in the inventory tested, and the players each of them needs.

**Main work:** Execute the final sync, update discovery to use The Den's name, disable all Plex integration endpoints, verify all gating criteria are met, and document the rollback procedure.

**Done when:** The household is running entirely on The Den with no functional dependency on Plex, and a one-release rollback path exists.

**Depends on:** M48, M50b, M51 (zero Plex-only users), M52, all device testing complete, all required players implemented.

### M61 Remove Plex

**Goal:** Delete Plex code from the server (app/plex.py, app/plex_scan.py, app/plex_access.py, app/routers/plex.py, the PlexMedia table and Plex settings through a migration, Plex badges and pages) and from both apps, after a release with Plex switched off and no rollback needed.

**Main work:** Remove all identified files and code paths, execute database migrations to drop the PlexMedia table and related settings, remove UI elements referencing Plex, clean up the KDE and Android apps, and verify the system operates correctly without any residual references.

**Done when:** No Plex code remains in the server or apps, and the release is stable with no rollback required.

**Depends on:** M60 completed successfully with at least one stable release in production.

## Open questions for Liam

1. Which TV platforms and models does the household use?
2. Which Plex features are used today beyond movies and TV: music or Plexamp, photos, live TV or DVR, offline downloads, skip intro?
3. The four decisions from docs/media-server-plan.md: licence, casting and certificates (now M48), the KDE player, and the transcoding hardware.
4. When the Cloudflare domain move (M48) can happen, since casting waits for it.

## Review

DeepSeek Flash critiqued the first draft of this order on 2026-09-15. Changes taken: history sync moved before the players, M48 made a prerequisite for casting, the scanner split and given the multiple-versions data model, the serving benchmark made a gate, switch-off separated from code removal with a bake period, and cutover gated on zero Plex-only users.
