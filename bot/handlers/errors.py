"""Глобальный обработчик ошибок: лог + уведомление админов + вежливый ответ клиенту."""
import logging
import traceback
from html import escape

from aiogram import Bot, Router
from aiogram.types import ErrorEvent

from bot import texts as t
from bot.config import Config
from bot.utils.notify import notify_admins

logger = logging.getLogger(__name__)
router = Router(name="errors")


@router.errors()
async def on_error(event: ErrorEvent, bot: Bot, config: Config):
    logger.exception("Ошибка при обработке update %s", event.update.update_id, exc_info=event.exception)

    upd = event.update
    user = None
    chat_id = None
    if upd.message:
        user, chat_id = upd.message.from_user, upd.message.chat.id
    elif upd.callback_query:
        user = upd.callback_query.from_user
        chat_id = upd.callback_query.message.chat.id if upd.callback_query.message else user.id

    trace = "".join(traceback.format_exception(event.exception))[-3000:]
    await notify_admins(bot, config, t.ERROR_ADMIN.format(
        update_id=upd.update_id,
        user_id=user.id if user else "—",
        trace=escape(trace),
    ))

    # Клиенту — короткое сообщение (только в личке)
    if chat_id and chat_id > 0 and chat_id not in config.admin_ids:
        try:
            await bot.send_message(chat_id, t.ERROR_USER)
        except Exception:
            pass
    return True
