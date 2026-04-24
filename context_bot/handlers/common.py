"""Common context bot commands."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.access import is_admin
from bot.models.user import User

router = Router(name="context_common")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User) -> None:
    if not is_admin(user.id):
        await message.answer("Этот бот доступен только администратору.")
        return

    lines = [
        f"Привет, <b>{user.first_name}</b>!",
        "",
        "Это отдельный context bot для управления assistant bridge-слоем.",
        "Он живет в пакете <code>context_bot/</code> и не смешивается с основным fitness bot.",
        "",
        "Основная команда сейчас: /status",
    ]
    await message.answer("\n".join(lines))


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    if not is_admin(user.id):
        await message.answer("Этот бот доступен только администратору.")
        return

    lines = [
        "<b>Команды context bot</b>",
        "",
        "/start - открыть bot",
        "/help - показать помощь",
        "/status - посмотреть состояние bridge-слоя",
        "",
        "Граница кода: Telegram orchestration живет в <code>context_bot/</code>,",
        "shared DB/ORM/services остаются в <code>bot/</code>.",
    ]
    await message.answer("\n".join(lines))
