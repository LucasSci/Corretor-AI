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

if BaseSettings is object:
    class Settings:
        APP_NAME: str = os.getenv("APP_NAME", "CorretorIA")
        DB_URL: str = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db")

        # Configurações da Evolution API
        URL_EVOLUTION: str = os.getenv("URL_EVOLUTION", "http://localhost:8080")
        API_KEY_EVOLUTION: str = os.getenv("API_KEY_EVOLUTION", "")
        EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "BotRiva1")

        # Configurações do Gemini e AI
        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        MODEL_NAME: str = os.getenv("MODEL_NAME", "gemini-2.5-flash")
        AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.6"))
        CHROMA_K: int = int(os.getenv("CHROMA_K", "4"))

        # Configurações do WhatsApp Webhook
        ALLOW_FROM_ME_TEST: bool = _env_bool("ALLOW_FROM_ME_TEST", True)
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = int(os.getenv("WEBHOOK_LOOP_GUARD_TTL_SEC", "30"))
        WHATSAPP_TEST_NUMBER: str = os.getenv("WHATSAPP_TEST_NUMBER", "")
        WHATSAPP_BOT_NUMBER: str = os.getenv("WHATSAPP_BOT_NUMBER", "")

        CORS_ORIGINS: List[str] = []

    settings = Settings()
else:
    class Settings(BaseSettings):
        APP_NAME: str = "CorretorIA"
        DB_URL: str = "sqlite+aiosqlite:///./data/app.db"

        # Configurações da Evolution API
        URL_EVOLUTION: str = "http://localhost:8080"
        API_KEY_EVOLUTION: str = ""
        EVOLUTION_INSTANCE: str = "BotRiva1"

        # Configurações do Gemini e AI
        GEMINI_API_KEY: str = ""
        MODEL_NAME: str = "gemini-2.5-flash"
        AI_TEMPERATURE: float = 0.6
        CHROMA_K: int = 4

        # Configurações do WhatsApp Webhook
        ALLOW_FROM_ME_TEST: bool = True
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = 30
        WHATSAPP_TEST_NUMBER: str = ""
        WHATSAPP_BOT_NUMBER: str = ""

        CORS_ORIGINS: List[str] = []

        model_config = SettingsConfigDict(
            env_file=".env",
            extra="allow",
        )

    settings = Settings()
