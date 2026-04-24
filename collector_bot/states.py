"""FSM states for the collector bot."""

from aiogram.fsm.state import State, StatesGroup


class CollectorSG(StatesGroup):
    choosing_kind = State()
    exercise_name = State()
    exercise_muscle_group = State()
    exercise_type = State()
    product_name = State()
    product_brand = State()
    product_calories = State()
    product_protein = State()
    product_fat = State()
    product_carbs = State()
    recipe_name = State()
    recipe_total_weight = State()
    recipe_servings = State()
    recipe_calories = State()
    recipe_protein = State()
    recipe_fat = State()
    recipe_carbs = State()
