"""Notifications: agents (Discord, ntfy, webhook, Telegram, Pushover) stored in
notification_agents, each subscribed to a set of events; notify_event fans one event out to
every enabled agent. Best-effort: a failing notification never breaks the action it reports on."""

import json

import httpx
from sqlalchemy.orm import Session

from app.models import NotificationAgent

EVENTS = {
    "grabbed": "Release grabbed",
    "imported": "Imported into the library",
    "upgraded": "Upgraded to a better release",
    "download_failed": "Download failed",
    "request_submitted": "Request submitted",
    "request_approved": "Request approved",
    "request_declined": "Request declined",
    "request_available": "Request now available",
    "health_warning": "Health warning",
}

KINDS = {
    "discord": ["webhook_url"],
    "ntfy": ["url", "topic", "token"],
    "webhook": ["url"],
    "telegram": ["bot_token", "chat_id"],
    "pushover": ["user_key", "app_token"],
}


async def send(kind: str, config: dict, title: str, message: str, event: str = "", link: str = "") -> None:
    """Send one notification through one agent kind. Raises on failure."""
    if kind not in KINDS:
        raise ValueError(f"unknown notification kind {kind!r}")

    async with httpx.AsyncClient(timeout=10) as client:
        match kind:
            case "discord":
                resp = await client.post(config["webhook_url"], json={"content": f"**{title}**\n{message}" if title else message})
            case "ntfy":
                url = f"{config['url'].rstrip('/')}/{config['topic']}"
                headers = {"Title": title, "Tags": event, "Priority": str(config.get("priority", 3))}
                if config.get("token"):
                    headers["Authorization"] = f"Bearer {config['token']}"
                if link:
                    headers["Click"] = link
                resp = await client.post(url, content=message.encode(), headers=headers)
            case "webhook":
                resp = await client.post(config["url"], json={"event": event, "title": title, "message": message, "link": link})
            case "telegram":
                base = config.get("api_url", "https://api.telegram.org").rstrip("/")  # api_url: tests point it at a mock
                resp = await client.post(
                    f"{base}/bot{config['bot_token']}/sendMessage",
                    json={"chat_id": config["chat_id"], "text": f"{title}\n{message}" if title else message},
                )
            case "pushover":
                resp = await client.post(
                    "https://api.pushover.net/1/messages.json",
                    data={"token": config["app_token"], "user": config["user_key"], "title": title, "message": message},
                )
            case _:
                raise ValueError(f"unknown notification kind {kind!r}")
        resp.raise_for_status()


async def notify_event(db: Session, event: str, message: str, title: str | None = None, legacy_discord_url: str = "", link: str = "") -> None:
    """Fan one event out to every enabled agent subscribed to it (empty list = all events).
    The legacy single Discord URL from Settings still fires unless an agent already covers it.
    link is a deep link (theden://...) that ntfy sends as the Click header and the webhook payload includes."""
    if not title:
        title = EVENTS.get(event, event)

    agents = db.query(NotificationAgent).filter(NotificationAgent.enabled == True).all()  # noqa: E712
    already = any(a.kind == "discord" and json.loads(a.config or "{}").get("webhook_url") == legacy_discord_url for a in agents)

    for agent in agents:
        config = json.loads(agent.config or "{}")
        subscribed = json.loads(agent.events or "[]")
        if not subscribed or event in subscribed:
            try:
                await send(agent.kind, config, title, message, event, link)
            except Exception:
                pass

    if legacy_discord_url and not already:
        try:
            await send("discord", {"webhook_url": legacy_discord_url}, title, message, event, link)
        except Exception:
            pass


async def test_agent(kind: str, config: dict) -> None:
    """Send a test message through an agent; raises so the caller can report the failure."""
    await send(kind, config, "The Den", "Test notification: this agent works.", "test")


async def notify(message: str, webhook_url: str) -> None:
    """Backward-compatible best-effort Discord post."""
    if webhook_url:
        try:
            await send("discord", {"webhook_url": webhook_url}, "", message)
        except Exception:
            pass
