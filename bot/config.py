from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    # Telegram bot
    bot_token: SecretStr

    # Database — SQLite by default, PostgreSQL when DB_HOST is set
    db_host: str = ""
    db_port: int = 5432
    db_user: str = "postgres"
    db_password: SecretStr = SecretStr("postgres")
    db_name: str = "fitness_bot"

    @property
    def database_url(self) -> str:
        if self.db_host:
            return (
                f"postgresql+asyncpg://{self.db_user}:"
                f"{self.db_password.get_secret_value()}@"
                f"{self.db_host}:{self.db_port}/{self.db_name}"
            )
        # Local SQLite fallback
        return f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}"

    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379

    @property
    def redis_url(self) -> str:
        return f"redis://{self.redis_host}:{self.redis_port}/0"

    # OpenAI
    openai_api_key: SecretStr = SecretStr("")
    openai_text_model: str = "gpt-4o"
    openai_vision_model: str = "gpt-4o"
    openai_daily_text_limit: int = 20
    openai_daily_photo_limit: int = 5
    openai_monthly_budget_usd: float = 30.0

    # General
    log_level: str = "INFO"
    debug: bool = False


settings = Settings()
