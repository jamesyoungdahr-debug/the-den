# Plan: Discover + Requests (the "Overseerr half") -- M11

Status: **planned, not started.** Written 2026-09-11 after researching Overseerr. Nothing
here is built yet; this is the design to build against once the open decisions at the
bottom are settled.

See also [ui-redesign-plan.md](ui-redesign-plan.md): the Discover/Requests pages are to be
built on the redesigned shell and component set, so that plan's U0/U1 come first.

## What we're adding, in one paragraph

Today The Den's front page is "Indexers & Search": admin plumbing (add/test indexers) plus a
raw release search. That page splits in two. **Indexers** becomes its own admin page.
**Search** becomes **Discover**: an Overseerr-style browsing experience -- search, trending,
popular, upcoming, poster cards with availability badges, detail pages -- where any user can
**request** a movie or a TV series (by season). An admin **approves or declines** requests;
approval adds the title to the library, and the existing automation loop grabs it through the
built-in torrent client. Users see their request move from *pending* to *approved* to
*available*. Because The Den already contains the Radarr/Sonarr/qBittorrent half in-process,
"approval" is a database insert rather than an API call to another service -- that's the
main way this is simpler than Overseerr.

## Research: what Overseerr does (the reference)

Source: github.com/sct/overseerr (MIT; archived Feb 2026, succeeded by *Seerr* -- same
design, still maintained). It's a Next.js/React app, so we borrow the **UX and data model**,
not code: The Den deliberately has no JS framework (Jinja + a little vanilla JS, HoltOS CSS).

**Discover page.** A search box up top, then horizontal "sliders" of poster cards: Recently
Added, Recent Requests, Trending, Popular Movies, Upcoming Movies, Popular Series, Upcoming
Series. Everything comes from TMDB (movies *and* TV).

**Title card.** Poster, year, a MOVIE/SERIES chip, and a **status badge** in the corner:
none (requestable) → *Pending* (requested, awaiting approval) → *Processing* (approved, being
fetched) → *Partially Available* (some seasons) → *Available*. Hover shows a Request button.

**Detail page.** Backdrop hero, poster, title/year/runtime/genres, overview, ratings, cast
row, similar/recommended sliders, and one primary **Request** button. For TV it opens a
**modal listing seasons** with checkboxes (each showing its current status), "select all",
and specials excluded by default. Requesting some seasons now and more later is normal.

**Request lifecycle.** `MediaRequest.status`: 1 PENDING → 2 APPROVED | 3 DECLINED.
Separately `Media.status` (availability): UNKNOWN, PENDING, PROCESSING, PARTIALLY_AVAILABLE,
AVAILABLE, DELETED. For TV, availability is tracked per season. Approval sends the title to
Radarr/Sonarr; availability flips when the library scan sees the file.

**Requests page (admin).** Table/cards of every request: poster, title, requester (avatar +
name), requested date, status, and **Approve / Decline** buttons; filters (all, pending,
approved, processing, available) and sort (added/modified). Users see the same page filtered
to their own requests, read-only.

**Users & permissions.** Owner account (setup) + Plex-imported users + local users (email +
password). Granular permission bits: Admin, Manage Users, Manage Requests, Request, Request
Movies, Request Series, Auto-Approve (all / movies / series), View Requests, Advanced
Request (pick quality profile / folder), 4K variants. **Request limits**: N movies and N
series per rolling X days, per user, admins/managers exempt.

**Notifications.** On new request (to admins), on approved/declined/available (to the
requester); Discord, email, Telegram, Pushover, webhooks, and in-app.

## How it maps onto The Den

| Overseerr concept | The Den equivalent |
|---|---|
| Send approved movie to Radarr | insert `Movie` row (automation loop grabs it) |
| Send approved seasons to Sonarr | insert `Series` + `Episode` rows, mark requested seasons *monitored* |
| Library scan → Available | `has_file` in our library **or** the title found by our own Plex server scan |
| Media status | derived from library rows + open requests, not a separate table |
| Plex users | Plex login (PIN flow); accounts the owner shares the server with may log in; local accounts as fallback |
| Radarr/Sonarr quality profile in request modal | `QualityProfile` picker for admins ("advanced request") -- later |

