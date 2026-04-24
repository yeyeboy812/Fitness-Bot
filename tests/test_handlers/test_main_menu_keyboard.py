"""Regression guards for the main-menu inline keyboard.

These tests ensure the «Мой день» header refactor did not quietly change
the button grid, labels, or callback data. They treat the layout as a
snapshot — when a future change intentionally edits buttons, update the
expectation here deliberately.
"""

from __future__ import annotations

# Import handlers package first to avoid the circular-import trap when
# ``bot.keyboards.inline`` is loaded in isolation (it reaches into the admin
# handler, which pulls in sibling modules that need ``bot.keyboards.stats``).
import bot.handlers  # noqa: F401  — side-effect import, not unused
from bot.keyboards.inline import main_menu_kb


EXPECTED_NON_ADMIN_LAYOUT = [
    [("🍽 Добавить еду", "menu:add_food"), ("📅 Мой день", "menu:my_day")],
    [("🏋️ Тренировка", "menu:workout"), ("📈 Статистика", "menu:stats")],
    [("🥗 Продукты", "menu:products"), ("🧾 Рецепты", "menu:recipes")],
    [("⚙️ Настройки", "menu:settings")],
    [("⭐ Pro", "menu:pro")],
]


def _layout(markup) -> list[list[tuple[str, str]]]:
    return [[(b.text, b.callback_data) for b in row] for row in markup.inline_keyboard]


def test_main_menu_layout_for_regular_user_unchanged():
    markup = main_menu_kb(user_id=123456789)  # definitely not admin
    assert _layout(markup) == EXPECTED_NON_ADMIN_LAYOUT


def test_main_menu_has_no_admin_row_when_user_id_none():
    markup = main_menu_kb(user_id=None)
    assert _layout(markup) == EXPECTED_NON_ADMIN_LAYOUT


def test_main_menu_has_settings_not_direct_profile():
    layout = [
        item
        for row in _layout(main_menu_kb(user_id=123456789))
        for item in row
    ]

    assert ("⚙️ Настройки", "menu:settings") in layout
    assert ("👤 Профиль", "menu:profile") not in layout
