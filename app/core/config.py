import os
from dotenv import load_dotenv

load_dotenv()

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional

class Settings(BaseSettings):
    APP_NAME: str = "CorretorIA"
    DB_URL: str = "sqlite+aiosqlite:///./data/app.db"

    OPENAI_API_KEY: Optional[str] = None
    MODEL_NAME: str = "gemini-2.5-flash"

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
