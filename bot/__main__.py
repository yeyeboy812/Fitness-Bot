import asyncio
import logging

from bot.config import settings
from bot.factory import create_bot, create_dispatcher
from bot.models.base import create_db_engine, create_session_factory, create_tables

logger = logging.getLogger(__name__)


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    db_url = settings.database_url
    logger.info("Database: %s", "SQLite (local)" if "sqlite" in db_url else "PostgreSQL")

    engine = create_db_engine(db_url)
    session_factory = create_session_factory(engine)

    # Auto-create tables for SQLite dev mode (use Alembic for PostgreSQL)
    if "sqlite" in db_url:
        from bot.models import Base  # noqa: F401 — triggers all model imports
        await create_tables(engine)
        logger.info("SQLite tables created")

    bot = create_bot(settings.bot_token)
    dp = create_dispatcher(session_factory=session_factory, settings=settings)

    try:
        await dp.start_polling(bot)
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
