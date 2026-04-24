"""Common handlers: /start, /help, /cancel."""

from aiogram import F, Router
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from bot.access import is_admin
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.states.onboarding import OnboardingSG

router = Router(name="common")


def _start_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎯 Открыть меню", callback_data="open_menu")],
        ]
    )


_WELCOME_TEXT = (
    "Доброго времени суток, Чемпион!\n\n"
    "Я — <b>Iron Fitness Bot</b>, твой персональный помощник "
    "по питанию и тренировкам.\n\n"
    "<b>Что я умею:</b>\n"
    "• Считать калории и КБЖУ\n"
    "• Вести дневник питания\n"
    "• Логировать тренировки\n"
    "• Показывать статистику и прогресс\n"
    "• Хранить свои продукты и рецепты\n\n"
    "<b>Полезные команды:</b>\n"
    "/add — добавить приём пищи\n"
    "/today — итоги дня\n"
    "/workout — начать тренировку\n"
    "/help — подсказка по разделам\n"
    "/cancel — отменить текущее действие\n\n"
    "Нажми кнопку ниже, чтобы начать 👇"
)


@router.message(CommandStart())
async def cmd_start(message: Message, user: User, state: FSMContext) -> None:
    """Entry point. Redirects to onboarding if not completed, otherwise shows welcome."""
    await state.clear()

    if not user.onboarding_completed:
        await message.answer(
            "Привет! Я — твой фитнес-помощник.\n"
            "Давай настрою всё под тебя.\n\n"
            "Как тебя зовут?",
        )
        await state.set_state(OnboardingSG.name)
        return

    await message.answer(_WELCOME_TEXT, reply_markup=_start_kb())


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    user_id = message.from_user.id if message.from_user else None
    lines = [
        "<b>Как пользоваться ботом</b>",
        "",
        "Основное:",
        "/start — открыть бота заново",
        "/help — подсказка по разделам",
        "/cancel — отменить текущее действие",
        "",
        "Быстрые действия:",
        "/add — добавить приём пищи",
        "/today — посмотреть итоги дня",
        "/workout — начать тренировку",
        "",
        "Для всего остального нажми «🎯 Меню».",
    ]
    if is_admin(user_id):
        lines.extend(["", "<b>Админ</b>", "/admin — админ-панель"])

    await message.answer("\n".join(lines))


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
    # Return to idle — restore the reply "Меню" button for navigation.
    await callback.message.answer("Готов к следующему действию.", reply_markup=MAIN_MENU)
    await callback.answer()
