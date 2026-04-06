"""Simple in-memory anti-flood middleware."""

import time
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Update

# Minimum interval between messages from the same user (seconds)
THROTTLE_SECONDS = 0.5


class ThrottleMiddleware(BaseMiddleware):
    def __init__(self, rate: float = THROTTLE_SECONDS) -> None:
        self.rate = rate
        self._last_seen: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[Update, dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: dict[str, Any],
    ) -> Any:
        tg_user = data.get("event_from_user")
        if tg_user:
            now = time.monotonic()
            last = self._last_seen.get(tg_user.id, 0.0)
            if now - last < self.rate:
                return  # silently drop
            self._last_seen[tg_user.id] = now

        return await handler(event, data)
