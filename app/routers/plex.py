"""Admin-side Plex plumbing: the servers and libraries the owner's token can see, and the
Settings form that picks which one The Den is tied to."""

import json

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app import auth, plex, plex_scan, scheduler
from app import settings as settings_module
from app.deps import get_db
from app.models import PlexMedia

router = APIRouter(tags=["plex"])


def _owner_token(db: Session) -> str:
    token = settings_module.effective(db).plex_token
    if not token:
        raise HTTPException(409, "No Plex account is connected. Connect one from Settings first.")
    return token


@router.get("/api/plex/servers", dependencies=[Depends(auth.require_admin)])
async def api_servers(db: Session = Depends(get_db)):
    try:
        servers = await plex.list_servers(_owner_token(db))
    except plex.PlexError as exc:
        raise HTTPException(502, str(exc))
    return [s.__dict__ for s in servers]


@router.get("/api/plex/sections", dependencies=[Depends(auth.require_admin)])
async def api_sections(machine_id: str, db: Session = Depends(get_db)):
    token = _owner_token(db)
    servers = await plex.list_servers(token)
    server = next((s for s in servers if s.machine_id == machine_id), None)
    if server is None:
        raise HTTPException(404, "That server isn't visible to the connected Plex account")
    try:
        return {"server": server.__dict__, "sections": await plex.library_sections(server.uri, token)}
    except Exception as exc:
        raise HTTPException(502, f"Could not reach the Plex server at {server.uri}: {exc}")


@router.post("/api/plex/scan", dependencies=[Depends(auth.require_admin)])
async def api_scan(db: Session = Depends(get_db)):
    """Scan the configured Plex libraries now (also runs on the interval in Settings)."""
    try:
        return await plex_scan.scan(db)
    except plex_scan.NotConfigured:
        raise HTTPException(409, "Connect a Plex account and pick a server in Settings first")
    except Exception as exc:
        raise HTTPException(502, f"Plex scan failed: {exc}")


@router.get("/api/plex/scan", dependencies=[Depends(auth.require_admin)])
def api_scan_status(db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    return {
        "last_scan_at": row.plex_last_scan_at.isoformat() if row.plex_last_scan_at else None,
        "last_scan_result": row.plex_last_scan_result,
        "items": db.query(PlexMedia).count(),
        "interval_minutes": settings_module.effective(db).plex_scan_interval_minutes,
    }


@router.post("/ui/settings/plex/scan", dependencies=[Depends(auth.page_admin)])
async def ui_scan_now(db: Session = Depends(get_db)):
    try:
        result = await plex_scan.scan(db)
    except plex_scan.NotConfigured:
        return RedirectResponse("/ui/settings?error=Pick+a+Plex+server+first#plex", status_code=303)
    except Exception as exc:
        return RedirectResponse(f"/ui/settings?error=Plex+scan+failed:+{str(exc).replace(' ', '+')}#plex", status_code=303)
    summary = result.get("summary") or result.get("reason") or "done"
    return RedirectResponse(f"/ui/settings?notice=Plex+scan:+{summary.replace(' ', '+')}#plex", status_code=303)


@router.post("/ui/settings/plex", dependencies=[Depends(auth.page_admin)])
async def ui_save_plex(
    request: Request,
    server: str = Form(""),  # "<machine_id>|<name>|<uri>" from the select
    sections: list[str] = Form([]),
    allow_any: str = Form(""),
    scan_interval: str = Form(""),
    db: Session = Depends(get_db),
):
    row = settings_module.get_row(db)
    old_interval = settings_module.effective(db).plex_scan_interval_minutes
    row.plex_scan_interval_minutes = max(5, int(scan_interval)) if scan_interval.strip().isdigit() else None
    if server:
        machine_id, _, rest = server.partition("|")
        name, _, uri = rest.partition("|")
        row.plex_machine_id = machine_id or None
        row.plex_server_name = name or None
        row.plex_url = uri or None
    else:
        row.plex_machine_id = row.plex_server_name = row.plex_url = None
    row.plex_sections = json.dumps(sections) if sections else None
    row.plex_allow_any_account = allow_any == "1"
    db.commit()
    new_interval = settings_module.effective(db).plex_scan_interval_minutes
    if new_interval != old_interval:
        try:
            scheduler.reschedule_plex(new_interval)
        except Exception:
            pass
    return RedirectResponse("/ui/settings?saved=1#plex", status_code=303)


@router.post("/ui/settings/plex/disconnect", dependencies=[Depends(auth.page_admin)])
def ui_disconnect_plex(db: Session = Depends(get_db)):
    row = settings_module.get_row(db)
    row.plex_token = None
    row.plex_owner_id = None
    row.plex_owner_username = None
    db.commit()
    return RedirectResponse("/ui/settings#plex", status_code=303)
