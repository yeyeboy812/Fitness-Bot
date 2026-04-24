"""Shared inline keyboard builders."""

from typing import Protocol, Sequence

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup

from bot.access import is_admin
from bot.states.app import INLINE_MENU_ACTIONS


class ShortcutButton(Protocol):
    id: object
    label: str


def main_menu_kb(
    user_id: int | None = None,
    shortcuts: Sequence[ShortcutButton] | None = None,
) -> InlineKeyboardMarkup:
    """Inline picker shown after the user taps the reply "Меню" button.

    Layout:
    - nutrition and progress actions in pairs;
    - product tools as a separate utility row;
    - Pro CTA on its own;
    - admin row only for allowed accounts.
    """
    rows = [
        [
            InlineKeyboardButton(text="🍽 Добавить еду", callback_data="menu:add_food"),
            InlineKeyboardButton(text="📅 Мой день", callback_data="menu:my_day"),
        ],
        [
            InlineKeyboardButton(text="🏋️ Тренировка", callback_data="menu:workout"),
            InlineKeyboardButton(text="📈 Статистика", callback_data="menu:stats"),
        ],
        [
            InlineKeyboardButton(text="🥗 Продукты", callback_data="menu:products"),
            InlineKeyboardButton(text="🧾 Рецепты", callback_data="menu:recipes"),
        ],
    ]
    if shortcuts:
        shortcut_buttons = [
            InlineKeyboardButton(text=item.label, callback_data=f"shortcut:{item.id}")
            for item in shortcuts
        ]
        for idx in range(0, len(shortcut_buttons), 2):
            rows.append(shortcut_buttons[idx:idx + 2])

    rows.append([InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu:settings")])
    rows.append([InlineKeyboardButton(text="⭐ Pro", callback_data="menu:pro")])
    if is_admin(user_id):
        admin_label = next(
            label for label, action in INLINE_MENU_ACTIONS.items() if action == "admin"
        )
        rows.append([InlineKeyboardButton(text=admin_label, callback_data="menu:admin")])

    return InlineKeyboardMarkup(inline_keyboard=rows)


def back_button(target: str) -> InlineKeyboardButton:
    """Shared back button. ``target`` is read by the state-specific back handler."""
    return InlineKeyboardButton(text="⬅️ Назад", callback_data=f"back:{target}")


def back_to_menu_button() -> InlineKeyboardButton:
    """Back button that returns to the main inline menu."""
    return InlineKeyboardButton(text="⬅️ Назад", callback_data="back:main_menu")


def back_to_menu_kb() -> InlineKeyboardMarkup:
    """Standalone keyboard with just a back-to-menu button."""
    return InlineKeyboardMarkup(inline_keyboard=[[back_to_menu_button()]])


def my_day_kb() -> InlineKeyboardMarkup:
    """Quick actions on the «Мой день» screen.

    Reuses existing ``menu:add_food`` and ``menu:workout`` callbacks handled
    by the main-menu dispatcher, so no new routing is required.
    """
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="➕ Еда", callback_data="menu:add_food"),
                InlineKeyboardButton(text="🏋️ Тренировка", callback_data="menu:workout"),
            ],
            [back_to_menu_button()],
        ]
    )


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


def add_meal_method_kb(*, ai_features_locked: bool = False) -> InlineKeyboardMarkup:
    text_label = "🔒 Описать текстом" if ai_features_locked else "Описать текстом"
    photo_label = "🔒 Отправить фото" if ai_features_locked else "Отправить фото"

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="Поиск продукта", callback_data="meal_method:search")],
            [InlineKeyboardButton(text="Ввести вручную", callback_data="meal_method:manual")],
            [InlineKeyboardButton(text=text_label, callback_data="meal_method:text")],
            [InlineKeyboardButton(text=photo_label, callback_data="meal_method:photo")],
            [InlineKeyboardButton(text="Из рецепта", callback_data="meal_method:recipe")],
            [back_to_menu_button()],
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
            [back_button("food_amount")],
        ]
    )
