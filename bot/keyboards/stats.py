"""Stats screen keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.inline import back_to_menu_button
from bot.services.analytics import StatsPeriod


def stats_period_kb(
    active: StatsPeriod,
    *,
    all_time_locked: bool = False,
) -> InlineKeyboardMarkup:
    """Period switcher. Active period is marked with a dot prefix."""
    def label(text: str, period: StatsPeriod) -> str:
        if period is StatsPeriod.all_time and all_time_locked:
            text = f"🔒 {text}"
        return f"• {text}" if period is active else text

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=label("7 дней", StatsPeriod.week),
                    callback_data=f"stats:{StatsPeriod.week.value}",
                ),
                InlineKeyboardButton(
                    text=label("30 дней", StatsPeriod.month),
                    callback_data=f"stats:{StatsPeriod.month.value}",
                ),
                InlineKeyboardButton(
                    text=label("Всё время", StatsPeriod.all_time),
                    callback_data=f"stats:{StatsPeriod.all_time.value}",
                ),
            ],
            [back_to_menu_button()],
        ]
    )