### Metadata sources

- **Discovery + search + detail pages: TMDB for both movies and TV.** TMDB has all the
  browsing endpoints (`/trending/all/week`, `/movie/popular`, `/movie/upcoming`,
  `/tv/popular`, `/tv/on_the_air`, `/search/multi`, `/movie/{id}`, `/tv/{id}` with
  `append_to_response=credits,external_ids,videos,recommendations`) and TVmaze has none of
  the browse/trending ones. The app already requires a TMDB key for movies.
- **TV library stays on TVmaze** (`Series.tvmaze_id`, no key, already built). On approval
  we map TMDB → TVmaze via TMDB's `external_ids.tvdb_id` and TVmaze's
  `/lookup/shows?thetvdb={id}` (returns a 301 to the show; fall back to `?imdb=`, then to
  name+year search). Store `Series.tmdb_id` too so cards can match library rows directly.
- **Posters/backdrops**: `https://image.tmdb.org/t/p/w342{poster_path}` /
  `w1280{backdrop_path}`. This also finally replaces the striped placeholder tiles in the
  Movies/TV library pages (already on the STATUS.md wish list).
- **Caching**: TMDB allows ~50 req/s but discover pages fan out to 5–6 calls; cache each
  discover/detail response in memory for 10 minutes (a dict with timestamps is enough).

### Users and auth (new -- the app currently has none)

**Decided 2026-09-11:** a proper login, with **Plex login** as the primary way in and local
accounts as the fallback, and a hard rule that **admin plumbing (Indexers, Downloads,
Settings, Users, Plex setup, library remove/grab actions) is only visible to a logged-in
admin** -- a standard user never sees it, in the nav or at the URL.

**Plex login (verified against plex.tv's documented flow and Overseerr's implementation):**

1. `POST https://plex.tv/api/v2/pins` with `strong=true` and headers
   `X-Plex-Product: The Den`, `X-Plex-Client-Identifier: <uuid generated once, stored under
   STATE_DIR>`, `Accept: application/json` → `{id, code}`.
2. Send the browser to `https://app.plex.tv/auth#?clientID=…&code=…&forwardUrl=<our
   /login/plex/callback>&context[device][product]=The Den`. The user signs in on plex.tv;
   we never see their password.
3. On return (or by polling) `GET https://plex.tv/api/v2/pins/{id}` → `authToken`.
4. `GET https://plex.tv/api/v2/user` with `X-Plex-Token` → account (`id`, `uuid`,
   `username`, `email`, `thumb` avatar).
5. **Who may log in:** the Plex account that set The Den up is the **owner** (admin). Any
   other Plex account is allowed in if it appears in the owner's shared users
   (`GET https://plex.tv/api/users` with the owner's token, matched on the configured
   server's `machineIdentifier`) -- i.e. exactly the people the owner already shares the
   Plex server with. Everyone else gets a 403. An admin toggle "allow any Plex account"
   exists for open setups. First login of an allowed account creates their `users` row
   with the `user` role.
6. The owner's Plex token is stored (secret, like the TMDB key) because the library scan
   and the shared-user check both need it. Per-user tokens are not kept beyond login.

**Local accounts** stay for anyone without Plex: username + password (stdlib
`hashlib.scrypt`, no new dependency), created by an admin from the Users page. The very
first run shows a setup page offering "Sign in with Plex" (becomes owner/admin) or "Create
admin account" (local).

**Sessions:** Starlette's `SessionMiddleware` (ships with FastAPI; needs `itsdangerous`, one
small pure-Python dep) with a secret auto-generated under `STATE_DIR`.

- `users` table: `id`, `username`, `email`, `avatar_url`, `password_hash` (null for
  Plex-only users), `plex_id`, `plex_username`, `role` (`admin` | `user`), `auto_approve`,
  `movie_limit`, `series_limit`, `limit_days`, `created_at`, `last_login_at`.
- Page access: **user** → Discover, Requests (own), Movies/TV (read-only browse, no
  remove/grab buttons), Calendar. **admin** → everything. Enforced by a dependency on
  every router, not just by hiding nav links; non-admins hitting an admin URL get 403 (or a
  redirect to Discover for HTML pages).
