"""Persistent reply keyboards.

The main menu is built from ``MAIN_MENU_BUTTONS`` in ``bot.states.app`` so
that the button labels, the filter, and the menu dispatcher always stay in
sync — change the registry in one place and everything follows.
"""

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot.states.app import MAIN_MENU_BUTTONS

# Layout: 2+2+2+1 rows, matching the previous hand-crafted layout.
_LABELS = list(MAIN_MENU_BUTTONS.keys())
_LAYOUT_ROWS = [(0, 2), (2, 4), (4, 6), (6, 7)]

MAIN_MENU = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text=_LABELS[i]) for i in range(start, end)]
        for start, end in _LAYOUT_ROWS
    ],
    resize_keyboard=True,
    input_field_placeholder="Выберите действие...",
)
