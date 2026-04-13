import os
from typing import List, Optional

from dotenv import load_dotenv

# Load `.env` into environment variables
load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except ImportError:
    BaseSettings = object  # type: ignore
    SettingsConfigDict = None  # type: ignore

def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}

# Centralize configuration using pydantic-settings when possible.
# Ensure all credentials and environment variables use clean names without hardcoded fallback credentials.

if BaseSettings is object:
    class Settings: # type: ignore
        APP_NAME: str = os.getenv("APP_NAME", "CorretorIA")
        DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db")
        OPENAI_API_KEY: Optional[str] = os.getenv("OPENAI_API_KEY")
        MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-1.5-pro")

        URL_EVOLUTION: str = os.getenv("URL_EVOLUTION", "")
        API_KEY_EVOLUTION: str = os.getenv("API_KEY_EVOLUTION", "")
        EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "")
        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")

        WHATSAPP_TEST_NUMBER: str = os.getenv("WHATSAPP_TEST_NUMBER", "")
        WHATSAPP_BOT_NUMBER: str = os.getenv("WHATSAPP_BOT_NUMBER", "")

        AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.6"))
        CHROMA_K: int = int(os.getenv("CHROMA_K", "4"))
        ALLOW_FROM_ME_TEST: bool = _env_bool("ALLOW_FROM_ME_TEST", True)
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = int(os.getenv("WEBHOOK_LOOP_GUARD_TTL_SEC", "30"))

        CORS_ORIGINS: List[str] = []

    settings = Settings()
else:
    class Settings(BaseSettings): # type: ignore
        APP_NAME: str = "CorretorIA"
        DB_URL: str = "sqlite+aiosqlite:///./data/app.db"

        OPENAI_API_KEY: Optional[str] = None
        MODEL_NAME: str = "gemini-1.5-pro"

        URL_EVOLUTION: str = ""
        API_KEY_EVOLUTION: str = ""
        EVOLUTION_INSTANCE: str = ""
        GEMINI_API_KEY: str = ""
        WHATSAPP_TEST_NUMBER: str = ""
        WHATSAPP_BOT_NUMBER: str = ""

        AI_TEMPERATURE: float = 0.6
        CHROMA_K: int = 4
        ALLOW_FROM_ME_TEST: bool = True
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = 30

        CORS_ORIGINS: List[str] = []

        model_config = SettingsConfigDict(
            env_file=".env",
            extra="allow",
        )

    settings = Settings()

__all__ = ["settings"]
