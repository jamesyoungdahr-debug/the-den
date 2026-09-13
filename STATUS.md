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
