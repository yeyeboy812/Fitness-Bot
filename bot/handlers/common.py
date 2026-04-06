"""Common handlers: /start, /help, /cancel."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.states.onboarding import OnboardingSG

router = Router(name="common")


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    """Entry point. Redirects to onboarding if not completed, otherwise shows main menu."""
    await state.clear()

    if not user.onboarding_completed:
        await message.answer(
            "Привет! Я — твой фитнес-помощник.\n"
            "Давай настрою всё под тебя.\n\n"
            "Как тебя зовут?",
        )
        await state.set_state(OnboardingSG.name)
        return

    await message.answer(
        f"С возвращением, <b>{user.first_name}</b>!\n"
        "Выбери действие:",
        reply_markup=MAIN_MENU,
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>Доступные команды:</b>\n\n"
        "/start — Перезапуск\n"
        "/add — Добавить приём пищи\n"
        "/today — Итоги дня\n"
        "/workout — Начать тренировку\n"
        "/cancel — Отменить текущее действие\n"
        "/help — Эта справка\n\n"
        "Или используй кнопки меню.",
    )


@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current is None:
        await message.answer("Нечего отменять.")
        return
    await state.clear()
    await message.answer("Действие отменено.", reply_markup=MAIN_MENU)


@router.callback_query(F.data == "cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("Действие отменено.")
    await callback.answer()
