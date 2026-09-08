# The Den

A single self-hosted app combining what Sonarr, Radarr, and Prowlarr do separately:
indexer search, a movie + TV library, quality-based release picking, download-client
integration, and a background loop that finds and grabs what's missing on its own.

See [ROADMAP.md](ROADMAP.md) for how it was built, milestone by milestone, and what's
still a known simplification.

## Running it for development

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt   # .venv/bin/pip on Linux
.venv/Scripts/python -m alembic upgrade head    # .venv/bin/python on Linux
.venv/Scripts/python -m uvicorn app.main:app --port 8686
```

Then open http://127.0.0.1:8686. Copy `.env.example` to `.env` (or export the same
variables) and fill in a real `TMDB_API_KEY` and your `QBIT_*` settings — without them
the app still runs, just against nothing real. See `tests/mock_*.py` for fake
TMDB/qBittorrent/Torznab servers used during development, if you want to poke at the
app without live accounts.

## Running it as a system service (Arch)

```bash
makepkg -si          # from this repo root
$EDITOR /etc/the-den/the-den.env
systemctl enable --now the-den
```

The service binds to `127.0.0.1:8686` only — **there's no login/auth layer**, so put a
reverse proxy in front of it (or accept LAN-only access via SSH tunnel/VPN) before
exposing it beyond localhost. This packaging has been written carefully against Arch
conventions but has **not been run through an actual `makepkg -si` + `pacman -U`** yet
(built from a Windows dev machine) — treat it as a solid first draft to test and fix up
on real hardware, not as verified.

## What's real vs. what needs your input

- The app logic, protocol clients (Torznab/Newznab, TMDB, qBittorrent WebUI), scoring,
  scheduler, and packaging are all real and tested (against mocks — see above).
- You still need: real indexer accounts/API keys, a real TMDB API key (free, 2-minute
  signup), qBittorrent actually installed and running, and — if you want it — a Discord
  webhook URL for notifications.
