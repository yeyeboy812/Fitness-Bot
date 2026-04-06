"""Shared inline keyboard builders."""

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")]
        ]
    )


def confirm_cancel_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data="confirm"),
                InlineKeyboardButton(text="Отмена", callback_data="cancel"),
            ]
        ]
    )


def add_meal_method_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поиск продукта", callback_data="meal_method:search")],
            [InlineKeyboardButton(text="Ввести вручную", callback_data="meal_method:manual")],
            [InlineKeyboardButton(text="Описать текстом", callback_data="meal_method:text")],
            [InlineKeyboardButton(text="Отправить фото", callback_data="meal_method:photo")],
            [InlineKeyboardButton(text="Из рецепта", callback_data="meal_method:recipe")],
            [InlineKeyboardButton(text="Отмена", callback_data="cancel")],
        ]
    )


def confirm_exit_kb(action: str) -> InlineKeyboardMarkup:
    """Inline confirm dialog shown when a menu button is pressed during an
    active scenario. ``action`` is the pending menu action key — the callback
    handler reads it back from the callback_data payload.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Выйти",
                    callback_data=f"menu_exit:confirm:{action}",
                ),
                InlineKeyboardButton(
                    text="Остаться",
                    callback_data="menu_exit:cancel",
                ),
            ]
        ]
    )


def meal_type_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Завтрак", callback_data="meal_type:breakfast"),
                InlineKeyboardButton(text="Обед", callback_data="meal_type:lunch"),
            ],
            [
                InlineKeyboardButton(text="Ужин", callback_data="meal_type:dinner"),
                InlineKeyboardButton(text="Перекус", callback_data="meal_type:snack"),
            ],
        ]
    )
