import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./den.db")

# A key shipped with the build, used when neither Settings nor TMDB_API_KEY provides one
# (the approach Overseerr takes). Non-commercial use only; TMDB requires the attribution the
# Settings page and README carry. Paste the key between the quotes to bake it in.
BUILTIN_TMDB_API_KEY = "9d4ba852db15c627e0803cea1b14dab1"
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "") or BUILTIN_TMDB_API_KEY
TMDB_BASE_URL = os.environ.get("TMDB_BASE_URL", "https://api.themoviedb.org/3")

# TVmaze needs no key/account at all, for real use -- this override exists only for tests.
TVMAZE_BASE_URL = os.environ.get("TVMAZE_BASE_URL", "https://api.tvmaze.com")

# Where finished movies/episodes get linked into.
MOVIES_ROOT = os.environ.get("MOVIES_ROOT", "./library/movies")
TV_ROOT = os.environ.get("TV_ROOT", "./library/tv")

# Built-in torrent client (app/torrent). Torrents download into DOWNLOADS_ROOT and keep
# seeding there after import; STATE_DIR holds resume data + DHT state across restarts
# and is not user-editable from the UI (it's an install-location concern, not a preference).
DOWNLOADS_ROOT = os.environ.get("DOWNLOADS_ROOT", "./downloads")
STATE_DIR = os.environ.get("STATE_DIR", "./state")
TORRENT_PORT = int(os.environ.get("TORRENT_PORT", "6881"))
DOWNLOAD_RATE_LIMIT_KIB = int(os.environ.get("DOWNLOAD_RATE_LIMIT_KIB", "0"))  # 0 = unlimited
UPLOAD_RATE_LIMIT_KIB = int(os.environ.get("UPLOAD_RATE_LIMIT_KIB", "0"))  # 0 = unlimited
SEED_RATIO_LIMIT = float(os.environ.get("SEED_RATIO_LIMIT", "2.0"))  # 0 = seed forever
SEED_TIME_LIMIT_MINUTES = int(os.environ.get("SEED_TIME_LIMIT_MINUTES", "0"))  # 0 = no time limit

AUTOMATION_INTERVAL_SECONDS = int(os.environ.get("AUTOMATION_INTERVAL_SECONDS", "900"))

# A Discord "Webhook URL" from a channel's Integrations settings. Left blank, notifications are a no-op.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")

# Accounts. AUTH_REQUIRED=false (the default until the companion apps gain a login step)
# keeps every page and API open exactly as before accounts existed, while still letting
# people sign in. Set it to true to require a login everywhere; the first run then shows
# /setup to create the admin. SESSION_SECRET signs the session cookie; left blank, one is
# generated once and kept under STATE_DIR.
AUTH_REQUIRED = os.environ.get("AUTH_REQUIRED", "false").strip().lower() in ("1", "true", "yes", "on")
SESSION_SECRET = os.environ.get("SESSION_SECRET", "")

# Plex. The owner's token and server are normally set from Settings (stored in the DB);
# these env defaults exist for headless setups. The two URLs only change for tests/mock_plex.py.
PLEX_TOKEN = os.environ.get("PLEX_TOKEN", "")
PLEX_URL = os.environ.get("PLEX_URL", "")
PLEX_TV_URL = os.environ.get("PLEX_TV_URL", "https://plex.tv")
PLEX_AUTH_URL = os.environ.get("PLEX_AUTH_URL", "https://app.plex.tv/auth")
PLEX_SCAN_INTERVAL_MINUTES = int(os.environ.get("PLEX_SCAN_INTERVAL_MINUTES", "30"))
