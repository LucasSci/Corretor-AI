import logging
import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Evita quebra comum ao rodar com Python fora da venv do projeto.
def _bootstrap_local_venv() -> None:
    project_root = Path(__file__).resolve().parent.parent
    candidates = [
        project_root / ".venv" / "Lib" / "site-packages",  # Windows venv
        project_root / "venv" / "Lib" / "site-packages",   # Windows alt name
    ]

    # Linux/macOS venv layout
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
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "Dependencias ausentes: FastAPI nao encontrado. "
        "Ative a venv do projeto ou execute: "
        r".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
    ) from exc

# Permite executar via `python app/main.py` sem quebrar imports absolutos `from app...`.
if __package__ is None or __package__ == "":
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    from app.db.init_db import init_db
except Exception as exc:
    init_db = None
    logging.getLogger(__name__).warning("Banco indisponivel no startup: %s", exc)
from app.api.webhook import router as webhook_router


@asynccontextmanager
async def lifespan(_: FastAPI): # type: ignore
    if init_db is not None:
        await init_db()
    yield


app: FastAPI = FastAPI(title="CorretorIA - MVP", lifespan=lifespan)

@app.get("/health")
async def health() -> dict[str, bool]:
    return {"ok": True}

@app.get("/")
async def root() -> dict[str, str]:
    return {"name": "CorretorIA", "status": "running", "docs": "/docs"}

app.include_router(webhook_router)


if __name__ == "__main__":
    try:
        import uvicorn
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            "Dependencias ausentes: uvicorn nao encontrado. "
            "Ative a venv do projeto ou execute: "
            r".\.venv\Scripts\python.exe -m pip install -r requirements.txt"
        ) from exc

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
    )
