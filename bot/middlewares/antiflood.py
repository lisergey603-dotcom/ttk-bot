"""Антифлуд: не более N событий за период (по умолчанию 5 за 10 сек) на пользователя."""
import time
from collections import defaultdict, deque
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot import texts as t


class AntiFloodMiddleware(BaseMiddleware):
    def __init__(self, limit: int = 5, period: float = 10.0, exempt_ids: set[int] | None = None):
        self.limit = limit
        self.period = period
        self.exempt_ids = exempt_ids or set()
        self.hits: dict[int, deque[float]] = defaultdict(deque)
        self.warned: dict[int, float] = {}

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user = data.get("event_from_user")
        chat = data.get("event_chat")
        # Админов и рабочий чат менеджеров не ограничиваем
        if not user or user.id in self.exempt_ids or (chat and chat.id in self.exempt_ids):
            return await handler(event, data)

        now = time.monotonic()
        q = self.hits[user.id]
        while q and now - q[0] > self.period:
            q.popleft()

        if len(q) >= self.limit:
            # Предупреждаем не чаще раза за период, остальное молча игнорируем
            if now - self.warned.get(user.id, 0) > self.period:
                self.warned[user.id] = now
                if isinstance(event, Message):
                    await event.answer(t.ANTIFLOOD)
                elif isinstance(event, CallbackQuery):
                    await event.answer(t.ANTIFLOOD, show_alert=False)
            elif isinstance(event, CallbackQuery):
                await event.answer()
            return None

        q.append(now)
        # Периодически чистим словарь, чтобы не рос бесконечно
        if len(self.hits) > 10_000:
            for uid in [u for u, d in self.hits.items() if not d or now - d[-1] > self.period]:
                self.hits.pop(uid, None)
                self.warned.pop(uid, None)
        return await handler(event, data)
