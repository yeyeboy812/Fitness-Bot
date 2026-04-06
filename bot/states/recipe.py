"""FSM states for recipe creation flow."""

from aiogram.fsm.state import State, StatesGroup


class CreateRecipeSG(StatesGroup):
    enter_name = State()
    search_ingredient = State()
    select_ingredient = State()
    enter_ingredient_amount = State()
    ingredient_added = State()  # choose: add more / set servings / cancel
    enter_servings = State()
    confirm = State()
