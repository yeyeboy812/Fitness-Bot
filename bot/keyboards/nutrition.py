"""Nutrition-specific keyboards."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.keyboards.inline import back_button
from bot.models.product import Product


def search_prompt_kb() -> InlineKeyboardMarkup:
    """Keyboard shown with the 'enter product name' prompt."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [back_button("adding_food")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
        ]
    )


def amount_prompt_kb() -> InlineKeyboardMarkup:
    """Keyboard shown with the 'how many grams' prompt."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [back_button("food_search_results")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
        ]
    )


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
    buttons.append([back_button("food_search")])
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
