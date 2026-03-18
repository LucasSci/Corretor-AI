import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

def _bootstrap_local_venv() -> None:
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / ".venv" / "Lib" / "site-packages",
        project_root / "venv" / "Lib" / "site-packages",
    ]

    for py_site in (project_root / ".venv" / "lib").glob("python*/site-packages"):
        candidates.append(py_site)
    for py_site in (project_root / "venv" / "lib").glob("python*/site-packages"):
        candidates.append(py_site)

    for site_packages in candidates:
        if site_packages.exists():
            site_path = str(site_packages)
            if site_path not in sys.path:
                sys.path.insert(0, site_path)

_bootstrap_local_venv()

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Dependencias ausentes: FastAPI nao encontrado. "
        "Ative a venv do projeto ou execute: "
        r"python3 -m pip install -r requirements.txt"
    ) from exc

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings

try:
    from app.db.init_db import init_db
except Exception as exc:
    init_db = None
    logging.getLogger(__name__).warning("Banco indisponivel no startup: %s", exc)

from app.api.webhook import router as webhook_router

@asynccontextmanager
async def lifespan(_: FastAPI):
    if init_db is not None:
        await init_db()
    yield

app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/")
async def root():
    return {"name": settings.APP_NAME, "status": "running", "docs": "/docs"}

app.include_router(webhook_router)

if __name__ == "__main__":
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Dependencias ausentes: uvicorn nao encontrado. "
            "Ative a venv do projeto ou execute: "
            r"python3 -m pip install -r requirements.txt"
        ) from exc

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
