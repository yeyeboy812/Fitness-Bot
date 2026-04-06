"""Onboarding-specific inline keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def gender_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Мужской", callback_data="gender:male"),
                InlineKeyboardButton(text="Женский", callback_data="gender:female"),
            ]
        ]
    )


def goal_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Похудеть", callback_data="goal:lose")],
            [InlineKeyboardButton(text="Поддерживать вес", callback_data="goal:maintain")],
            [InlineKeyboardButton(text="Набрать массу", callback_data="goal:gain")],
        ]
    )


def activity_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Сидячий образ жизни", callback_data="activity:sedentary")],
            [InlineKeyboardButton(text="Лёгкая активность (1-2 тр/нед)", callback_data="activity:light")],
            [InlineKeyboardButton(text="Умеренная (3-5 тр/нед)", callback_data="activity:moderate")],
            [InlineKeyboardButton(text="Высокая (6-7 тр/нед)", callback_data="activity:active")],
            [InlineKeyboardButton(text="Очень высокая (2 раза/день)", callback_data="activity:very_active")],
        ]
    )


def referral_source_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Instagram/TikTok", callback_data="ref:social")],
            [InlineKeyboardButton(text="Друг порекомендовал", callback_data="ref:friend")],
            [InlineKeyboardButton(text="Поиск в Telegram", callback_data="ref:search")],
            [InlineKeyboardButton(text="Другое", callback_data="ref:other")],
        ]
    )


def onboarding_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Всё верно, начнём!", callback_data="onb:confirm")],
            [InlineKeyboardButton(text="Хочу пересчитать", callback_data="onb:restart")],
        ]
    )
