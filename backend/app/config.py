from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "PayOps AI API"
    database_url: str = "postgresql+psycopg://payops:payops@localhost:5432/payops"
    frontend_url: str = "http://localhost:3000"
    razorpay_key_id: str = ""
    razorpay_key_secret: SecretStr = SecretStr("")
    razorpay_webhook_secret: SecretStr = SecretStr("")
    razorpay_api_url: str = "https://api.razorpay.com/v1"
    openai_api_key: SecretStr = SecretStr("")
    openai_model: str = "gpt-5.4-mini"
    openai_timeout_seconds: float = 30.0
    openai_max_output_tokens: int = 700

    model_config = SettingsConfigDict(
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
