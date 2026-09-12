"""Notification agents (M15): CRUD and test endpoints for the web UI and the apps."""

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app import auth, notifier
from app.deps import get_db
from app.models import NotificationAgent

router = APIRouter(prefix="/api/notifications", tags=["notifications"], dependencies=[Depends(auth.require_admin)])

SECRET_KEYS = ("token", "webhook_url", "bot_token", "app_token", "user_key")


class AgentIn(BaseModel):
    name: str
    kind: str
    config: dict = {}
    events: list[str] = []
    enabled: bool = True


class AgentTest(BaseModel):
    kind: str
    config: dict = {}


def _out(agent) -> dict:
    """Secrets never echo back: the client only learns they are set (has_* flags)."""
    config = json.loads(agent.config or "{}")
    flags = {f"has_{key}": bool(config.get(key)) for key in SECRET_KEYS if key in notifier.KINDS.get(agent.kind, [])}
    for key in SECRET_KEYS:
        if isinstance(config.get(key), str) and config[key]:
            config[key] = ""
    return {
        "id": agent.id,
        "name": agent.name,
        "kind": agent.kind,
        "config": config,
        "events": json.loads(agent.events or "[]"),
        "enabled": agent.enabled,
        **flags,
    }


def _validate(kind: str, config: dict) -> None:
    if kind not in notifier.KINDS:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Unknown notification kind {kind!r}")
    for key in notifier.KINDS[kind]:
        if key != "token" and not config.get(key):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{kind}: {key} is required")


@router.get("/events")
def get_events():
    return [{"key": k, "label": v} for k, v in notifier.EVENTS.items()]


@router.get("/kinds")
def get_kinds():
    return [{"kind": k, "fields": v} for k, v in notifier.KINDS.items()]


@router.get("/agents")
def list_agents(db: Session = Depends(get_db)):
    agents = db.query(NotificationAgent).order_by(NotificationAgent.id).all()
    return [_out(agent) for agent in agents]


@router.post("/agents", status_code=status.HTTP_201_CREATED)
def create_agent(agent: AgentIn, db: Session = Depends(get_db)):
    _validate(agent.kind, agent.config)
    new_agent = NotificationAgent(name=agent.name, kind=agent.kind, config=json.dumps(agent.config), events=json.dumps(agent.events), enabled=agent.enabled)
    db.add(new_agent)
    db.commit()
    db.refresh(new_agent)
    return _out(new_agent)


@router.post("/test")
async def test_config(agent: AgentTest, db: Session = Depends(get_db)):
    _validate(agent.kind, agent.config)
    try:
        await notifier.test_agent(agent.kind, agent.config)
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Test failed: {exc}")
    return {"ok": True}


@router.post("/agents/{agent_id}/test")
async def test_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(NotificationAgent).filter(NotificationAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    try:
        await notifier.test_agent(agent.kind, json.loads(agent.config or "{}"))
    except Exception as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"Test failed: {exc}")
    return {"ok": True}


@router.put("/agents/{agent_id}")
def update_agent(agent_id: int, updates: AgentIn, db: Session = Depends(get_db)):
    agent = db.query(NotificationAgent).filter(NotificationAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    stored = json.loads(agent.config or "{}")
    stored.update({k: v for k, v in updates.config.items() if v not in ("", None)})  # blank secret keeps the stored one
    _validate(updates.kind, stored)
    agent.name = updates.name
    agent.kind = updates.kind
    agent.config = json.dumps(stored)
    agent.events = json.dumps(updates.events)
    agent.enabled = updates.enabled
    db.commit()
    return _out(agent)


@router.delete("/agents/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: int, db: Session = Depends(get_db)):
    agent = db.query(NotificationAgent).filter(NotificationAgent.id == agent_id).first()
    if not agent:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    db.delete(agent)
    db.commit()
