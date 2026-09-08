import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./den.db")

TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "")
TMDB_BASE_URL = os.environ.get("TMDB_BASE_URL", "https://api.themoviedb.org/3")

QBIT_URL = os.environ.get("QBIT_URL", "http://127.0.0.1:8080")
QBIT_USERNAME = os.environ.get("QBIT_USERNAME", "admin")
QBIT_PASSWORD = os.environ.get("QBIT_PASSWORD", "adminadmin")

MOVIES_ROOT = os.environ.get("MOVIES_ROOT", "./library/movies")
TV_ROOT = os.environ.get("TV_ROOT", "./library/tv")

AUTOMATION_INTERVAL_SECONDS = int(os.environ.get("AUTOMATION_INTERVAL_SECONDS", "900"))

# A Discord "Webhook URL" from a channel's Integrations settings. Left blank, notifications are a no-op.
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK_URL", "")
