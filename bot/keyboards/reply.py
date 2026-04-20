"""Persistent reply keyboard.

The main reply keyboard is intentionally minimal — a single "🎯 Меню" button
that opens an inline action picker. All concrete actions live in
:data:`bot.states.app.INLINE_MENU_ACTIONS` and are rendered by
``bot.keyboards.inline.main_menu_kb``.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.states.app import MAIN_MENU_LABEL

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text=MAIN_MENU_LABEL)]],
    resize_keyboard=True,
    input_field_placeholder="Нажми «Меню» или введи команду…",
)
