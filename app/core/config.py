import os
from dotenv import load_dotenv

load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:
    BaseSettings = object
    SettingsConfigDict = None


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


DEFAULT_APP_NAME = os.getenv("APP_NAME", "CorretorIA")
DEFAULT_DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./data/app.db")
DEFAULT_MODEL_NAME = os.getenv("MODEL_NAME", "gemini-2.5-flash")

# Retira os valores hardcoded ("lucas_senha_123", "BotRiva1", "http://localhost:8080")
DEFAULT_ALLOW_FROM_ME_TEST = _env_bool("ALLOW_FROM_ME_TEST", True)
DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC = int(os.getenv("WEBHOOK_LOOP_GUARD_TTL_SEC", "30"))

if BaseSettings is object:
    class Settings:
        APP_NAME: str = DEFAULT_APP_NAME
        DB_URL: str = DEFAULT_DB_URL
        OPENAI_API_KEY: str | None = os.getenv("OPENAI_API_KEY")
        MODEL_NAME: str = DEFAULT_MODEL_NAME
        URL_EVOLUTION: str = os.getenv("URL_EVOLUTION", "")
        API_KEY_EVOLUTION: str = os.getenv("API_KEY_EVOLUTION", "")
        EVOLUTION_INSTANCE: str = os.getenv("EVOLUTION_INSTANCE", "")
        GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
        AI_TEMPERATURE: float = float(os.getenv("AI_TEMPERATURE", "0.6"))
        CHROMA_K: int = int(os.getenv("CHROMA_K", "4"))
        ALLOW_FROM_ME_TEST: bool = DEFAULT_ALLOW_FROM_ME_TEST
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC
        WHATSAPP_TEST_NUMBER: str = os.getenv("WHATSAPP_TEST_NUMBER", "")
        WHATSAPP_BOT_NUMBER: str = os.getenv("WHATSAPP_BOT_NUMBER", "")
        CORS_ORIGINS: list[str] = []

    settings = Settings()
else:
    class Settings(BaseSettings):
        APP_NAME: str = DEFAULT_APP_NAME
        DB_URL: str = DEFAULT_DB_URL

        OPENAI_API_KEY: str | None = None
        MODEL_NAME: str = DEFAULT_MODEL_NAME

        URL_EVOLUTION: str = ""
        API_KEY_EVOLUTION: str = ""
        EVOLUTION_INSTANCE: str = ""
        GEMINI_API_KEY: str = ""
        WHATSAPP_TEST_NUMBER: str = ""
        WHATSAPP_BOT_NUMBER: str = ""

        AI_TEMPERATURE: float = 0.6
        CHROMA_K: int = 4
        ALLOW_FROM_ME_TEST: bool = DEFAULT_ALLOW_FROM_ME_TEST
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC

        CORS_ORIGINS: list[str] = []

        model_config = SettingsConfigDict(
            env_file=".env",
            extra="allow",
        )

    settings = Settings()
