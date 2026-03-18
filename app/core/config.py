import os
from typing import List, Optional
from dotenv import load_dotenv

load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    BaseSettings = object
    SettingsConfigDict = None

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

class Settings(BaseSettings if BaseSettings is not object else object):
    APP_NAME: str = os.getenv("APP_NAME", "CorretorIA")
    DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db")

    OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
    MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")

    URL_EVOLUTION: str = os.getenv("URL_EVOLUTION", "")
    API_KEY_EVOLUTION: str = os.getenv("API_KEY_EVOLUTION", "")
    EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

    AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.6"))
    CHROMA_K: int = int(os.getenv("CHROMA_K", "4"))

    ALLOW_FROM_ME_TEST: bool = _env_bool("ALLOW_FROM_ME_TEST", True)
    WEBHOOK_LOOP_GUARD_TTL_SEC: int = int(os.getenv("WEBHOOK_LOOP_GUARD_TTL_SEC", "30"))
    WHATSAPP_TEST_NUMBER: str = os.getenv("WHATSAPP_TEST_NUMBER", "")
    WHATSAPP_BOT_NUMBER: str = os.getenv("WHATSAPP_BOT_NUMBER", "")

    CORS_ORIGINS: List[str] = []

    if SettingsConfigDict is not None:
        model_config = SettingsConfigDict(
            env_file=".env",
            extra="allow",
        )

settings = Settings()
