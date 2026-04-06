"""Inner middleware that logs FSM state transitions for debugging.

Registered on message and callback_query observers so that ``FSMContext`` is
already injected into ``data`` by the time it runs. Emits one log line per
handler invocation *only when the state actually changes*, so idle chatter
does not spam the log.

Log records land in the ``bot.fsm`` logger — filter by that name to get a
clean transition trace when reproducing flow bugs.
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.fsm.context import FSMContext
from aiogram.types import TelegramObject

logger = logging.getLogger("bot.fsm")


class StateLoggerMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        state: FSMContext | None = data.get("state")
        before = await state.get_state() if state else None

        try:
            return await handler(event, data)
        finally:
            after = await state.get_state() if state else None
            if before != after:
                tg_user = data.get("event_from_user")
                uid = getattr(tg_user, "id", "?")
                logger.info(
                    "fsm_transition user=%s %s -> %s",
                    uid,
                    before or "idle",
                    after or "idle",
                )
