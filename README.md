<p align="center">
  <img src="assets/logo.svg" width="72" alt="The Den">
</p>
<h1 align="center">The Den</h1>
<p align="center"><code>PART OF HOLTOS</code></p>

One self-hosted app in place of the usual four. What Sonarr, Radarr, Prowlarr and
qBittorrent each do separately, The Den does in a single process: indexer search, a
movie + TV library, quality-based release picking, a **built-in BitTorrent client**, and a
background loop that finds, downloads and imports what's missing on its own. No download
client to install, configure, or keep in sync. See the companion native desktop app:
[the-den-client](https://github.com/jamesyoungdahr-debug/the-den-client).

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
.venv/bin/python -m uvicorn app.main:app --port 8686
```

Then open http://127.0.0.1:8686. Configure TMDB key, library folders, the torrent client
(downloads folder, listen port, rate and seeding limits), automation interval, and Discord
webhook from **Settings** in the app itself -- or copy `.env.example` to `.env` (or export
the same variables) if you'd rather manage config as files; the in-app settings win if both
are set. Without either, the app still runs, just against nothing real.

### Accounts

The Den has local accounts with two roles. **Admins** see everything (Indexers, Downloads,
Users, Settings, add/remove/grab actions); **users** can browse the library, and in M11
will request titles. Sign-in is **optional by default** (`AUTH_REQUIRED=false`): anyone who
isn't signed in is treated as an admin, exactly as before accounts existed, so the desktop
and Android apps keep working until they gain a login step. Set `AUTH_REQUIRED=true` to
require sign-in everywhere; the first visit then shows `/setup` to create the admin.

Companion apps authenticate with a per-user **API token** (generate one on `/ui/profile`,
send it as `X-Api-Key`) or a session from `POST /api/auth/login`. `GET /api/auth/me` tells a
client who it is and whether it's an admin.

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

The web UI binds to `127.0.0.1:8686` only -- **there's no login/auth layer**, so put a
reverse proxy in front of it (or accept LAN-only access via SSH tunnel/VPN) before
exposing it beyond localhost. The torrent client listens on `TORRENT_PORT` (default 6881,
TCP+UDP) on all interfaces; forward that port on your router for better peer connectivity.
This packaging has been run for real through `makepkg -si` + `pacman -U` +
`systemctl enable --now` on genuine Arch Linux (WSL2, not literally CachyOS -- see
ROADMAP.md for details) and came up cleanly.

## Discover

The home page browses TMDB: a trending hero, a **Recommended for you** rail built from
TMDB's recommendations for the titles you added most recently (minus what you already
have), then trending, popular and upcoming movies, popular series and what's on the air.
Every card carries your library's status, search covers movies and series together, and
the detail pages show cast, trailer, seasons and recommendations with an availability
card. Admins add a title to the library from there; series are matched to TVmaze (by TVDB
id, IMDb id, then exact title) for their episode lists. Users get a Request button once
M11f lands. `tests/mock_tmdb.py` stands in for TMDB offline (`TMDB_BASE_URL`).

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
