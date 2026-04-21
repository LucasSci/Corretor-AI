import os

from dotenv import load_dotenv

from app.core.desktop_settings import (
    DEFAULT_DESKTOP_SETTINGS_PATH,
    flatten_settings_document,
    read_settings_document,
)

load_dotenv()

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
except Exception:
    BaseSettings = object
    SettingsConfigDict = None


_DESKTOP_SETTINGS_PATH = os.getenv("DESKTOP_SETTINGS_PATH", DEFAULT_DESKTOP_SETTINGS_PATH)
_DESKTOP_SETTINGS_DOC = read_settings_document(_DESKTOP_SETTINGS_PATH)
_DESKTOP_SETTINGS_ENV = flatten_settings_document(_DESKTOP_SETTINGS_DOC)


def _setting_raw(name: str, default=None):
    raw_env = os.getenv(name)
    if raw_env is not None:
        return raw_env
    if name in _DESKTOP_SETTINGS_ENV:
        return _DESKTOP_SETTINGS_ENV.get(name)
    return default


def _setting_str(name: str, default: str = "") -> str:
    raw = _setting_raw(name, default)
    if raw is None:
        return default
    if isinstance(raw, list):
        return ",".join(str(item) for item in raw)
    return str(raw)


def _setting_bool(name: str, default: bool) -> bool:
    raw = _setting_raw(name)
    if raw is None:
        return default
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _setting_int(name: str, default: int) -> int:
    raw = _setting_raw(name)
    if raw is None:
        return default
    try:
        return int(raw)
    except Exception:
        return default


