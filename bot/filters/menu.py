"""Filters that separate main-menu button presses from free text input.

`MainMenuFilter` is installed on the top-priority main-menu router so that
global buttons are handled before any scenario handler sees the message.

`NotMainMenuFilter` is the defense-in-depth counterpart: every state-bound
text handler applies it so that menu button labels can never be interpreted
as user input, even if router ordering regresses in the future.
"""

from __future__ import annotations

from aiogram.filters import BaseFilter
from aiogram.types import Message

from bot.models.user import User
from bot.states.app import MAIN_MENU_BUTTONS


class MainMenuFilter(BaseFilter):
    """Match messages whose text is one of the main-menu button labels.

    Additionally, during onboarding (user not yet onboarded) this filter
    intentionally does NOT match — onboarding keeps full control over input
    because the main menu keyboard is not shown to the user yet.
    """

    async def __call__(self, message: Message, user: User | None = None) -> bool:
        if user is not None and not user.onboarding_completed:
            return False
        text = message.text
        return bool(text is not None and text in MAIN_MENU_BUTTONS)


class NotMainMenuFilter(BaseFilter):
    """Reject main-menu button labels.

    Apply to free-text state handlers so they never capture a menu press,
    even if the top-level menu router ever fails to match first.
    Non-text messages (photo, sticker, …) pass through.
    """

    async def __call__(self, message: Message) -> bool:
        text = message.text
        if text is None:
            return True
        return text not in MAIN_MENU_BUTTONS
