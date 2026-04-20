"""Workout-specific keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.inline import back_to_menu_button


def workout_start_kb() -> InlineKeyboardMarkup:
    """Keyboard shown at the start of a workout (exercise name prompt)."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[back_to_menu_button()]]
    )


def workout_action_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Ещё подход", callback_data="workout:add_set")],
            [InlineKeyboardButton(text="Следующее упражнение", callback_data="workout:next_exercise")],
            [InlineKeyboardButton(text="Завершить тренировку", callback_data="workout:finish")],
        ]
    )
