import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./den.db")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
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
