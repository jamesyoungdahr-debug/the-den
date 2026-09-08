"""Stand-in for a Discord webhook so we can verify notifications actually fire."""

from fastapi import FastAPI, Request

app = FastAPI()
received: list[dict] = []


@app.post("/")
async def webhook(request: Request):
    received.append(await request.json())
    return {"ok": True}


@app.get("/received")
def get_received():
    return received
