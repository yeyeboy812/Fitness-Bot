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
from uuid import UUID

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.access import is_admin
from bot.filters.menu import MainMenuFilter
from bot.handlers.admin import render_admin_dashboard
from bot.handlers.analytics.dashboard import show_dashboard
from bot.handlers.nutrition.add_meal import open_add_food
from bot.handlers.nutrition.daily_summary import show_today
from bot.handlers.products.create import open_create_product
from bot.handlers.recipes.create import open_create_recipe
from bot.handlers.settings import open_settings
from bot.handlers.subscription import open_subscription
from bot.handlers.workout.start_workout import open_workout
from bot.keyboards.inline import confirm_exit_kb, main_menu_kb
from bot.keyboards.reply import MAIN_MENU
from bot.models.agent import AgentEventType
from bot.models.user import User
from bot.repositories.agent import AgentEventRepository, UserShortcutRepository
from bot.repositories.meal import MealRepository
from bot.repositories.workout import WorkoutRepository
from bot.services.agent_events import AgentEventService
from bot.services.agent_shortcuts import AgentShortcutService
from bot.services.analytics import _compute_streaks
from bot.services.my_day import build_my_day_block, render_my_day_block
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
    event_service = AgentEventService(AgentEventRepository(session))
    await event_service.record(AgentEventType.menu_opened, user_id=user.id)
    text = await _render_menu_header(user, session, date.today())
    await message.answer(text, reply_markup=await _build_menu_markup(user, session))


async def _render_menu_header(
    user: User,
    session: AsyncSession,
    today: date,
) -> str:
    """Build the «Мой день» header shown above the inline action picker."""
    meal_repo = MealRepository(session)
    workout_repo = WorkoutRepository(session)

    totals = await meal_repo.get_daily_totals(user.id, today)
    activity = await workout_repo.get_daily_activity(user.id, today)
    workouts_today = int(activity["workouts_count"])

    meal_days = await meal_repo.get_active_dates(user.id)
    workout_days = await workout_repo.get_active_dates(user.id)
    current_streak, _ = _compute_streaks(meal_days | workout_days, today)

    block = build_my_day_block(
        calories_today=float(totals["calories"]),
        calorie_goal=user.calorie_norm,
        workouts_today=workouts_today,
        current_streak=current_streak,
        gender=user.gender,
    )
    return render_my_day_block(block)


async def _build_menu_markup(
    user: User,
    session: AsyncSession,
) -> InlineKeyboardMarkup:
    shortcut_service = AgentShortcutService(UserShortcutRepository(session))
    shortcuts = await shortcut_service.list_menu_shortcuts(user.id)
    return main_menu_kb(user.id, shortcuts=shortcuts)


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
    await AgentEventService(AgentEventRepository(session)).menu_action(
        user.id,
        action,
        current_state=current_state,
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


@router.callback_query(F.data.startswith("shortcut:"))
async def on_shortcut_action(
    callback: CallbackQuery,
    state: FSMContext,
    session: AsyncSession,
    user: User,
) -> None:
    try:
        shortcut_id = UUID(callback.data.split(":", 1)[1])
    except ValueError:
        await callback.answer("Неверная кнопка", show_alert=True)
        return

    event_service = AgentEventService(AgentEventRepository(session))
    shortcut_service = AgentShortcutService(
        UserShortcutRepository(session),
        NutritionService(MealRepository(session)),
    )
    shortcut = await shortcut_service.get_for_user(shortcut_id, user.id)
    if shortcut is None:
        await callback.answer("Кнопка больше недоступна", show_alert=True)
        return

    await event_service.shortcut_used(user.id, shortcut.id, shortcut.label)

    current_state = await state.get_state()
    result = await shortcut_service.execute(shortcut, user.id)

    if result.action == "menu_action":
        action = result.payload["action"]
        await event_service.menu_action(
            user.id,
            action,
            current_state=current_state,
        )
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
        return

    if result.action == "log_meal":
        await event_service.meal_logged(
            user.id,
            meal_id=UUID(result.payload["meal_id"]),
            source="shortcut",
            payload={"shortcut_id": shortcut.id, "label": shortcut.label},
        )
        await state.clear()
        await callback.message.answer(result.message)
        await callback.message.answer("Что дальше?", reply_markup=MAIN_MENU)
        await callback.answer("Сохранено!")
        return

    await callback.answer("Эта кнопка пока недоступна", show_alert=True)


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
    await AgentEventService(AgentEventRepository(session)).record(
        AgentEventType.menu_opened,
        user_id=user.id,
    )
    text = await _render_menu_header(user, session, date.today())
    markup = await _build_menu_markup(user, session)
    try:
        await callback.message.edit_text(text, reply_markup=markup)
    except Exception:  # noqa: BLE001
        await callback.message.answer(text, reply_markup=markup)
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
        await open_add_food(message, state, user)
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
        await open_settings(message, state)
    elif action == "pro":
        await open_subscription(message, user)
    elif action == "admin":
        if not is_admin(user.id):
            await message.answer("Этот раздел доступен только администратору.")
            return
        await render_admin_dashboard(message, session)
    else:
        logger.warning("unknown menu action: %s", action)
