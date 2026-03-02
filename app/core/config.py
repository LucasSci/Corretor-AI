from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CorretorIA"
    DB_URL: str

    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-4.1-mini"

    URL_EVOLUTION: str = ""
    API_KEY_EVOLUTION: str = ""
    GEMINI_API_KEY: str = ""

    AI_TEMPERATURE: float = 0.6
    CHROMA_K: int = 4

    # CORS Configuration
    CORS_ORIGINS: list[str] = []

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

settings = Settings()
