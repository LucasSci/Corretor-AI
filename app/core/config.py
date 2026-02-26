from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    APP_NAME: str = "CorretorIA"
    DB_URL: str

    OPENAI_API_KEY: str | None = None
    MODEL_NAME: str = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
    )

settings = Settings()
