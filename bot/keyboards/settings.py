"""Inline keyboards for user settings."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def settings_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👤 Профиль / Персонализация",
                    callback_data="settings:profile",
                )
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="settings:back_menu"),
                InlineKeyboardButton(text="🎯 Меню", callback_data="settings:menu"),
            ],
        ]
    )
