"""FSM states for nutrition-related flows.

The main "add meal" scenario now uses :class:`bot.states.app.AppState`
(``adding_food`` / ``food_search`` / …). This module only keeps the
ancillary state groups: manual product creation and meal history browsing.
"""

from aiogram.fsm.state import State, StatesGroup


class CreateProductSG(StatesGroup):
    enter_name = State()
    enter_calories = State()
    enter_protein = State()
    enter_fat = State()
    enter_carbs = State()
    confirm = State()


class MealHistorySG(StatesGroup):
    select_date = State()
    view_meals = State()