def _setting_float(name: str, default: float) -> float:
    raw = _setting_raw(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except Exception:
        return default


def _setting_list(name: str, default: list[str] | None = None) -> list[str]:
    raw = _setting_raw(name)
    if raw is None:
        return list(default or [])
    if isinstance(raw, list):
        return [str(item).strip() for item in raw if str(item).strip()]
    return [item.strip() for item in str(raw).split(",") if item.strip()]


DEFAULT_APP_NAME = _setting_str("APP_NAME", "CorretorIA")
DEFAULT_DB_URL = _setting_str("DB_URL", "sqlite+aiosqlite:///./data/app.db")
DEFAULT_MODEL_NAME = _setting_str("MODEL_NAME", "gemini-2.5-flash")

# Compatibilidade com nomes antigos e valores locais do projeto.
DEFAULT_URL_EVOLUTION = (
    _setting_str("URL_EVOLUTION")
    or _setting_str("WHATSAPP_API_URL")
    or "http://localhost:8080"
)
DEFAULT_API_KEY_EVOLUTION = (
    _setting_str("API_KEY_EVOLUTION")
    or _setting_str("WHATSAPP_API_TOKEN")
    or _setting_str("WHATSAPP_API_KEY")
    or "lucas_senha_123"
)
DEFAULT_EVOLUTION_INSTANCE = (
    _setting_str("EVOLUTION_INSTANCE")
    or _setting_str("WHATSAPP_INSTANCE")
    or _setting_str("INSTANCIA")
    or "BotRiva1"
)
DEFAULT_ALLOW_FROM_ME_TEST = _setting_bool("ALLOW_FROM_ME_TEST", True)
DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC = _setting_int("WEBHOOK_LOOP_GUARD_TTL_SEC", 30)
DEFAULT_WHATSAPP_TEST_NUMBER = _setting_str("WHATSAPP_TEST_NUMBER", "")
DEFAULT_WHATSAPP_BOT_NUMBER = _setting_str("WHATSAPP_BOT_NUMBER", "")
DEFAULT_WHATSAPP_MEDIA_AUTO_SAVE = _setting_bool("WHATSAPP_MEDIA_AUTO_SAVE", True)
DEFAULT_WHATSAPP_UPLOADS_DIR = _setting_str("WHATSAPP_UPLOADS_DIR", "data/whatsapp_uploads")
DEFAULT_WHATSAPP_ALLOWED_NUMBERS = _setting_str("WHATSAPP_ALLOWED_NUMBERS", "")
DEFAULT_WHATSAPP_COMMAND_NUMBERS = _setting_str("WHATSAPP_COMMAND_NUMBERS", "") or DEFAULT_WHATSAPP_ALLOWED_NUMBERS
DEFAULT_HOST = _setting_str("HOST", "0.0.0.0")
DEFAULT_PORT = _setting_int("PORT", 8000)
DEFAULT_CORS_ORIGINS = _setting_list(
    "CORS_ORIGINS",
    [
        "http://127.0.0.1:1420",
        "http://localhost:1420",
        "http://127.0.0.1:5173",
        "http://localhost:5173",
    ],
)
DEFAULT_EVOLUTION_WEBHOOK_URL = _setting_str(
    "EVOLUTION_WEBHOOK_URL",
    f"http://host.docker.internal:{DEFAULT_PORT}/webhook",
)
DEFAULT_OUTPUT_LOG_PATH = _setting_str("OUTPUT_LOG_PATH", "output.log")
DEFAULT_ERROR_LOG_PATH = _setting_str("ERROR_LOG_PATH", "output.err.log")


if BaseSettings is object:
    class Settings:
        APP_NAME: str = DEFAULT_APP_NAME
        DB_URL: str = DEFAULT_DB_URL
        OPENAI_API_KEY: str | None = _setting_str("OPENAI_API_KEY", "") or None
        MODEL_NAME: str = DEFAULT_MODEL_NAME
        URL_EVOLUTION: str = DEFAULT_URL_EVOLUTION
        API_KEY_EVOLUTION: str = DEFAULT_API_KEY_EVOLUTION
        EVOLUTION_INSTANCE: str = DEFAULT_EVOLUTION_INSTANCE
        GEMINI_API_KEY: str = _setting_str("GEMINI_API_KEY", "")
        AI_TEMPERATURE: float = _setting_float("AI_TEMPERATURE", 0.6)
        CHROMA_K: int = _setting_int("CHROMA_K", 4)
        ALLOW_FROM_ME_TEST: bool = DEFAULT_ALLOW_FROM_ME_TEST
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC
        WHATSAPP_TEST_NUMBER: str = DEFAULT_WHATSAPP_TEST_NUMBER
        WHATSAPP_BOT_NUMBER: str = DEFAULT_WHATSAPP_BOT_NUMBER
        WHATSAPP_MEDIA_AUTO_SAVE: bool = DEFAULT_WHATSAPP_MEDIA_AUTO_SAVE
        WHATSAPP_UPLOADS_DIR: str = DEFAULT_WHATSAPP_UPLOADS_DIR
        WHATSAPP_ALLOWED_NUMBERS: str = DEFAULT_WHATSAPP_ALLOWED_NUMBERS
        WHATSAPP_COMMAND_NUMBERS: str = DEFAULT_WHATSAPP_COMMAND_NUMBERS
        EVOLUTION_WEBHOOK_URL: str = DEFAULT_EVOLUTION_WEBHOOK_URL
        HOST: str = DEFAULT_HOST
        PORT: int = DEFAULT_PORT
        CORS_ORIGINS: list[str] = DEFAULT_CORS_ORIGINS
        DESKTOP_SETTINGS_PATH: str = _DESKTOP_SETTINGS_PATH
        OUTPUT_LOG_PATH: str = DEFAULT_OUTPUT_LOG_PATH
        ERROR_LOG_PATH: str = DEFAULT_ERROR_LOG_PATH

    settings = Settings()
else:
    class Settings(BaseSettings):
        APP_NAME: str = DEFAULT_APP_NAME
        DB_URL: str = DEFAULT_DB_URL

        OPENAI_API_KEY: str | None = _setting_str("OPENAI_API_KEY", "") or None
        MODEL_NAME: str = DEFAULT_MODEL_NAME

        URL_EVOLUTION: str = DEFAULT_URL_EVOLUTION
        API_KEY_EVOLUTION: str = DEFAULT_API_KEY_EVOLUTION
        EVOLUTION_INSTANCE: str = DEFAULT_EVOLUTION_INSTANCE
        GEMINI_API_KEY: str = _setting_str("GEMINI_API_KEY", "")

        AI_TEMPERATURE: float = _setting_float("AI_TEMPERATURE", 0.6)
        CHROMA_K: int = _setting_int("CHROMA_K", 4)
        ALLOW_FROM_ME_TEST: bool = DEFAULT_ALLOW_FROM_ME_TEST
        WEBHOOK_LOOP_GUARD_TTL_SEC: int = DEFAULT_WEBHOOK_LOOP_GUARD_TTL_SEC
        WHATSAPP_TEST_NUMBER: str = DEFAULT_WHATSAPP_TEST_NUMBER
        WHATSAPP_BOT_NUMBER: str = DEFAULT_WHATSAPP_BOT_NUMBER
        WHATSAPP_MEDIA_AUTO_SAVE: bool = DEFAULT_WHATSAPP_MEDIA_AUTO_SAVE
        WHATSAPP_UPLOADS_DIR: str = DEFAULT_WHATSAPP_UPLOADS_DIR
        WHATSAPP_ALLOWED_NUMBERS: str = DEFAULT_WHATSAPP_ALLOWED_NUMBERS
        WHATSAPP_COMMAND_NUMBERS: str = DEFAULT_WHATSAPP_COMMAND_NUMBERS
        EVOLUTION_WEBHOOK_URL: str = DEFAULT_EVOLUTION_WEBHOOK_URL
        HOST: str = DEFAULT_HOST
        PORT: int = DEFAULT_PORT
        DESKTOP_SETTINGS_PATH: str = _DESKTOP_SETTINGS_PATH
        OUTPUT_LOG_PATH: str = DEFAULT_OUTPUT_LOG_PATH
        ERROR_LOG_PATH: str = DEFAULT_ERROR_LOG_PATH

        CORS_ORIGINS: list[str] = DEFAULT_CORS_ORIGINS

        model_config = SettingsConfigDict(
            env_file=".env",
            extra="allow",
        )

    settings = Settings()
