"""Inline keyboard pagination helper."""

from typing import Any

from aiogram.types import InlineKeyboardButton

DEFAULT_PAGE_SIZE = 8


def paginate_items(
    items: list[Any],
    page: int = 0,
    page_size: int = DEFAULT_PAGE_SIZE,
) -> tuple[list[Any], bool, bool]:
    """Return (page_items, has_prev, has_next)."""
    start = page * page_size
    end = start + page_size
    return items[start:end], page > 0, end < len(items)


def pagination_row(
    prefix: str,
    page: int,
    has_prev: bool,
    has_next: bool,
) -> list[InlineKeyboardButton]:
    """Build navigation buttons row."""
    buttons = []
    if has_prev:
        buttons.append(
            InlineKeyboardButton(text="◀ Назад", callback_data=f"{prefix}:page:{page - 1}")
        )
    if has_next:
        buttons.append(
            InlineKeyboardButton(text="Вперёд ▶", callback_data=f"{prefix}:page:{page + 1}")
        )
    return buttons
