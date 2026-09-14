<p align="center">
  <img src="assets/logo.svg" width="72" alt="The Den">
</p>
<h1 align="center">The Den</h1>
<p align="center"><code>PART OF HOLTOS</code></p>

One self-hosted app in place of the usual four. What Sonarr, Radarr, Prowlarr and
qBittorrent each do separately, The Den does in a single process: indexer search, a
movie + TV library, quality-based release picking, a **built-in BitTorrent client**, and a
background loop that finds, downloads and imports what's missing on its own. No download
client to install, configure, or keep in sync. Companion apps: the native KDE desktop
app [the-den-client](https://github.com/jamesyoungdahr-debug/the-den-client) and the
Android app [the-den-android](https://github.com/jamesyoungdahr-debug/the-den-android),
each in its own repo with its own package.

See [ROADMAP.md](ROADMAP.md) for how it was built, milestone by milestone, and
[STATUS.md](STATUS.md) for what's done/next right now.

## Running it for development

The torrent client is [libtorrent-rasterbar](https://libtorrent.org) embedded in-process
(the same engine qBittorrent is built on). Its Python bindings come from the system package
manager -- `python3-libtorrent` on Debian/Ubuntu, `libtorrent-rasterbar` on Arch -- and the
venv is created with `--system-site-packages` so it can see them. (On Python 3.13 and older,
`pip install libtorrent` works too.)

```bash
sudo apt install python3-libtorrent        # or: pacman -S libtorrent-rasterbar
python -m venv --system-site-packages .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m alembic upgrade head
.venv/bin/python -m app        # listens on WEB_HOST:WEB_PORT, 127.0.0.1:40204 by default
```

Then open http://127.0.0.1:40204. Configure TMDB key, library folders, the torrent client
(downloads folder, listen port, rate and seeding limits), automation interval, and Discord
webhook from **Settings** in the app itself -- or copy `.env.example` to `.env` (or export
the same variables) if you'd rather manage config as files; the in-app settings win if both
are set. Without either, the app still runs, just against nothing real.

### Accounts

The Den has local accounts with two roles. **Admins** see everything (Indexers, Downloads,
Users, Settings, add/remove/grab actions); **users** can browse the library, and in M11
will request titles. Sign-in is **always required**. On a fresh install the first visit runs a
two-step setup (create the admin with a password or Plex, then name the server and pick the
library folders); until it's finished the server serves only the setup and sign-in pages and
answers every app or API call with 503 "setup required".

Companion apps authenticate with a **device token**, sent as `X-Api-Key`: after signing in
(`POST /api/auth/login` or Plex), an app calls `POST /api/auth/token` with its `name` and
`platform` and keeps the token it gets back. Every device has its own token, stored on the
server only as a hash; `GET /api/auth/devices` lists them, `DELETE /api/auth/devices/{id}`
revokes one, and `POST /api/auth/logout` with a token revokes that token. `/ui/profile` lists
your devices and can make a token for a script. `GET /api/auth/me` tells a client who it is
and whether it's an admin.

**Plex sign-in.** Sign in with the Plex account that owns your server and The Den links
it as the owner (an admin) and keeps that account's token for reading the library. People
the owner shares that server with can then sign in with their own Plex accounts (or anyone,
if you allow it in Settings → Plex, where you also pick the server and libraries). Local
accounts still work alongside. Native clients use `POST /api/auth/plex/pin` then poll
`POST /api/auth/plex`. `tests/mock_plex.py` stands in for plex.tv and a Plex server when
developing offline (`PLEX_TV_URL`/`PLEX_AUTH_URL` point the app at it).

### Testing without the internet

`tests/` has stand-ins for every external service, including a private BitTorrent swarm:

```bash
.venv/bin/python -m uvicorn tests.local_swarm:app --port 8083   # seeder + tracker + .torrent files
.venv/bin/python -m uvicorn tests.mock_torznab:app --port 8082  # indexer whose results point at the swarm
```

Add `http://127.0.0.1:8082/api` as an indexer, add any movie, hit *find releases* → *Grab*,
and the built-in client really downloads the release from the local seeder, imports it,
and keeps seeding it. `tests/mock_tmdb.py`, `mock_tvmaze.py` and `mock_webhook.py` cover
the rest.

## Running it as a system service (Arch)

```bash
makepkg -si          # from this repo root
$EDITOR /etc/the-den/the-den.env
systemctl enable --now the-den
```

The web UI listens on `WEB_HOST:WEB_PORT` from `/etc/the-den/the-den.env`, `127.0.0.1:40204` by
default. Set `WEB_HOST=0.0.0.0` so the apps can find it on your LAN: The Den then advertises itself
over mDNS as `_theden._tcp`. Any bind that isn't loopback serves **HTTPS only** (`TLS=auto`, the
default): The Den makes its own key and self-signed certificate under `STATE_DIR/tls`, and the apps
pin that key (`/health` shows it as `tls_pin`). Set `PUBLIC_HOST` (for example your DDNS name) so the
certificate covers it. Browsers warn about a self-signed certificate; a trusted one needs a DNS
provider with an API (Cloudflare, planned). `TLS=off` is refused on anything but a loopback bind, and
the KDE client (0.5.0c) and the Android app (0.7.0b) can't pin yet, so they only reach a loopback or
plain-HTTP server until their next versions. The torrent client listens on `TORRENT_PORT` (default 6881,
TCP+UDP) on all interfaces; forward that port on your router for better peer connectivity.
The built-in Cloudflare solver opens Chromium headed when a display is available (that
clears the check most reliably); set `DEN_SOLVER_HEADLESS=1` to keep it windowless anyway,
for example on a dev box with WSLg where the browser would pop up on your desktop.
This packaging has been run for real through `makepkg -si` + `pacman -U` +
`systemctl enable --now` on genuine Arch Linux (WSL2, not literally CachyOS -- see
ROADMAP.md for details) and came up cleanly.

## Repository layout

- `app/`, `migrations/`, `tests/` -- the server (FastAPI + SQLite + libtorrent) and its offline mocks.
- The KDE desktop client lives in its own repo, [the-den-client](https://github.com/jamesyoungdahr-debug/the-den-client), with its own package; it carries a copy of the generated tokens from `design/exports/`.
- `design/` -- the HoltOS Glass tokens (`tokens.json`) and their generated exports for the web UI, the KDE client and the Android app.
- `docs/` -- the Requests and UI redesign plans.

## Discover

The home page browses TMDB: a trending hero, a **Recommended for you** rail built from
TMDB's recommendations for the titles you added most recently (minus what you already
have), then trending, popular and upcoming movies, popular series and what's on the air.
Every card carries your library's status, search covers movies and series together, and
the detail pages show cast, trailer, seasons and recommendations with an availability
card. Admins add a title to the library from there; series are matched to TVmaze (by TVDB
id, IMDb id, then exact title) for their episode lists. `tests/mock_tmdb.py` stands in for
TMDB offline (`TMDB_BASE_URL`).

## Plex and Requests

Connect the Plex account that owns your server in Settings → Plex, pick the server and the
movie/show libraries, and The Den scans them on a timer (default every 30 minutes, or
**Scan now**). Anything already on Plex shows as *available* on Discover, the detail
page lists which seasons Plex has, and the **Movies** and **TV** pages show the whole
collection: what The Den manages, what is only on Plex (with its Plex poster, served
through `/api/plex/thumb/{key}` so the Plex token never leaves the server), and what is
both, with an *On Plex* filter; admins can pull a Plex-only title into The Den with one
click. The apps read the same merged lists from `/api/library/movies` and
`/api/library/series`. Shared users of that server can sign in with Plex and
**request** a movie or particular seasons of a series from the detail page; The Den refuses
requests for what is already on Plex or in the library. Admins get a pending badge in the
sidebar and approve or decline (with a note) on **Requests**; an approval adds the title to
the library with only the requested seasons monitored, so automation searches for just those.
Admins and users marked *auto-approve* skip the queue. Non-admins have a request quota
(default 10 movies and 5 series per 7 days; change the defaults in Settings → Requests or
per person on Users; 0 means unlimited). When an approved request turns up, through an
import or the next Plex scan, it is marked *available* and Discord is told once. JSON twins
live at `/api/requests`, `/api/requests/quota` and `/api/plex/scan`.

## Accounts

Sign-in is always required; there is no anonymous access. The first visit to a fresh install
runs the setup (admin account, then server name and library folders). Create accounts on
Users, or let people sign in with Plex. Each app sign-in gets its own device token, sent as
`X-Api-Key`. People see and revoke their devices on their profile; admins can sign out all of
someone's devices on Users.

## How the built-in torrent client works

`app/torrent/engine.py` wraps one libtorrent session for the whole app. A grab adds the
release (magnet link, `.torrent` URL, or a URL that redirects to a magnet -- all three
shapes indexers use) straight into that session and records the info-hash. The automation
loop polls the session for progress, and when a download finishes the importer
**hard-links** the video file into the library (falling back to a copy across filesystems),
so the torrent keeps seeding from the downloads folder without a second copy on disk. Once
an imported torrent passes the seed ratio or seed time limit, it's stopped and the next
cycle removes it along with its downloaded data; the library keeps its link. Resume data
and the DHT table are saved under `STATE_DIR`, so a restart picks every torrent back up
where it was. The Downloads page shows all of this live, and lets you add torrents by hand,
pause/resume, and remove them.

## Design

The UI follows the HoltOS design system (`design/` in this repo -- colors, type,
component specs) by hand-translating its React/JSX components into plain CSS classes in
`app/static/den.css`, since this app deliberately has no JS framework (keeps it working
offline and easy to bundle into the distro). See `design/readme.md` for the source
system and `design/docs/brand-cheat-sheet.md` for the palette/type quick reference.

## What's real vs. what needs your input

- The app logic, protocol clients (Torznab/Newznab, TMDB), the torrent engine, scoring,
  scheduler, and packaging are all real and tested (against the local swarm and mocks --
  see above).
- You still need: real indexer accounts/API keys and -- if you want it -- a Discord webhook
  URL for notifications. Movie metadata comes from TMDB: a key shipped with the build
  (`BUILTIN_TMDB_API_KEY` in `app/config.py`) is used unless you set your own in Settings
  or `TMDB_API_KEY`. TV metadata uses TVmaze, which needs no key. This product uses the
  TMDB API but is not endorsed or certified by TMDB; non-commercial use only.
