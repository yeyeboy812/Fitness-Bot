"""FSM states for onboarding flow."""

from aiogram.fsm.state import State, StatesGroup


class OnboardingSG(StatesGroup):
    name = State()
    gender = State()
    birth_year = State()
    height = State()
    weight = State()
    goal = State()
    activity = State()
    water = State()
    referral_source = State()
    confirm = State()
