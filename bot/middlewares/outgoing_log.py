"""Логирует исходящие сообщения бота в messages_log (на уровне HTTP-сессии)."""
from aiogram.client.session.middlewares.base import BaseRequestMiddleware, NextRequestMiddlewareType
from aiogram.methods import EditMessageText, SendDocument, SendMessage, SendPhoto, TelegramMethod
from aiogram.methods.base import TelegramType

from bot.database import Database


class OutgoingLogMiddleware(BaseRequestMiddleware):
    def __init__(self, db: Database):
        self.db = db

    async def __call__(self, make_request: NextRequestMiddlewareType[TelegramType], bot, method: TelegramMethod[TelegramType]):
        result = await make_request(bot, method)
        try:
            if isinstance(method, (SendMessage, EditMessageText)) and isinstance(method.chat_id, int):
                await self.db.log_message(method.chat_id, "out", method.text)
            elif isinstance(method, (SendDocument, SendPhoto)) and isinstance(method.chat_id, int):
                await self.db.log_message(method.chat_id, "out", f"[{type(method).__name__}] {method.caption or ''}")
        except Exception:  # лог не должен ронять отправку
            pass
        return result
