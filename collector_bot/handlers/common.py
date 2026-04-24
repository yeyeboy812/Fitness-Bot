"""Common collector bot commands."""

from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from bot.access import is_admin
from bot.models.user import User

from collector_bot.keyboards import submission_kind_kb
from collector_bot.states import CollectorSG

router = Router(name="collector_common")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CollectorSG.choosing_kind)

    lines = [
        f"Привет, <b>{user.first_name}</b>!",
        "",
        "Этот бот собирает новые сущности для общей базы данных.",
        "Выбери, что хочешь добавить: упражнение, продукт или рецепт.",
        "",
        "Каждая запись сохраняется вместе с твоим Telegram ID.",
    ]
    if is_admin(user.id):
        lines.extend(["", "Для модерации используй команду /pending."])

    await message.answer("\n".join(lines), reply_markup=submission_kind_kb())


@router.message(Command("help"))
async def cmd_help(message: Message, user: User) -> None:
    lines = [
        "<b>Команды collector bot</b>",
        "",
        "/start — начать ввод новой записи",
        "/help — показать помощь",
        "/cancel — отменить текущий ввод",
    ]
    if is_admin(user.id):
        lines.append("/pending — показать заявки на модерацию")
    await message.answer("\n".join(lines))


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(CollectorSG.choosing_kind)
    await message.answer("Ввод отменён. Выбери, что хочешь добавить.", reply_markup=submission_kind_kb())
