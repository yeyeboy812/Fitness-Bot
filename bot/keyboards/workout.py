"""Workout-specific keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def workout_action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ещё подход", callback_data="workout:add_set")],
            [InlineKeyboardButton(text="Следующее упражнение", callback_data="workout:next_exercise")],
            [InlineKeyboardButton(text="Завершить тренировку", callback_data="workout:finish")],
        ]
    )
