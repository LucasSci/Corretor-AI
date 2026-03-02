from fastapi import FastAPI
from app.db.init_db import init_db
from app.api.webhook import router as webhook_router

app = FastAPI(title="CorretorIA - MVP")

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/")
async def root():
    return {"name": "CorretorIA", "status": "running", "docs": "/docs"}

app.include_router(webhook_router)
