"""Отправка уведомлений менеджеру и админам."""
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup

from bot.config import Config

logger = logging.getLogger(__name__)


async def notify_manager(bot: Bot, config: Config, text: str,
                         markup: InlineKeyboardMarkup | None = None) -> int | None:
    """Пишет в чат менеджеров. Если не получилось — пробует админам. Возвращает message_id."""
    try:
        msg = await bot.send_message(config.manager_chat_id, text, reply_markup=markup)
        return msg.message_id
    except Exception as e:
        logger.error("Не удалось написать в MANAGER_CHAT_ID=%s: %s", config.manager_chat_id, e)
        await notify_admins(bot, config, text, markup)
        return None


async def notify_admins(bot: Bot, config: Config, text: str,
                        markup: InlineKeyboardMarkup | None = None) -> None:
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(admin_id, text, reply_markup=markup)
        except Exception as e:
            logger.error("Не удалось уведомить админа %s: %s", admin_id, e)
