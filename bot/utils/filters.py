"""Фильтры доступа."""
from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message

from bot.config import Config


class IsAdmin(BaseFilter):
    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        return bool(event.from_user and event.from_user.id in config.admin_ids)


class IsStaff(BaseFilter):
    """Админ или любое событие из чата менеджеров."""

    async def __call__(self, event: Message | CallbackQuery, config: Config) -> bool:
        msg = event.message if isinstance(event, CallbackQuery) else event
        if event.from_user and event.from_user.id in config.admin_ids:
            return True
        return bool(msg and msg.chat.id == config.manager_chat_id)
