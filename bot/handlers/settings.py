"""User settings section."""

from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.handlers.profile import show_profile
from bot.keyboards.settings import settings_kb
from bot.models.user import User
from bot.states.app import AppState

router = Router(name="settings")


async def open_settings(message: Message, state: FSMContext) -> None:
    await show_settings(message, state, edit=False)


async def show_settings(message: Message, state: FSMContext, *, edit: bool) -> None:
    text = (
        "<b>⚙️ Настройки</b>\n\n"
        "Выбери раздел. Здесь будут жить персонализация, уведомления, язык, "
        "часовой пояс и другие параметры."
    )
    if edit:
        try:
            await message.edit_text(text, reply_markup=settings_kb())
        except Exception:  # noqa: BLE001
            await message.answer(text, reply_markup=settings_kb())
    else:
        await message.answer(text, reply_markup=settings_kb())
    await state.set_state(AppState.viewing_settings)


@router.callback_query(F.data == "settings:profile")
async def on_settings_profile(
    callback: CallbackQuery,
    state: FSMContext,
    user: User,
) -> None:
    await show_profile(callback.message, state, user, edit=True)
    await callback.answer()


@router.callback_query(F.data.in_({"settings:menu", "settings:back_menu"}))
async def on_settings_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    from bot.handlers.main_menu import _build_menu_markup, _render_menu_header

    await state.clear()
    text = await _render_menu_header(user, session, date.today())
    markup = await _build_menu_markup(user, session)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=markup)
    await callback.answer()
