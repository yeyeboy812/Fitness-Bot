"""Canonical FSM states and main-menu registry.

This module is the single source of truth for:
  - every user-facing FSM state the bot can be in;
  - the list of main-menu buttons and their action keys;
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
    workout_name_input = State()     # waiting for exercise name
    workout_set_input = State()      # waiting for "weight x reps"
    workout_in_progress = State()    # between-sets choice (add / next / finish)

    # --- Read-only / passive sections -------------------------------------
    # These are "transient" states — set briefly while rendering the section
    # so state transitions are observable in logs and tests.
    viewing_day = State()
    viewing_stats = State()
    viewing_products = State()
    viewing_recipes = State()
    settings = State()


# --- Main menu button registry --------------------------------------------
# Button label (exactly as shown to the user) → internal action key.
# Used by: the reply keyboard builder, MainMenuFilter, and the menu dispatcher.
MAIN_MENU_BUTTONS: dict[str, str] = {
    "Добавить еду": "add_food",
    "Мой день": "my_day",
    "Тренировка": "workout",
    "Статистика": "stats",
    "Продукты": "products",
    "Рецепты": "recipes",
    "Настройки": "settings",
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
    AppState.workout_name_input,
    AppState.workout_set_input,
    AppState.workout_in_progress,
})

_INTERRUPTIBLE_AUX_STATES: frozenset[State] = frozenset({
    CreateProductSG.enter_name,
    CreateProductSG.enter_calories,
    CreateProductSG.enter_protein,
    CreateProductSG.enter_fat,
    CreateProductSG.enter_carbs,
    CreateProductSG.confirm,
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
