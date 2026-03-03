from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from pathlib import Path
from app.core.config import settings

if settings.DB_URL.startswith("sqlite+aiosqlite:///./"):
    db_path = settings.DB_URL.replace("sqlite+aiosqlite:///./", "", 1)
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

engine = create_async_engine(settings.DB_URL, echo=False)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)
