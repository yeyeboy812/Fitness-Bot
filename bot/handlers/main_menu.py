"""Global main-menu router — registered first, highest priority.

Responsibilities
----------------
1. Handle the single reply "🎯 Меню" button: send a fresh message with the
   inline action picker (:func:`main_menu_kb`). Opening the picker itself
   never interrupts an active scenario — the user is just looking.
2. Handle ``menu:<action>`` callback presses from the inline picker:
   - if the user is mid-scenario (FSM state in
     ``INTERRUPTIBLE_STATE_NAMES``), ask for exit confirmation;
   - otherwise clear the state and dispatch to the section opener.
3. Handle ``menu_exit:*`` callbacks from the confirm dialog.

Why lives here and not per-feature
----------------------------------
Having a single owner for menu routing structurally guarantees that global
navigation is checked *before* any state-bound scenario handler — which is
the invariant the whole filter setup relies on.

Section openers are imported from the feature modules, so this router only
knows the action → opener mapping.
"""

from __future__ import annotations

import logging
from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.filters.menu import MainMenuFilter
from bot.handlers.admin import is_admin, render_admin_dashboard
from bot.handlers.analytics.dashboard import show_dashboard
from bot.handlers.nutrition.add_meal import open_add_food
from bot.handlers.nutrition.daily_summary import show_today
from bot.handlers.products.create import open_create_product
from bot.handlers.recipes.create import open_create_recipe
from bot.handlers.subscription import open_subscription
from bot.handlers.workout.start_workout import open_workout
from bot.keyboards.inline import confirm_exit_kb, main_menu_kb
from bot.models.user import User
from bot.repositories.meal import MealRepository
from bot.schemas.nutrition import DailySummary
from bot.services.nutrition import NutritionService
from bot.states.app import INLINE_MENU_ACTIONS, is_interruptible

logger = logging.getLogger(__name__)

router = Router(name="main_menu")


_VALID_ACTIONS = frozenset(INLINE_MENU_ACTIONS.values())


# ---------------------------------------------------------------------------
# Reply "🎯 Меню" press — opens the inline action picker
# ---------------------------------------------------------------------------
@router.message(MainMenuFilter())
async def on_main_menu_button(
    message: Message,
    user: User,
    session: AsyncSession,
) -> None:
    """Open the inline action picker as a single message.

    We intentionally do NOT check the interruptible state here: tapping
    "Меню" is a passive navigation action (the user is just browsing).
    The interruption prompt fires only when a concrete action is picked.
    """
    logger.info("menu_open user=%s", user.id)

    service = NutritionService(MealRepository(session))
    summary = await service.get_daily_summary(
        user.id,
        date.today(),
        calorie_norm=user.calorie_norm,
        protein_norm=user.protein_norm,
        fat_norm=user.fat_norm,
        carb_norm=user.carb_norm,
    )
    greeting = _progress_greeting(summary)

    sections = [
        "🍽 Питание и дневник",
        "🏋️ Тренировки и прогресс",
        "🥗 Свои продукты и рецепты",
    ]
    if is_admin(user.id):
        sections.append("🔐 Админ-инструменты")

    text = f"{greeting}\n\n" + "\n".join(sections)
    await message.answer(text, reply_markup=main_menu_kb(user.id))


def _progress_greeting(summary: DailySummary) -> str:
    """Pick a motivational header based on today's nutrition progress.

    Tiers (by calorie norm, with macro overshoot short-circuiting to the
    'stop' tier):
      • overshoot on any macro OR calories ≥ 100%  → stop
      • calories ≥ 80% of norm                      → almost there
      • any calories logged today                   → keep going
      • nothing logged yet                          → start
    """
    cal = summary.total_calories
    norm = summary.calorie_norm or 0

    macros = [
        (summary.total_calories, summary.calorie_norm),
        (summary.total_protein, summary.protein_norm),
        (summary.total_fat, summary.fat_norm),
        (summary.total_carbs, summary.carb_norm),
    ]
    overshoot = any(current > target for current, target in macros if target)

    if norm and (overshoot or cal >= norm):
        return "✋ Остановись-ка, бейба."
    if norm and cal >= norm * 0.8:
        return "🎯 Ты уже на пороге большого события — сделай это!\n\n👇 Выбери раздел:"
    if cal > 0:
        return "🔥 Молодец, ты можешь ещё больше!\n\n👇 Выбери раздел:"
    return "💪 Ну что, пора становиться сильным!\n\n👇 Выбери раздел:"


# ---------------------------------------------------------------------------
# Inline action pick — dispatch or ask for confirmation
# ---------------------------------------------------------------------------
@router.callback_query(F.data.startswith("menu:"))
async def on_menu_action(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    action = callback.data.split(":", 1)[1]
    if action not in _VALID_ACTIONS:
        logger.warning("unknown menu action: %s", action)
        await callback.answer("Неизвестное действие", show_alert=True)
        return

    current_state = await state.get_state()
    logger.info(
        "menu_pick user=%s action=%s current_state=%s",
        user.id, action, current_state,
    )

    # Active scenario with unsaved progress → ask for confirmation.
    if is_interruptible(current_state):
        await state.update_data(pending_menu_action=action)
        await callback.message.answer(
            "У тебя есть незавершённое действие.\n"
            "Выйти и перейти в другой раздел?",
            reply_markup=confirm_exit_kb(action),
        )
        await callback.answer()
        return

    await state.clear()
    await _dispatch(action, callback.message, state, session, user)
    await callback.answer()


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
# Global "back to menu" — returns user to the inline action picker
# ---------------------------------------------------------------------------
@router.callback_query(F.data == "back:main_menu")
async def on_back_to_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    await state.clear()
    service = NutritionService(MealRepository(session))
    summary = await service.get_daily_summary(
        user.id,
        date.today(),
        calorie_norm=user.calorie_norm,
        protein_norm=user.protein_norm,
        fat_norm=user.fat_norm,
        carb_norm=user.carb_norm,
    )
    greeting = _progress_greeting(summary)

    sections = [
        "🍽 Питание и дневник",
        "🏋️ Тренировки и прогресс",
        "🥗 Свои продукты и рецепты",
    ]
    if is_admin(user.id):
        sections.append("🔐 Админ-инструменты")

    text = f"{greeting}\n\n" + "\n".join(sections)
    try:
        await callback.message.edit_text(text, reply_markup=main_menu_kb(user.id))
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=main_menu_kb(user.id))
    await callback.answer()


@router.callback_query(F.data == "open_menu")
async def on_open_menu(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    """Handle the 'Открыть меню' button from /start."""
    await on_back_to_menu(callback, state, session, user)


# ---------------------------------------------------------------------------
# Dispatcher — maps action key to its section opener
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
    elif action == "pro":
        await open_subscription(message, user)
    elif action == "admin":
        if not is_admin(user.id):
            await message.answer("Этот раздел доступен только администратору.")
            return
        await render_admin_dashboard(message, session)
    else:
        logger.warning("unknown menu action: %s", action)
