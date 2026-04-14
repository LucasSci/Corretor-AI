import logging
import os
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI
from app.db.init_db import init_db
from app.api.webhook import router as webhook_router

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(_: FastAPI):
    if init_db is not None:
        try:
            await init_db()
        except Exception as exc:
            logger.warning("Banco indisponivel no startup: %s", exc)
    yield

app = FastAPI(title="CorretorIA - MVP", lifespan=lifespan)

@app.get("/health")
async def health() -> Dict[str, Any]:
    return {"ok": True}

@app.get("/")
async def root() -> Dict[str, Any]:
    return {"name": "CorretorIA", "status": "running", "docs": "/docs"}

app.include_router(webhook_router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
