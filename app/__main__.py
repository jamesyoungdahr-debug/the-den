"""Run The Den on WEB_HOST:WEB_PORT from app.config.

deploy/the-den.service starts it as `python -m app` from /opt/the-den, so the listen address
comes from /etc/the-den/the-den.env instead of being hardcoded in the unit. HTTPS (M35) is on
unless WEB_HOST is a loopback address (TLS=auto); plain HTTP is refused on any other bind.
"""

import sys

import uvicorn

from app import config, tls


def _public_host() -> str | None:
    """The public name from Settings, or None when the database isn't ready yet."""
    try:
        from app import settings as settings_module
        from app.db import SessionLocal

        with SessionLocal() as db:
            return settings_module.effective(db).public_host
    except Exception:
        return None


if __name__ == "__main__":
    options = {}
    if tls.enabled():
        cert, key = tls.ensure_certificate(_public_host())
        options = {"ssl_certfile": str(cert), "ssl_keyfile": str(key)}
    elif not tls.is_loopback(config.WEB_HOST):
        sys.exit(f"The Den: TLS=off only works with a loopback WEB_HOST, not {config.WEB_HOST!r}; plain HTTP never leaves this machine.")
    uvicorn.run("app.main:app", host=config.WEB_HOST, port=config.WEB_PORT, **options)
