"""Nutrition-specific keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.models.product import Product


def product_list_kb(products: list[Product]) -> InlineKeyboardMarkup:
    """Build inline keyboard from product search results."""
    buttons = [
        [
            InlineKeyboardButton(
                text=f"{p.name} — {p.calories_per_100g:.0f} ккал/100г",
                callback_data=f"product:{p.id}",
            )
        ]
        for p in products
    ]
    buttons.append([InlineKeyboardButton(text="Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def parsed_food_confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Сохранить", callback_data="parsed:save"),
                InlineKeyboardButton(text="Отмена", callback_data="cancel"),
            ]
        ]
    )
