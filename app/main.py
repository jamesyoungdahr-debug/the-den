from fastapi import FastAPI
from sqlalchemy import text

from app.db import engine
from app.routers import indexers

app = FastAPI(title="The Den")
app.include_router(indexers.router)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}
