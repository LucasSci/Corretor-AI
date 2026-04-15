import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
import uvicorn

from app.db.init_db import init_db
from app.api.webhook import router as webhook_router
from app.core.config import settings

@asynccontextmanager
async def lifespan(_: FastAPI):
    if init_db is not None:
        try:
            await init_db()
        except Exception as exc:
            logging.getLogger(__name__).warning("Database unavailable on startup: %s", exc)
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
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=settings.PORT,
    )
