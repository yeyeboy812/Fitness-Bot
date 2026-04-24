"""Factory helpers for the collector bot."""

from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat

from bot.config import settings


def create_bot(token: Any) -> Bot:
    raw_token = token.get_secret_value() if hasattr(token, "get_secret_value") else str(token)
    return Bot(
        token=raw_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(session_factory: Any) -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    _register_middlewares(dp, session_factory=session_factory)
    _register_routers(dp)
    dp.startup.register(_on_startup)
    return dp


def _register_middlewares(dp: Dispatcher, *, session_factory: Any) -> None:
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
    from collector_bot.handlers import register_all_routers

    register_all_routers(dp)


async def _on_startup(bot: Bot) -> None:
    public_commands = [
        BotCommand(command="start", description="Начать ввод данных"),
        BotCommand(command="help", description="Справка по collector bot"),
        BotCommand(command="cancel", description="Отменить текущий ввод"),
    ]
    admin_commands = public_commands + [
        BotCommand(command="pending", description="Заявки на модерацию"),
    ]

    await bot.set_my_commands(public_commands)

    for admin_id in settings.admin_ids:
        await bot.set_my_commands(
            admin_commands,
            scope=BotCommandScopeChat(chat_id=admin_id),
        )