- JSON API: browser sessions work for `fetch()` from our own pages. The companion apps
  (the-den-client, the-den-android) currently call the API unauthenticated; they get a
  per-user **API token** (`X-Api-Key` header, generated on the user's profile page) plus
  `POST /api/auth/plex` mirroring the web flow. Until they're updated, an env flag
  `AUTH_REQUIRED=false` keeps the old open behaviour so nothing breaks on day one.
- Not doing now: Jellyfin/Emby login, email/password reset. The table is shaped so another
  external-login column can be added later.

### Knowing what we already have (library awareness)

**Decided 2026-09-11:** Discover must reflect what's already available, and "available"
means *in The Den's own library **or** on the Plex server* -- Plex may hold plenty of media
that The Den never downloaded.

Two sources, merged when computing a title's status:

1. **The Den's library** -- `Movie.has_file`, `Episode.has_file` (exists today).
2. **Plex library scan** (new, mirrors Overseerr's scanner):
   - Admin picks the server on the Plex settings page: `GET https://plex.tv/api/resources
     ?includeHttps=1` with the owner token lists their servers and connection URIs; we store
     `plex_url`, `plex_machine_id`, and which library sections to scan.
   - Scan: `GET {plex_url}/library/sections` → for each movie/show section
     `GET /library/sections/{id}/all?includeGuids=1` (paginated with
     `X-Plex-Container-Start/Size`). Each item's `Guid` tags carry `tmdb://123`,
     `tvdb://456`, `imdb://tt…` (new agent), or a legacy agent guid we parse the same ids
     out of. Movies: record tmdb_id. Shows: `GET /library/metadata/{ratingKey}/children`
     for seasons, then each season's children for episode counts → per-season availability
     (season complete when Plex has ≥ TMDB's episode count, else *partial*).
   - Results go in a `plex_media` table: `media_type`, `tmdb_id`, `tvdb_id`, `imdb_id`,
     `rating_key`, `title`, `seasons` (JSON `{season_number: episode_count}`),
     `scanned_at`. Full rescan on a timer (default every 30 min, admin-triggerable), with
     `updatedAt`-based incremental scans later if full scans get slow.
   - Requests for something Plex already has are refused with "already available" (and
     the Discover badge says so before the user even clicks).
3. Optional later: when The Den imports a file into a folder Plex indexes, poke
   `GET {plex_url}/library/sections/{id}/refresh` so Plex picks it up straight away.

### Data model additions

```
users            (above)
plex_media       (above)
settings         + plex_token (secret), plex_url, plex_machine_id, plex_sections (JSON),
                   plex_scan_interval_minutes, plex_allow_any_account (bool)
media_requests   id, media_type (movie|tv), tmdb_id, title, year, poster_path,
                 seasons (JSON list of ints; [] for movies / whole-series),
                 status (pending|approved|declined), note,
                 requested_by → users.id, decided_by → users.id, decided_at,
                 movie_id → movies.id | series_id → series.id (set on approval),
                 created_at, updated_at
movies           + tmdb backdrop_path (poster_path exists)
series           + tmdb_id, backdrop_path
episodes         + monitored (bool, default true) -- automation only grabs monitored
                   episodes; a season request sets monitored on that season's episodes
```

Availability is computed, not stored: movie → `has_file` **or** a `plex_media` row; series
season → all its monitored episodes `has_file` **or** Plex has the season's full episode
count; series → all requested seasons available (partial otherwise).

### Pages (Jinja + vanilla JS, HoltOS components)

Navigation becomes: **Discover** (home) · **Requests** · Movies · TV · Calendar · Downloads ·
Indexers · Settings · user menu (name, logout). Non-admins don't see Downloads/Indexers/Settings.

1. `/` **Discover** -- search bar; sliders for Trending this week, Popular movies, Upcoming
   movies, Popular series, Recent requests. Each card = `MediaTile` from `design/` (poster
   slot exists already) + status badge + hover Request button. Sliders are plain
   `overflow-x: auto` rows, no carousel library.
2. `/discover/search?q=` -- multi-search results grid (movies + TV, people dropped).
3. `/discover/movie/{tmdb_id}` and `/discover/tv/{tmdb_id}` -- detail page: backdrop,
   poster, facts row, overview, cast row, status, **Request** button. TV: season list with
   per-season status and checkboxes; the request modal is a `<dialog>` element.
4. `/requests` -- admin: all requests with Approve/Decline and filters; user: own requests.
   Live-updating like the Downloads page (poll `/api/requests` every few seconds).
5. `/indexers` -- the current indexer add/test/delete panel, moved out of the home page,
   plus the raw release search (renamed "Manual search", admin tool).
6. `/setup` (first run: Sign in with Plex, or create a local admin), `/login` (Plex button +
   local form), `/login/plex/callback`, `/logout`, `/profile` (API token), `/users` (admin:
   list Plex-linked and local users, create local users, set role, auto-approve, limits).
7. Settings gains a **Plex** panel (admin): connect owner account (Plex login), pick server
   and sections, scan interval, "scan now", last scan result, "allow any Plex account".

### API (JSON, for the companion apps)

```
POST /api/auth/login (local)  POST /api/auth/plex {authToken}  /api/auth/logout  GET /api/auth/me
GET  /api/auth/plex/pin  (creates the PIN; returns id, code, and the app.plex.tv URL)
POST /api/plex/scan (admin)   GET /api/plex/servers (admin, from the owner token)
GET  /api/discover/trending|popular-movies|upcoming-movies|popular-tv|search?q=
GET  /api/discover/movie/{tmdb_id}   /api/discover/tv/{tmdb_id}   (+ status merged in)
GET  /api/requests?status=&mine=     POST /api/requests {media_type, tmdb_id, seasons[]}
POST /api/requests/{id}/approve | /decline     DELETE /api/requests/{id} (own, if pending)
GET/POST /api/users ... (admin)
```

### Approval → library flow

```
approve(request):
  movie:  Movie.get_or_create(tmdb_id, title, year, poster, backdrop)      → automation grabs
  tv:     tvmaze_id = map_tmdb_to_tvmaze(tmdb_id)                          (external_ids → lookup)
          Series.get_or_create(tvmaze_id, tmdb_id, ...) + fetch episodes (existing code)
          set Episode.monitored = season in request.seasons  (unrequested seasons unmonitored)
  request.status = approved; notify requester
auto-approve: same path immediately at creation when user.auto_approve (or admin)
decline: status = declined; notify requester
availability: computed on read; a small hook after import flips "available" notifications
```

### Notifications

Extend `app/notifier.py` (Discord webhook, exists): new request → "**X** requested *Title
(Year)* -- approve at /requests"; approved/declined → requester-facing message;
available → "*Title* is now available". Per-user notification targets (own webhook/email)
are out of scope for M11.

## Milestones (each runnable + tested before the next)

| Step | Scope | Size |
|---|---|---|
| M11a | Nav split: `/indexers` page, home becomes a placeholder Discover; no behaviour change otherwise | S |
| M11b | Users + auth: table, migration, setup page, local login/logout, session middleware, **admin-only gating on every admin page and API route**, `AUTH_REQUIRED` escape hatch, Users admin page | M |
| M11c | **Plex login**: client identifier, PIN flow, callback, owner linking, shared-user check, "allow any Plex account" toggle; Plex panel in Settings (server + sections picker) | M |
| M11d | TMDB discovery client + cache; Discover, search, and detail pages with real posters; library pages get poster art too | M |
| M11e | **Plex library scan**: `plex_media` table, scanner, timer, "scan now"; availability merged into Discover badges and detail pages | M |
| M11f | Requests: model, API, request modal (seasons), Requests page with approve/decline, approval→library flow incl. TMDB→TVmaze mapping and `Episode.monitored`; automation honours `monitored`; "already available" refusal | L |
| M11g | Auto-approve, request limits, Discord notifications for request events, "available" detection, profile page + API token for companion apps, polish, docs | M |

Rough order of effort: M11f is the heart; M11b/M11c are the prerequisites most likely to
surface design questions. Tests: extend `tests/mock_tmdb.py` with discover/detail/
external_ids fixtures, and add `tests/mock_plex.py` (fake plex.tv PIN/user/users endpoints
and a fake Plex Media Server with a couple of sections) so the whole flow, Plex included,
runs offline like everything else.

## Decisions

**Settled (2026-09-11):**
- **Accounts: yes, a proper login.** Plex login as the main path, local accounts as
  fallback, admin/user roles. Everything infrastructural (Indexers, Downloads, Settings,
  Users, Plex) is admin-only, enforced server-side.
- **Library awareness: yes, including Plex.** Discover/requests must know what's already
  in The Den's library *and* on the Plex server.
- **Companion apps:** the API goes behind auth (API token per user), with
  `AUTH_REQUIRED=false` as the transition flag.

**Still open:**
1. **TV request granularity.** Per-season like Overseerr (recommended; needs
   `Episode.monitored`) -- or whole-series only (simpler, grabs everything)?
2. **Admin auto-approve.** Admins' own requests approve instantly (Overseerr default) --
   or should even admins go through the queue?
3. **Request limits.** Ship quotas in M11g (e.g. default 10 movies / 5 series per 7 days,
   admins exempt) -- or skip quotas entirely for a household?
4. **Home page.** Discover becomes `/` (Overseerr-style, recommended) -- or keep the
   library as landing and put Discover in the nav?
5. **Who may log in with Plex.** Only accounts the owner shares the server with
   (recommended, Overseerr's default) -- or anyone with a Plex account?

## Companion apps (reviewed 2026-09-11)

Both clients live in their own repos and talk only to this backend's JSON API. Cloned to
`C:\projects\the-den-client` and `C:\projects\the-den-android` for this review.

### the-den-client (KDE desktop) -- github.com/jamesyoungdahr-debug/the-den-client

- Python + PySide6 + Kirigami QML (~1,500 lines). All of its milestones are done: M0–M7
  mirror the web UI (indexers, movies, candidates/grab, downloads, TV, calendar,
  settings) and M8 is a native Arch package that built and installed for real. Verified
  headlessly throughout (`QT_QPA_PLATFORM=offscreen` + models driven against a live
  backend); never actually seen on a screen since M0.
- Endpoints it consumes: `/health`, `/indexers` (+`/{id}/test`), `/movies`,
  `/movies/search-tmdb`, `/movies/{id}/candidates|grab`, `/downloads` (+`/{id}/check`),
  `/series`, `/series/search-tvmaze`, `/series/{id}/episodes`,
  `/episodes/{id}/candidates|grab`, `/api/settings`. No `/calendar` JSON exists; it
  composes the calendar client-side.
- One `ApiClient` holds the base URL; every model gets it via a lambda. Networking is
  `QNetworkAccessManager`, so adding an `X-Api-Key` header is a one-place change in each
  model's request construction (or a shared helper -- STATUS.md already wants to
  de-duplicate the near-identical model classes).
- **M10 fallout (today):** `SettingsController` still reads/writes `qbit_url`,
  `qbit_username`, `qbit_password`, `has_qbit_password`. The backend ignores unknown
  POST fields and simply doesn't return the GET ones, so the Settings page shows blank
  qBittorrent fields and never shows the new torrent settings -- degraded, not crashing.
  `DownloadsPage` keeps working (`/downloads` and `/check` still exist) but shows only
  record status, no live progress.

### the-den-android -- github.com/jamesyoungdahr-debug/the-den-android

- Kotlin + Jetpack Compose + Retrofit/OkHttp/kotlinx.serialization (~2,400 lines).
  Done: M0 connect, M1 indexers, M2 movie library, M7 settings. **Not started:** M3
  candidates/grab, M4 downloads, M5 TV, M6 calendar, M8 distribution. Has a real
  emulator-verified test loop (`gradlew test` runs ViewModel tests against a live
  backend; AVD runs for visual checks).
- **M10 fallout (today): the Settings screen is broken.** `SettingsResponse` declares
  `qbit_url`, `qbit_username`, `qbit_password`, `has_qbit_password` as non-nullable
  fields with no defaults; `ignoreUnknownKeys` doesn't help with *missing* keys, so
  decoding `GET /api/settings` throws and the screen shows "Load failed". One-line fix
  per field (defaults or removal) plus the new torrent fields.

### What M10 already needs from them (do first, small)

| Client | Change |
|---|---|
| both | Settings: drop `qbit_*`, add `downloads_root`, `torrent_port`, `download_rate_limit_kib`, `upload_rate_limit_kib`, `seed_ratio_limit`, `seed_time_limit_minutes`; show `state_dir` read-only |
| KDE | Downloads page: switch from `/downloads` to `/torrents` -- progress bar, rates, peers, ETA, pause/resume/remove, "add torrent" field; poll every 2 s like the web page |
| Android | Same when its M4 Downloads milestone is built -- build it straight on `/torrents`, skip the `/downloads`-only version |
| backend | Add `api_version` to `/health` (start at 2) so clients can tell an M10+ backend from an older one and show a clear "update the server" message instead of failing field-by-field |

### What M11 means for them

- **Auth is the breaking change.** Both clients currently send no credentials. Plan:
  - Backend: every user gets an **API token** (profile page); `X-Api-Key` header
    authenticates API calls; `POST /api/auth/login` (local) returns the token;
    `GET /api/auth/plex/pin` + `POST /api/auth/plex` let a client do the Plex flow
    (open `app.plex.tv` in the system browser / Android Custom Tab, then poll). `GET
    /api/auth/me` returns role + permissions so clients can gate their own UI.
    `AUTH_REQUIRED=false` keeps today's open behaviour during the transition.
  - KDE client: a Login page before Connect succeeds (Plex button + local form); token
    stored with `QSettings`; header added in one shared request helper; admin-only pages
    (Indexers, Downloads, Settings) hidden unless `/api/auth/me` says admin.
  - Android: Login screen (Plex via Custom Tab + local form); token in
    `EncryptedSharedPreferences`; an OkHttp interceptor adds the header; same role
    gating.
- **Discover + Requests are the features that matter most on a phone** -- approving a
  request from the sofa is Overseerr's headline use case. Recommendation: **re-order
  the Android roadmap** so Discover (poster grid from `/api/discover/*`, detail page,
  request with season picker) and Requests (own list; approve/decline for admins, with
  a notification tap-through later) come *before* the unstarted admin-ish milestones
  M3–M6. The KDE client gets the same two pages after its M10 fixes. Posters are plain
  image URLs (`image.tmdb.org`), which Qt's `Image` and Coil on Android both load
  directly.
- **Test harnesses**: both clients test against a real running backend. `tests/
  local_swarm.py` + `mock_torznab.py` now let those runs exercise real grabs offline;
  the planned `tests/mock_plex.py` will do the same for login and the library scan.
- Sequencing across repos: backend M11b/M11c (auth) ship with `AUTH_REQUIRED=false`
  defaulted **on** until both clients have a login step; flip the default in M11g.

## Risks / things to watch

- **TMDB → TVmaze mapping misses** for obscure or very new series: fall back to name+year
  search, and if that fails show the admin a "pick the TVmaze match" step on approval
  rather than failing silently.
- **TMDB key becomes mandatory** for the Discover half (it already is for movies).
- **Unmonitored episodes** change automation semantics: today every episode of an added
  series is grabbed. Series added directly from the TV page should default to all-monitored
  so existing behaviour holds.
- **The API gaining auth** is the one breaking change for the companion apps; the
  `AUTH_REQUIRED` flag and an API-token option keep that migration gentle.
- **Plex API is undocumented officially.** The PIN flow and `/api/v2/user` are described
  on Plex's forums and used by every third-party app; `/api/users` (shared users) and
  `/api/resources` are older XML endpoints that Overseerr relies on and could change.
  Isolate all of it in one `app/plex.py` client so a change is a one-file fix.
- **Plex GUID formats vary** by agent and library age; parse `tmdb://`, `tvdb://`,
  `imdb://` and the legacy `com.plexapp.agents.*` forms, and log anything unmatched so it
  can be added rather than silently counted as "not available".
- **Owner token security.** It's as sensitive as a password (full Plex account access);
  same handling as the TMDB key -- never echoed by the API, only a `has_plex_token` flag.
