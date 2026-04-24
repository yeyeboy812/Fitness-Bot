"""Entry point for the collector Telegram bot."""

import asyncio
import logging

from bot.config import settings
from bot.models.base import create_db_engine, create_session_factory, create_tables

from collector_bot.factory import create_bot, create_dispatcher

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    token = settings.collector_bot_token.get_secret_value()
    if not token:
        raise RuntimeError("COLLECTOR_BOT_TOKEN is not set in .env")

    db_url = settings.database_url
    engine = create_db_engine(db_url)
    session_factory = create_session_factory(engine)

    if "sqlite" in db_url:
        from bot.models import Base  # noqa: F401

        await create_tables(engine)
        logger.info("SQLite tables created for collector bot")

    bot = create_bot(settings.collector_bot_token)
    dp = create_dispatcher(session_factory=session_factory)

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
