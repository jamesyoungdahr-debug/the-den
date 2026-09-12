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
- **the-den-client / the-den-android need updating** (reviewed; see `docs/requests-plan.md`
  "Companion apps" -- the Android Settings screen is actually broken by this): `GET/POST /api/settings` no longer
  has `qbit_url` / `qbit_username` / `qbit_password` / `has_qbit_password`; it has
  `downloads_root`, `state_dir` (read-only), `torrent_port`, `download_rate_limit_kib`,
  `upload_rate_limit_kib`, `seed_ratio_limit`, `seed_time_limit_minutes` instead. They can
  also now use `/torrents` for live download progress.
- Torrent client polish worth doing once real use shows the need: per-torrent file
  selection, sequential download, IP filter, proxy support, a session-wide stats line
  (libtorrent exposes all of these; none are wired yet).
- Cleanup findings from the earlier code review still stand: the same query-building +
  quality-profile-fallback logic duplicated across `movies.py`/`series.py`/`ui.py`/
  `automation.py`; N+1 queries in `ui.py`'s `calendar()` and `tv_library()`;
  `scheduler.py` (and now `app/torrent/engine.py`) using a module-level global instead of DI.
- Optional: wire up real poster art (tiles currently show the intentional striped
  placeholder -- TMDB/TVmaze poster URLs aren't fetched/displayed yet).
