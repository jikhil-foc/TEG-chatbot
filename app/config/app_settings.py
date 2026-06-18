from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "TEG Chatbot API"
    debug: bool = False
    host: str = "0.0.0.0"
    port: int = 8000
    website_url: str = "https://www.teg.ie/"


settings = Settings()
