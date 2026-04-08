import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot.config import Settings

logger = logging.getLogger(__name__)


def create_bot(token: Any) -> Bot:
    """Create and return a Bot instance with HTML parse mode."""
    raw_token = token.get_secret_value() if hasattr(token, "get_secret_value") else str(token)

    return Bot(
        token=raw_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(
    session_factory: Any,
    settings: Settings,
) -> Dispatcher:
    """Create dispatcher with FSM storage, middlewares, and routers."""
    storage = _create_storage(
        use_redis=settings.use_redis,
        redis_url=settings.redis_url,
    )
    dp = Dispatcher(storage=storage)

    _register_middlewares(dp, session_factory=session_factory, settings=settings)
    _register_routers(dp)

    dp.startup.register(_on_startup)
    return dp


def _create_storage(*, use_redis: bool, redis_url: str):
    """Use MemoryStorage by default in local dev, Redis only when explicitly enabled."""
    if not use_redis:
        logger.info("USE_REDIS=false -> using MemoryStorage for FSM")
        return MemoryStorage()

    try:
        from aiogram.fsm.storage.redis import RedisStorage

        storage = RedisStorage.from_url(redis_url)
        logger.info("Using RedisStorage for FSM")
        return storage
    except Exception as exc:
        logger.warning("Redis unavailable (%s), falling back to MemoryStorage", exc)
        return MemoryStorage()


def _register_middlewares(
    dp: Dispatcher,
    *,
    session_factory: Any,
    settings: Settings,
) -> None:
    """Register all outer/inner middlewares on the dispatcher."""
    from bot.middlewares.db import DbSessionMiddleware
    from bot.middlewares.state_logger import StateLoggerMiddleware
    from bot.middlewares.throttle import ThrottleMiddleware
    from bot.middlewares.user import UserInjectMiddleware

    dp.update.outer_middleware(DbSessionMiddleware(session_factory=session_factory))
    dp.update.outer_middleware(UserInjectMiddleware())
    dp.update.outer_middleware(ThrottleMiddleware())

    state_logger = StateLoggerMiddleware()
    dp.message.middleware(state_logger)
    dp.callback_query.middleware(state_logger)


def _register_routers(dp: Dispatcher) -> None:
    """Import and include all handler routers."""
    from bot.handlers import register_all_routers

    register_all_routers(dp)


async def _on_startup(bot: Bot) -> None:
    """Set bot commands on startup."""
    commands = [
        BotCommand(command="start", description="Начать работу с ботом"),
        BotCommand(command="help", description="Помощь и список команд"),
        BotCommand(command="add", description="Добавить приём пищи / тренировку"),
        BotCommand(command="today", description="Статистика за сегодня"),
        BotCommand(command="workout", description="Начать тренировку"),
        BotCommand(command="cancel", description="Отменить текущее действие"),
    ]

    await bot.set_my_commands(commands)
    logger.info("Bot commands set successfully")
