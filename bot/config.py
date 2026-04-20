from pathlib import Path
from typing import Annotated

from pydantic import BeforeValidator
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


def _parse_admin_ids(value: object) -> list[int]:
    """Parse ADMIN_IDS from env formats like `1,2,3` or JSON-like lists."""
    if value is None or value == "":
        return []
    if isinstance(value, list):
        return [int(item) for item in value]
    if isinstance(value, int):
        return [value]

    raw = str(value).strip().strip("[]")
    if not raw:
        return []

    return [int(chunk.strip()) for chunk in raw.split(",") if chunk.strip()]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Telegram
    bot_token: SecretStr
    admin_ids: Annotated[list[int], BeforeValidator(_parse_admin_ids)] = []

    # Database
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

        return f"sqlite+aiosqlite:///{BASE_DIR / 'data' / 'bot.db'}"

    # Redis / FSM
    use_redis: bool = False
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

    @property
    def admin_ids_set(self) -> set[int]:
        return set(self.admin_ids)


settings = Settings()
