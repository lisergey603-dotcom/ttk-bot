"""Регистрирует пользователя и пишет входящие сообщения в messages_log."""
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.enums import ChatType
from aiogram.types import CallbackQuery, Message, TelegramObject

from bot.database import Database


class UserTrackingMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        db: Database = data["db"]
        user = data.get("event_from_user")
        chat = data.get("event_chat")

        # Учитываем только личные чаты с ботом (чат менеджеров — не клиенты)
        if user and not user.is_bot and chat and chat.type == ChatType.PRIVATE:
            await db.upsert_user(user.id, user.username, user.full_name)
            if isinstance(event, Message):
                text = event.text or event.caption or (f"[{event.content_type}]")
                await db.log_message(user.id, "in", text)
            elif isinstance(event, CallbackQuery):
                await db.log_message(user.id, "in", f"[btn] {event.data}")

        return await handler(event, data)
