from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.sessions import SessionMiddleware

from app import auth, automation, scheduler
from app import settings as settings_module
from app.db import SessionLocal, engine as db_engine
from app.deps import get_db
from app.models import QualityProfile
from app.routers import api_settings, discover, downloads, indexers, library, movies, notifications, plex as plex_routes, requests as request_routes, search, series, torrents, ui, users
from app.routers import auth as auth_routes
from app.templating import templates
from app.torrent import engine as torrent_engine

app = FastAPI(title="The Den")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
app.include_router(auth_routes.router)
app.include_router(users.router)
app.include_router(plex_routes.router)
app.include_router(discover.router)
app.include_router(request_routes.router)
app.include_router(library.router)
app.include_router(indexers.router)
app.include_router(search.router)
app.include_router(movies.router)
app.include_router(series.router)
app.include_router(downloads.router)
app.include_router(torrents.router)
app.include_router(api_settings.router)
app.include_router(notifications.router)
app.include_router(ui.router)


@app.middleware("http")
async def load_current_user(request: Request, call_next):
    """Resolve the signed-in user (session cookie or X-Api-Key) once per request so
    guards and templates can read request.state.user without touching the DB again."""
    request.state.user = None
    if not request.url.path.startswith("/static/"):
        db = SessionLocal()
        try:
            request.state.user = auth.resolve_user(request, db)
        finally:
            db.close()
    return await call_next(request)


# Added after the user-loading middleware so it wraps it (Starlette: last added = outermost).
app.add_middleware(
    SessionMiddleware,
    secret_key=auth.session_secret(),
    session_cookie=auth.SESSION_COOKIE,
    max_age=auth.SESSION_MAX_AGE,
    same_site="lax",
    https_only=False,
)


@app.exception_handler(auth.LoginRequired)
async def _login_required(request: Request, exc: auth.LoginRequired):
    db = SessionLocal()
    try:
        target = "/login" if auth.users_exist(db) else "/setup"
    finally:
        db.close()
    if target == "/login" and exc.next_url and exc.next_url != "/":
        target += f"?next={exc.next_url}"
    return RedirectResponse(target, status_code=303)


@app.exception_handler(auth.Forbidden)
async def _forbidden(request: Request, exc: auth.Forbidden):
    return templates.TemplateResponse("forbidden.html", {"request": request}, status_code=403)


@app.on_event("startup")
def load_auth_override():
    """Settings -> Accounts may override the AUTH_REQUIRED env var (M11g)."""
    db = SessionLocal()
    try:
        auth.set_required_override(settings_module.get_row(db).auth_required)
    finally:
        db.close()


@app.on_event("startup")
def seed_default_quality_profile():
    db = SessionLocal()
    try:
        if not db.query(QualityProfile).first():
            db.add(QualityProfile(name="Default", allowed_qualities="1080p,720p,480p", cutoff="1080p"))
            db.commit()
    finally:
        db.close()


@app.on_event("startup")
async def start_torrent_engine():
    # Before the scheduler: its first cycle polls the engine for in-flight downloads.
    db = SessionLocal()
    try:
        cfg = settings_module.effective(db).engine_config()
    finally:
        db.close()
    torrent_engine.start(cfg)


@app.on_event("startup")
def start_scheduler():
    scheduler.start()


@app.on_event("shutdown")
def stop_scheduler():
    scheduler.stop()


@app.on_event("shutdown")
async def stop_torrent_engine():
    await torrent_engine.stop()
    from app.indexers import solver

    await solver.close()  # the built-in Cloudflare solver's Chromium, if it was started


@app.post("/automation/run-now", dependencies=[Depends(auth.require_admin)])
async def run_automation_now(db: Session = Depends(get_db)):
    await automation.run_cycle(db)
    return {"status": "ok"}


@app.get("/health")
def health():
    with db_engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok", "api_version": 2, "auth_required": auth.required(), "torrent_engine": torrent_engine.info()}


@app.get("/forbidden", response_class=HTMLResponse, include_in_schema=False)
def forbidden_page(request: Request):
    return templates.TemplateResponse("forbidden.html", {"request": request}, status_code=403)
