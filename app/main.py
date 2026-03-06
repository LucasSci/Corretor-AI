import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncGenerator

# Bootstrap local venv
def _bootstrap_local_venv() -> None:
    project_root: Path = Path(__file__).resolve().parent.parent
    candidates: list[Path] = [
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
        "Ative a venv do projeto ou instale os requisitos."
    ) from exc

if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.api.webhook import router as webhook_router
from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncGenerator[None, None]:
    # Startup actions
    logger.info("Iniciando API %s", settings.APP_NAME)
    yield
    # Shutdown actions
    logger.info("Encerrando API %s", settings.APP_NAME)


app = FastAPI(title=settings.APP_NAME, lifespan=lifespan)

if settings.CORS_ORIGINS:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}

@app.get("/")
async def root() -> dict[str, str]:
    return {"name": settings.APP_NAME, "status": "running", "docs": "/docs"}

app.include_router(webhook_router)

if __name__ == "__main__":
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Dependencias ausentes: uvicorn nao encontrado."
        ) from exc

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )
