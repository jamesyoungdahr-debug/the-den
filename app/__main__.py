"""Run The Den on WEB_HOST:WEB_PORT from app.config.

deploy/the-den.service starts it as `python -m app` from /opt/the-den, so the listen address
comes from /etc/the-den/the-den.env instead of being hardcoded in the unit.
"""

import uvicorn

from app import config

if __name__ == "__main__":
    uvicorn.run("app.main:app", host=config.WEB_HOST, port=config.WEB_PORT)
