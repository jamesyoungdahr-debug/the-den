# Status

## Last completed
**M10 -- built-in torrent client.** The external qBittorrent dependency is gone; The Den
now embeds libtorrent-rasterbar (`app/torrent/engine.py`) and downloads releases itself.
Grabs go straight into the in-process session, the importer hard-links finished files into
the library so torrents keep seeding, seed ratio/time limits stop them, and the automation
cycle reaps stopped+imported torrents with their data. New `/torrents` JSON API and a live
Downloads page (progress, rates, peers, ETA, pause/resume/remove, add-by-hand). Settings
gained a "Torrent client" section (downloads folder, port, rate limits, seed limits);
`qbit_*` settings and `DownloadRecord.category` were removed by migration `b7e2f1c4d9a0`.

Verified end to end against `tests/local_swarm.py` (a private seeder + tracker on
localhost): grab → real download → import (same inode as the seeding copy) → `has_file`
→ seed-time limit → reaped; manual magnet add via 302 redirect; pause/resume; restart
restores torrents from resume data. See ROADMAP.md's M10 section for the details and the
two loopback-swarm gotchas that cost the most debugging time.

## Currently working on

**M36 -- remote access through the router, plus discovery and /health fixes (2026-09-15, LiamPC; committed locally, not pushed or tagged; the router test waits for Liam).** Settings > Remote access (off by default; `remote_access_enabled`, migration `c2d3e4f5a6b7`) asks the router over UPnP to forward `WEB_PORT` to this machine. The guard in `app/remote_access.py` refuses unless HTTPS is on with an unexpired certificate, the bind isn't loopback, first-run setup is finished and the port isn't 80 or 443, and a rule on the router that already forwards the port to another machine is never touched. libtorrent's port mapper couldn't be used (its Python bindings raise a TypeError instead of returning mapping handles), so `app/upnp.py` is a standard-library UPnP IGD client that treats router answers as untrusted (LAN http addresses only, the SSDP answer must come from the host it names, no DTDs, size limits, timeouts). Mappings use a one-hour lease renewed by a 10-minute scheduler job, which also re-checks the guard and runs the NAT loopback self-check (the served key must match this server's pin and /health its server id); they are removed when the setting is turned off or the server stops. `GET /api/remote-access`, `POST /api/remote-access/check`, the Settings status line and a health warning show the state, and `/health` now includes `public_host` when it is set. Also fixed: LAN discovery no longer advertises link-local or Docker, VM and VPN interface addresses, and `/health` no longer fails when `STATE_DIR` can't be written (a temporary server id is used). Server 0.8.1d. Verified in WSL: 27 unit checks with a fake UPnP client, 17 checks against a fake UPnP router on loopback (including hostile answers), 15 live checks against `python -m app` on 0.0.0.0 (no router in WSL, so the error path, the API, Settings, /health and the loopback probe against the real HTTPS server), `tests/test_discovery.py` 10/10 and a migration round-trip. Not tested yet: a mapping on a real router, NAT loopback on Liam's router, and access from outside. Claude wrote `app/upnp.py`, `app/remote_access.py` and the TLS helpers; the local models wrote the setting, migration, scheduler job, health check, API, Settings page, main.py wiring, discovery fixes and docs.

**M35 -- HTTPS with a pinned self-signed certificate (2026-09-14, LiamPC; committed locally, not pushed or tagged).** Liam never opens ports 80 or 443, and the router DDNS name has no DNS API, so no ACME challenge can issue a certificate browsers trust; that waits for Cloudflare DNS-01 (M48), and M38 passkeys move after it. `app/tls.py` keeps one ECDSA P-256 key under `STATE_DIR/tls` and a two-year self-signed certificate for localhost, the hostname, the public name and the LAN addresses. The certificate is reissued with the same key at startup when those names change or it nears expiry, so the pin the apps store (`sha256/<base64>` of the public key, OkHttp's format) never changes. `TLS=auto` (the default) serves HTTPS only on any bind that isn't loopback, and `TLS=off` on a LAN bind refuses to start. The session cookie is Secure while HTTPS is on; `/health`, the mDNS TXT record and `GET /api/settings` show `https` and the pin; `public_host` (migration `b1c2d3e4f5a6`, default from `PUBLIC_HOST`) is set in Settings > Remote access, which also shows the pin. `cryptography==46.0.5` is pinned in requirements.txt. Server 0.8.1c. The KDE client 0.5.0c and the Android app 0.7.0b can't pin yet, so they only reach loopback or plain-HTTP servers until M39 and M40; the laptop install binds 127.0.0.1 and is unaffected. Verified in WSL: 26 unit checks on `app/tls.py` (modes, certificate names, key file 0600 and folder 0700, a reissue keeps the pin, a corrupt key is replaced), the migration round-trip, `TLS=off` refused on 0.0.0.0, a loopback bind still on plain HTTP, 15 live checks against `python -m app` on 0.0.0.0 (the pin matches the served key, a client without the pin refuses the certificate, plain HTTP gets no answer, the Secure cookie, public_host validation and the Remote access section) and the offline server tests. Also run offline in the holtos-test VM (HoltOS 0.0.6d, Python 3.14.7, OpenSSL 3.6.4) from a home folder on 0.0.0.0:40290: 26 unit checks, `TLS=off` refused, and 21 live checks including real `curl --pinnedpubkey` pinning (right pin connects, wrong pin refused), first-run setup over HTTPS and the mDNS TXT pin; from Windows the right pin got HTTP 200 and a wrong pin was refused. Claude wrote `app/tls.py`, `app/__main__.py` and the TLS wiring in `app/main.py` and `app/discovery.py`; the local models wrote the setting, the migration, the settings API and page, and the docs.

**M37 -- device tokens (2026-09-14, LiamPC; committed locally, not pushed or tagged).** Every app sign-in now gets its own token in a new `device_tokens` table (migration `a0b1c2d3e4f5`), stored only as a SHA-256 hash with the first 8 characters kept to tell devices apart; `users.api_token` is gone and each existing token moved in as one device, so signed-in apps keep working. `POST /api/auth/token` takes an optional `{name, platform}` body; `GET /api/auth/devices` and `DELETE /api/auth/devices/{id}` list and revoke (owner or admin); logout with a token revokes it; deleting a user deletes their devices. The profile page lists devices with Revoke and makes named tokens for scripts; Users shows each person's device count and "sign out devices". The KDE client (0.5.0c) sends the hostname and the Android app (0.7.0b, versionCode 24) sends the manufacturer and model. Server 0.8.1b. Verified: migration upgrade, downgrade and upgrade on a copy of the test database (the old token signs in after the upgrade), a 31-check API smoke test (two devices, revoke one while the other keeps working, non-admins can't touch other people's devices, revoked and logged-out tokens get 401, thumbnails with `?api_key=`), the server unit tests, the KDE suite and the Android build and unit tests. Claude wrote the security code (`app/device_tokens.py`, the migration, `app/auth.py` and the auth, users and Plex thumbnail routes); the local models wrote the model, templates, client changes and docs.

**M34 -- server identity and LAN discovery (2026-09-13; released as v0.8.1a and installed on the Strix Halo on 2026-09-14, now on port 40204).** The server listens on `WEB_HOST:WEB_PORT` through a new `python -m app` launcher, so the systemd unit no longer hardcodes 127.0.0.1:8686; the default port is now 40204. `app/discovery.py` keeps a random server id under `STATE_DIR` and, unless `WEB_HOST` is a loopback address, advertises `_theden._tcp` over mDNS with TXT `name`, `id` and `api`. The name is the Plex server's, else the name from setup, else `SERVER_NAME`, else the hostname, and it is re-announced when Settings or the Plex settings change it. `/health` gains `server_id` and `server_name`. New dependency: zeroconf 0.151.3. Verified: `tests/test_discovery.py` 8/8 plus the other offline tests, and a live run on port 8689 that advertised on the LAN address with the id from `/health`, re-announced within 2 s after a rename through `/api/settings`, kept its id across a restart, advertised nothing when bound to 127.0.0.1, and left nothing advertised after a clean stop or a failed bind. The local models wrote all of it; Claude reviewed each diff and sent fix rounds for `app/discovery.py`, which had 7 bugs, including a server id that failed its own format check and nothing advertised on 0.0.0.0.

**Session handoff note (2026-09-13, evening):** work moved from the Windows machine to Liam's HoltOS laptop (Linux), where the repos are in `/home/liam/Projects/theden/`. Read `CONTEXT.txt` "PICK UP HERE" first. The HoltOS-installed v0.7.0 showed a real bug: `app/torrent/engine.py` still reads `torrent_status.paused` and `.auto_managed`, which libtorrent 2.1.1 removed, so the engine loop errors about once a second, seed limits never run and `/ui/downloads` returns 500. That fix ships first, together with M33, as v0.8.0a through the HoltOS updater. M34 comes next; its uncommitted `app/discovery.py` draft was lost with the Windows machine and has to be written again.

**M23 -- manual import for unmatched downloads (2026-09-13).** Downloads The Den couldn't fully place -- a movie or episode grab with no video, a season pack with leftover files, or a torrent added by hand with no target -- land in one queue with two actions per leftover file: assign it to a title, or import it as-is under its own name. Server 0.6.9, client 0.4.12, android 0.6.2. The first Tier 2 milestone (E3 in `docs/feature-research.md`).

**M22 -- Discover grouped and paged (2026-09-13).** Discover now separates movies from series (a Movies group and a Series group, with an All / Movies / Series filter in the apps), adds trending and top-rated rails for each, and every rail has a "View more" that opens the full TMDB list as a paged grid (`/discover/rail/{key}?page=N` on the web, `GET /api/discover/{rail}?page=N` for the apps, 20 cards a page, Load more appends). Server 0.6.7, client 0.4.11, android 0.6.1.

**M21 -- Android search from Detail, push, deep links (2026-09-13).** Every notification the server sends now carries a `theden://` deep link (ntfy `Click` header, webhook `link` field). The Android app (0.6.0) subscribes to the ntfy topic itself from a foreground service, shows each event on its own notification channel, opens the linked request, download or title when tapped, and lets admins open Releases from a tracked movie or season on Detail. Plan: `docs/tier1-plan.md`.

**M20 -- season packs and season actions (2026-09-13).** Multi-file torrents import
every episode they contain; automation prefers a season pack when most of a season is
missing; each season on the series page (web, KDE, Android) can be monitored, searched,
browsed for packs or marked as have. Plan: `docs/tier1-plan.md`.

**M19 -- failed-download handling (2026-09-13).** Torrents that error out, never get
metadata, or stall with no seeders are given up on automatically: the release goes on a
blocklist (30 days by default), the torrent and its data are removed, and the next cycle
searches again without it. "Blocklist and search again" is one click on the Downloads
page and in both apps. Plan: `docs/tier1-plan.md`.

**M18 -- upgrades (2026-09-12).** Titles that have a file but sit below the profile's
cutoff quality or its score target are "upgradable": automation re-searches them daily,
grabs only a release that clearly beats the file on disk, imports over it with an atomic
swap, and fires "upgraded". Library pages get an Upgradable filter and badge; both apps
show the badge and let you pick a release by hand. Plan: `docs/tier1-plan.md`.

**M17 -- custom formats (2026-09-12).** Release titles are parsed into source / codec /
HDR / audio / language / group; 16 built-in custom formats (editable, plus your own rule
sets) each carry a score per quality profile, and the profile has a minimum score below
which a release is never grabbed. Selection is quality, then score, then seeders. Managed
from Settings -> Quality & formats on the web; the Releases page and both apps show each
release's score and matched formats. Plan: `docs/tier1-plan.md`.

**M16 -- health and indexer stats (2026-09-12).** Every search is counted per indexer per
day (`indexer_stats`); `app/health.py` checks folders, the torrent engine, the Cloudflare
solver, the Plex token and failing indexers at the end of each automation cycle, keeps the
open issues in `health_issues`, fires `health_warning` for new ones and returns them from
`/health` as `checks`. Discover shows a banner, the Indexers page shows a 7-day stats line
and enable / disable, on the web, the KDE client and Android. Plan: `docs/tier1-plan.md`.

**M15 -- notification agents (2026-09-12).** Discord, ntfy, generic webhook, Telegram and
Pushover agents, each subscribed to a set of events (grabbed, imported, upgraded, download
failed, request submitted / approved / declined / available, health warning), managed from
Settings on all three surfaces via `/api/notifications`. The old single Discord webhook
setting keeps working as a legacy agent. Verified with `tests/e2e_notifications.sh` against
the extended `tests/mock_webhook.py`. Plan: `docs/tier1-plan.md`.

**M13 -- Plex-style file names (2026-09-12).** Decided: keep hard-links (the torrent keeps
seeding, no extra space), rename the imported file. `app/importer.py` now writes
`Movies/Title (Year)/Title (Year).mkv` and `TV/Show/Season 01/Show - S01E02 - Title.mkv`;
the folder layout is unchanged so existing libraries are not split. Covered by
`tests/test_importer.py` (5 checks, drafted by the local model).

**M12 -- indexer presets, native public trackers, Cloudflare solver (2026-09-12).**
Indexers are now picked from a catalog (`GET /indexers/presets`: Knaben, The Pirate Bay,
YTS, Nyaa, LimeTorrents, TorrentDownloads, EZTV, 1337x, AnimeTosho, thirteen usenet
indexers, Jackett/Prowlarr/generic) and the public trackers are talked to natively
(`app/indexers/native.py`), so Jackett/Prowlarr are no longer needed for them. Sites behind
Cloudflare go through a solver: the built-in one drives the system Chromium via nodriver
(`app/indexers/solver.py`, `chromium` is now a package dependency), or an external
FlareSolverr/Byparr URL from Settings -> Indexers. Five trackers verified live, all parsers
covered offline (`tests/test_native_indexers.py`, 11 checks); the built-in solver could not
be verified from the dev network (Cloudflare never clears there, even in a normal browser)
and needs the HoltOS box. All three clients got the preset picker and the solver field.
Details and open items: `docs/indexers-plan.md`.

**Library pages now include Plex (2026-09-12, v0.4.3).** Movies and TV merge The Den's rows
with the Plex scan (`app/library_service.py`): Plex-only titles appear with their Plex
poster via the new `/api/plex/thumb/{rating_key}` proxy (owner token stays server-side;
`?api_key=` accepted because `<img>`/QML `Image` can't send headers), *On Plex* filter,
"Add to Den" for admins; `/api/library/movies|series` for the apps; `plex_media.thumb`
column (migration `b8c9d0e1f2a3`). The web sidebar scrolls on short windows. Verified by
the e2e (72 checks) and the client harness.

**U4 -- the KDE client redesign -- is done** (2026-09-12, in the `the-den-client` repo): Plex/local sign-in
with a personal API token, the HoltOS Glass shell, Discover / Search / Detail / Requests
pages, poster-grid libraries, Downloads on the built-in torrent client, and a Settings
page that works against the current API again. Verified offscreen (13 pages, zero QML
warnings, full-app screenshot walk); still to be looked at on a real HoltOS desktop.
**Next: U5, the Android app** (`the-den-android`): login + API token, the changed
settings fields, then Discover and Requests first.

**Repo layout, settled 2026-09-12:** the KDE client was briefly merged into this repo
(v0.4.0) and even packaged inside `the-den` (v0.4.1), then split back out: the HoltOS
updater follows both repos, so `the-den-client` is its own repo and its own package
again (history kept via `git subtree split`; its U4 work is in there). `the-den` v0.4.2
is server-only once more. The client carries a copy of `design/exports/holt_tokens.py`;
regenerate here and copy across when tokens change.

**M11g is done (2026-09-12), which closes M11.** Request quotas (defaults in Settings →
Requests, per-user overrides on Users, admins exempt), "now available" detection with a
one-time Discord post when an approved request lands via import or Plex scan, and a
**Require sign-in** toggle in Settings → Accounts that overrides the `AUTH_REQUIRED` env
var (guarded so an anonymous admin can't lock themselves out). `/api/requests/quota`,
`quota` on `/api/auth/me`, `auth_required` + quota fields on `/api/settings`. 61-check e2e.
**Next: U4 (KDE client) and U5 (Android)** -- both need the login step, API-token auth,
the changed `/api/settings` fields, and the Discover/Requests screens. Still not tried
against real plex.tv.

**M11e Plex scan + M11f Requests are done** (2026-09-11): the scheduler walks the Plex
libraries picked in Settings into `plex_media` (TMDB/TVDB/IMDb ids, per-season episode
counts), so Discover and the detail pages know what is already on Plex; signed-in users
request movies or specific seasons from the detail page, admins approve or decline (with a
note) on `/requests`, approvals land in the library with only the wanted seasons monitored,
and automation only grabs monitored episodes. Requests that are already on Plex or in the
library are refused up front. `/api/requests` and `/api/plex/scan` for the clients. 36-check
e2e (`tests/mock_plex.py` now includes a mock PMS library). **Next is M11g** (request
limits, API tokens for the companion apps, flipping `AUTH_REQUIRED`), then the client
redesigns U4/U5. Still not tried against real plex.tv.

**M11d Discover is done** (2026-09-11): TMDB-driven home (hero, Recommended for you, trending,
popular, upcoming, on the air), multi-search, movie/series detail pages with cast, trailer,
seasons, availability and recommendations, admin add-to-library with TMDB→TVmaze mapping,
`/api/discover/*`. Verified live against TMDB with the built-in key. **Next is M11e (Plex
library scan)** so Discover can also show what's already on Plex, then M11f (Requests).

**M11c Plex login is done** (2026-09-11): PIN sign-in on /login and /setup, first Plex
sign-in on a fresh install becomes the owner/admin, shared users of the chosen server may
sign in (or anyone, if allowed), Plex panel in Settings picks the server and libraries,
JSON PIN flow for the native clients, Plex linking from the profile page. 34-check
end-to-end run against `tests/mock_plex.py` passed. **Not yet tried against real plex.tv**
(the client module follows Plex's documented flow and Overseerr's usage). **Next is M11d
(TMDB Discover)** -- needs the TMDB key -- or M11e (Plex library scan).

**U2 is done** (2026-09-11): every web page is now in the HoltOS Glass design -- Downloads,
Settings, Calendar (real month grid + agenda), Series detail (season accordion), Candidates.
The web UI redesign (U0-U2) is complete; what's left of the redesign is the two clients
(U4/U5) after their API changes. **Next is M11c (Plex login).**

**M11b accounts are done** (2026-09-11): local users with roles, sessions, API tokens,
`/setup`, `/login`, `/ui/users`, `/ui/profile`, page and API guards everywhere, `AUTH_REQUIRED`
off by default (anonymous = admin) until the companion apps gain a login step. 51-check
end-to-end run in both modes passed. **Next is M11c (Plex login) or U2.**

**UI redesign U0 + U1 are done**: tokens as a single source (`design/tokens.json` +
`build_tokens.py`), the Glass shell (`base.html`: sidebar/rail, top bar, mobile tab bar), the
v2 component layer (`den.css`/`den.js`), poster-grid Movies/TV with real art, Discover home,
Indexers at `/ui/indexers` (M11a). See `docs/ui-redesign-plan.md`. **Next is U2** (Downloads,
Settings, Calendar, Series detail, Candidates in the new components) **or M11b** (accounts). Also planned: M11 Discover + Requests -- design,
milestones and open decisions are in `docs/requests-plan.md`. Also planned: a full UI redesign
("HoltOS Glass", `docs/ui-redesign-plan.md`) whose shell/component work comes before M11's pages. Not started.

## Next steps
- **Real-world shakedown** (still the one thing never done): a real TMDB key, a real
  indexer. The engine itself HAS now been run against a public swarm: the Ubuntu 24.04.4
  ISO torrent pulled 60+ peers via tracker+DHT and peaked at 45 MiB/s, with the rate
  limiter and live settings reload both confirmed. Still untested: a real indexer grab.
- Built-in Cloudflare solver: verify against 1337x / EZTV from a residential connection
  (the dev network is refused by Cloudflare outright); if it still fails there, look at
  what Byparr does differently for the Turnstile iframe.
- Torrent client polish worth doing once real use shows the need: per-torrent file
  selection, sequential download, IP filter, proxy support, a session-wide stats line
  (libtorrent exposes all of these; none are wired yet).
- Cleanup (2026-09-12): the query-building and quality-profile fallback now live in
  `app/candidates.py` (`movie_query`, `episode_query`, `profile_for`) and the five call sites
  use them; the calendar and TV-library N+1s were already gone. Still module-level globals:
  `scheduler.py`, `app/torrent/engine.py`, `app/indexers/solver.py` -- left as is on purpose,
  each is a process-wide singleton and DI would only add plumbing.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder -- TMDB/TVmaze poster URLs aren't fetched/displayed yet).
