"""Stand-in for the notification targets so tests can verify notifications actually fire:
a Discord / generic webhook (POST /), an ntfy topic (POST /{topic}, headers Title/Tags/Priority/Click)
and a Telegram bot (POST /bot{token}/sendMessage). GET /received lists everything, POST /reset clears."""

from fastapi import FastAPI, Request

app = FastAPI()
received: list[dict] = []


@app.post("/")
async def webhook(request: Request):
    received.append(await request.json())
    return {"ok": True}


@app.post("/bot{token}/sendMessage")
async def telegram_webhook(token: str, request: Request):
    data = await request.json()
    received.append({"telegram": token, **data})
    return {"ok": True}


@app.post("/reset")
async def reset():
    received.clear()
    return {"ok": True}


@app.post("/{topic}")
async def topic_webhook(topic: str, request: Request):
    body = (await request.body()).decode()
    received.append({
        "topic": topic,
        "title": request.headers.get("Title"),
        "tags": request.headers.get("Tags"),
        "priority": request.headers.get("Priority"),
        "auth": request.headers.get("Authorization"),
        "click": request.headers.get("Click"),
        "message": body,
    })
    return {"ok": True}


@app.get("/received")
def get_received():
    return received
