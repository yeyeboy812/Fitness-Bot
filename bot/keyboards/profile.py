"""Inline keyboards for profile and personalization flows."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def profile_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Изменить имя", callback_data="profile:edit:name")],
            [InlineKeyboardButton(text="⚧ Изменить пол", callback_data="profile:edit:gender")],
            [
                InlineKeyboardButton(
                    text="🎂 Изменить год рождения",
                    callback_data="profile:edit:birth_year",
                )
            ],
            [InlineKeyboardButton(text="✏️ Изменить вес", callback_data="profile:edit:weight")],
            [InlineKeyboardButton(text="📏 Изменить рост", callback_data="profile:edit:height")],
            [InlineKeyboardButton(text="🎯 Изменить цель", callback_data="profile:edit:goal")],
            [
                InlineKeyboardButton(
                    text="🏃 Изменить активность",
                    callback_data="profile:edit:activity",
                )
            ],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:back_settings"),
                InlineKeyboardButton(text="🎯 Меню", callback_data="profile:menu"),
            ],
        ]
    )


def profile_back_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:back")],
            [InlineKeyboardButton(text="🎯 Меню", callback_data="profile:menu")],
        ]
    )


def profile_choice_kb(field: str, choices: list[tuple[str, str]]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(text=label, callback_data=f"profile:value:{field}:{value}")]
        for label, value in choices
    ]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="profile:back")])
    rows.append([InlineKeyboardButton(text="🎯 Меню", callback_data="profile:menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def profile_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Сохранить", callback_data="profile:save"),
                InlineKeyboardButton(text="↩️ Отменить", callback_data="profile:cancel"),
            ],
            [InlineKeyboardButton(text="🎯 Меню", callback_data="profile:menu")],
        ]
    )
