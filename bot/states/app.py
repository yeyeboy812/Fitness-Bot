"""Canonical FSM states and main-menu registry.

This module is the single source of truth for:
  - every user-facing FSM state the bot can be in;
  - the single reply-menu label and the inline action registry;
  - which states represent an interruptible in-progress scenario.

`idle` is represented implicitly as ``state is None`` — no explicit member is
needed. Every other logical state from the product spec is listed here as an
``AppState`` member so handlers, filters, and the state-transition logger all
refer to a common vocabulary.
"""

from __future__ import annotations

from aiogram.fsm.state import State, StatesGroup

from bot.states.nutrition import CreateProductSG
from bot.states.recipe import CreateRecipeSG


class AppState(StatesGroup):
    """Unified FSM for all main user-facing flows."""

    # --- Add food flow -----------------------------------------------------
    adding_food = State()            # "Как добавить еду?" — method choice
    food_search = State()            # waiting for search query text
    food_search_results = State()    # waiting for product pick (callback)
    food_amount = State()            # waiting for grams
    food_meal_type = State()         # waiting for breakfast/lunch/dinner/snack
    food_manual_input = State()      # manual KBJU entry
    food_text_description = State()  # AI text parse
    food_photo_input = State()       # AI photo parse
    food_recipe_input = State()      # pick a saved recipe as meal

    # --- Workout flow ------------------------------------------------------
    workout_type_select = State()            # picking section: warmup/gym/home/cooldown
    workout_muscle_group_select = State()    # picking muscle group (gym only)
    workout_exercise_select = State()        # picking exercise from catalog
    workout_name_input = State()             # custom exercise name entry
    workout_fullbody_group_pick = State()    # pick canonical group for custom full-body name
    workout_load_choice = State()            # bodyweight: pick «no extra» / «with extra»
    workout_weight_input = State()           # external-weight entry (kg)
    workout_extra_weight_input = State()     # bodyweight + extra: extra weight (kg)
    workout_reps_input = State()             # reps entry
    workout_duration_input = State()         # duration entry (sec or mm:ss)
    workout_set_input = State()              # legacy "weight x reps" — kept for compat
    workout_in_progress = State()            # between-sets: add / finish-exercise / delete-last
    workout_exercise_summary = State()       # after exercise finished: next / repeat / finish / back

    # --- Read-only / passive sections -------------------------------------
    # These are "transient" states — set briefly while rendering the section
    # so state transitions are observable in logs and tests.
    viewing_day = State()
    viewing_stats = State()
    viewing_products = State()
    viewing_recipes = State()
    viewing_settings = State()
    viewing_profile = State()

    # --- Profile / personalization flow -----------------------------------
    profile_value_input = State()
    profile_confirm = State()


# --- Main reply-menu label ------------------------------------------------
# The only button on the persistent reply keyboard. Tapping it opens the
# inline action picker built from INLINE_MENU_ACTIONS.
MAIN_MENU_LABEL = "🎯 Меню"


# --- Inline menu registry -------------------------------------------------
# Button label (as shown inside the inline picker) → internal action key.
# Used by the inline keyboard builder and the menu dispatcher.
INLINE_MENU_ACTIONS: dict[str, str] = {
    "🍽 Добавить еду": "add_food",
    "📅 Мой день": "my_day",
    "🏋️ Тренировка": "workout",
    "📈 Статистика": "stats",
    "🥗 Продукты": "products",
    "🧾 Рецепты": "recipes",
    "⚙️ Настройки": "settings",
    "⭐ Pro": "pro",
    "🔐 Админка": "admin",
}


# --- Interruptible states -------------------------------------------------
# Pressing a main-menu button while in one of these states triggers the
# "exit confirmation" flow. Passive viewing states are excluded — they have
# no unsaved progress.
_INTERRUPTIBLE_APP_STATES: frozenset[State] = frozenset({
    AppState.adding_food,
    AppState.food_search,
    AppState.food_search_results,
    AppState.food_amount,
    AppState.food_meal_type,
    AppState.food_manual_input,
    AppState.food_text_description,
    AppState.food_photo_input,
    AppState.food_recipe_input,
    AppState.workout_type_select,
    AppState.workout_muscle_group_select,
    AppState.workout_exercise_select,
    AppState.workout_name_input,
    AppState.workout_fullbody_group_pick,
    AppState.workout_load_choice,
    AppState.workout_weight_input,
    AppState.workout_extra_weight_input,
    AppState.workout_reps_input,
    AppState.workout_duration_input,
    AppState.workout_set_input,
    AppState.workout_in_progress,
    AppState.workout_exercise_summary,
    AppState.profile_value_input,
    AppState.profile_confirm,
})

_INTERRUPTIBLE_AUX_STATES: frozenset[State] = frozenset({
    CreateProductSG.enter_name,
    CreateProductSG.enter_nutrition,
    CreateRecipeSG.enter_name,
    CreateRecipeSG.search_ingredient,
    CreateRecipeSG.select_ingredient,
    CreateRecipeSG.enter_ingredient_amount,
    CreateRecipeSG.ingredient_added,
    CreateRecipeSG.enter_servings,
    CreateRecipeSG.confirm,
})

INTERRUPTIBLE_STATE_NAMES: frozenset[str] = frozenset(
    s.state for s in (_INTERRUPTIBLE_APP_STATES | _INTERRUPTIBLE_AUX_STATES)
)


def is_interruptible(state_name: str | None) -> bool:
    """True if pressing a menu button in this state should prompt for exit."""
    return state_name is not None and state_name in INTERRUPTIBLE_STATE_NAMES
