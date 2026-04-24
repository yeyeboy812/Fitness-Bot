"""CallbackData subclasses for structured callback routing."""

from aiogram.filters.callback_data import CallbackData


class ProductCB(CallbackData, prefix="product"):
    id: str  # UUID as string


class MealMethodCB(CallbackData, prefix="meal_method"):
    method: str  # search, manual, text, photo, recipe


class MealTypeCB(CallbackData, prefix="meal_type"):
    type: str  # breakfast, lunch, dinner, snack


class GenderCB(CallbackData, prefix="gender"):
    value: str


class GoalCB(CallbackData, prefix="goal"):
    value: str


class ActivityCB(CallbackData, prefix="activity"):
    value: str


