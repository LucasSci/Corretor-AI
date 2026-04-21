import logging
from contextlib import asynccontextmanager
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.webhook import router as webhook_router
from app.core.config import settings

try:
    from app.db.init_db import init_db
except Exception as exc:
    init_db = None
    logging.getLogger(__name__).warning("Database unavailable on startup: %s", exc)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    try:
        if init_db is not None:
            await init_db()
    except Exception as exc:
        logger.warning("Database unavailable on startup: %s", exc)
    yield


app = FastAPI(title="CorretorIA - MVP", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
        port=settings.PORT,
    )
