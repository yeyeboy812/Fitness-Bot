"""Filters that separate the main-menu reply button from free-text input.

`MainMenuFilter` is installed on the top-priority main-menu router so that
the "Меню" button is handled before any scenario handler sees the message.

`NotMainMenuFilter` is the defense-in-depth counterpart: every state-bound
text handler applies it so that the menu label can never be interpreted as
user input, even if router ordering regresses in the future.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.models.user import User
from bot.states.app import MAIN_MENU_LABEL


class MainMenuFilter(BaseFilter):
    """Match messages whose text is the main-menu reply label.

    Additionally, during onboarding (user not yet onboarded) this filter
    intentionally does NOT match — onboarding keeps full control over input
    because the main menu keyboard is not shown to the user yet.
    """

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        if user is not None and not user.onboarding_completed:
            return False
        return message.text == MAIN_MENU_LABEL


class NotMainMenuFilter(BaseFilter):
    """Reject the main-menu reply label.

    Apply to free-text state handlers so they never capture a menu press,
    even if the top-level menu router ever fails to match first.
    Non-text messages (photo, sticker, …) pass through.
    """

    async def __call__(self, message: Message) -> bool:
        text = message.text
        if text is None:
            return True
        return text != MAIN_MENU_LABEL
