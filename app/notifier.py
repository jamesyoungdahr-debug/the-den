import httpx

from app import config


async def notify(message: str) -> None:
    """Best-effort Discord webhook post. Silently does nothing if unconfigured or unreachable
    — a notification failing should never take down the grab/import it's reporting on."""
    if not config.DISCORD_WEBHOOK_URL:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(config.DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception:
        pass
