from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/surveydb"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # OpenAI
    openai_api_keys: str = ""  # comma-separated list of API keys
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    parse_model: str = "gpt-4o-mini"

    # Token pricing (USD per 1K tokens)
    prompt_token_price: float = 0.00015   # gpt-4o-mini input
    completion_token_price: float = 0.0006  # gpt-4o-mini output

    # Admin
    admin_username: str = "admin"
    admin_password: str = "changeme"
    jwt_secret: str = "changeme-jwt-secret-32chars-min!!"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # App
    cors_origins: str = "http://localhost:3000,http://localhost:80"
    redis_task_ttl: int = 1800  # 30 minutes
    download_token_ttl: int = 3600  # 1 hour

    def get_api_keys(self) -> List[str]:
        return [k.strip() for k in self.openai_api_keys.split(",") if k.strip()]

    def get_cors_origins(self) -> List[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
