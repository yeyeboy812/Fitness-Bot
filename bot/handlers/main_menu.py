"""Global main-menu router — registered first, highest priority.

Responsibilities
----------------
1. Detect any main-menu button press via :class:`MainMenuFilter`.
2. If the user is mid-scenario (FSM state in ``INTERRUPTIBLE_STATE_NAMES``)
   ask for exit confirmation using an inline dialog.
3. Otherwise clear the current state and dispatch to the per-section entry
   function (``open_add_food``, ``show_today``, …).
4. Handle ``menu_exit:*`` callback queries from the confirm dialog.

Why lives here and not per-feature
----------------------------------
Having a single owner for menu-button routing structurally guarantees that
global navigation is checked *before* any state-bound scenario handler —
which is exactly the bug we are fixing.

All section opener functions are thin wrappers around existing scenario
handlers exported from their own feature modules, so there is no duplicated
logic: this router only knows the menu → action map and the dispatch table.
"""

from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import MainMenuFilter
from bot.handlers.analytics.dashboard import show_dashboard
from bot.handlers.nutrition.add_meal import open_add_food
from bot.handlers.nutrition.daily_summary import show_today
from bot.handlers.products.create import open_create_product
from bot.handlers.recipes.create import open_create_recipe
from bot.handlers.workout.start_workout import open_workout
from bot.keyboards.inline import confirm_exit_kb
from bot.keyboards.reply import MAIN_MENU
from bot.models.user import User
from bot.states.app import (
    MAIN_MENU_BUTTONS,
    AppState,
    is_interruptible,
)

logger = logging.getLogger(__name__)

router = Router(name="main_menu")


# ---------------------------------------------------------------------------
# Menu button press — top-priority handler
# ---------------------------------------------------------------------------
@router.message(MainMenuFilter())
async def on_main_menu_button(
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Handle any main menu button press.

    Runs before all scenario routers because this router is included first
    in the dispatcher.
    """
    action = MAIN_MENU_BUTTONS[message.text]  # type: ignore[index]
    current_state = await state.get_state()

    logger.info(
        "menu_press user=%s action=%s current_state=%s",
        user.id, action, current_state,
    )

    # Active scenario with unsaved progress → ask for confirmation.
    if is_interruptible(current_state):
        await state.update_data(pending_menu_action=action)
        await message.answer(
            "У тебя есть незавершённое действие.\n"
            "Выйти и перейти в другой раздел?",
            reply_markup=confirm_exit_kb(action),
        )
        return

    # No active scenario (or only a passive view) → clear and dispatch.
    await state.clear()
    await _dispatch(action, message, state, session, user)


# ---------------------------------------------------------------------------
# Exit confirmation callbacks
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("menu_exit:confirm:"))
async def on_menu_exit_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    action = callback.data.split(":", 2)[2]
    logger.info("menu_exit_confirm user=%s action=%s", user.id, action)

    await state.clear()
    try:
        await callback.message.edit_text("Действие прервано.")
    except Exception:  # noqa: BLE001 — edit may fail on stale messages
        pass

    await _dispatch(action, callback.message, state, session, user)
    await callback.answer()


@router.callback_query(F.data == "menu_exit:cancel")
async def on_menu_exit_cancel(
    callback: CallbackQuery,
    state: FSMContext,
) -> None:
    logger.info("menu_exit_cancel user=%s", callback.from_user.id)
    # Clear the pending marker; keep current scenario state intact.
    data = await state.get_data()
    if "pending_menu_action" in data:
        data.pop("pending_menu_action")
        await state.set_data(data)
    try:
        await callback.message.delete()
    except Exception:  # noqa: BLE001
        pass
    await callback.answer("Продолжаем текущее действие")


# ---------------------------------------------------------------------------
# Dispatcher — maps menu action key to the section opener
# ---------------------------------------------------------------------------
async def _dispatch(
    action: str,
    message: Message,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    if action == "add_food":
        await open_add_food(message, state)
    elif action == "my_day":
        await show_today(message, state, session, user)
    elif action == "workout":
        await open_workout(message, state)
    elif action == "stats":
        await show_dashboard(message, state, session, user)
    elif action == "products":
        await open_create_product(message, state)
    elif action == "recipes":
        await open_create_recipe(message, state)
    elif action == "settings":
        await _open_settings(message, state)
    else:
        logger.warning("unknown menu action: %s", action)


async def _open_settings(message: Message, state: FSMContext) -> None:
    await state.set_state(AppState.settings)
    try:
        await message.answer(
            "Раздел настроек пока в разработке.",
            reply_markup=MAIN_MENU,
        )
    finally:
        await state.clear()
