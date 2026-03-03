from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.init_db import init_db
from app.api.webhook import router as webhook_router
from app.core.config import settings

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def on_startup() -> None:
    await init_db()

@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}

@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.APP_NAME, "status": "running", "docs": "/docs"}

app.include_router(webhook_router)
