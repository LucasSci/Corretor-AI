import logging
import os
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI

from app.api.webhook import router as webhook_router

try:
    from app.db.init_db import init_db
except Exception as exc:
    init_db = None
    logging.getLogger(__name__).warning("Database unavailable on startup: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI):
    if init_db is not None:
        await init_db()
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
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Missing dependencies: uvicorn not found. "
            "Activate the project venv or install requirements."
        ) from exc

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
