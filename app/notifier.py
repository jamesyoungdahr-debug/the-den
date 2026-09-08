import httpx


async def notify(message: str, webhook_url: str) -> None:
    """Best-effort Discord webhook post. Silently does nothing if unconfigured or unreachable
    — a notification failing should never take down the grab/import it's reporting on."""
    if not webhook_url:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(webhook_url, json={"content": message})
    except Exception:
        pass
