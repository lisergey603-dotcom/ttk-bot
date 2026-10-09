"""Ответы менеджера реплаем и обработка всего, что не попало в другие хендлеры."""
import logging
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramForbiddenError
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.config import Config
from bot.database import Database
from bot.handlers.faq import handle_free_text
from bot.keyboards import inline
from bot.utils.filters import IsStaff
from bot.utils.helpers import extract_user_id, tg_link_from_user
from bot.utils.notify import notify_manager

logger = logging.getLogger(__name__)
router = Router(name="common")

# Реплай на сообщение бота, в котором есть метка #id123
REPLY_TO_TAGGED = F.reply_to_message.func(
    lambda m: m.from_user and m.from_user.is_bot and extract_user_id(m.text or m.caption) is not None
)


@router.message(IsStaff(), REPLY_TO_TAGGED)
async def manager_reply(message: Message, bot: Bot, db: Database):
    """Менеджер ответил реплаем на вопрос/заявку — пересылаем клиенту."""
    src = message.reply_to_message
    user_id = extract_user_id(src.text or src.caption)
    try:
        if message.text:
            await bot.send_message(user_id, t.MANAGER_REPLY_TO_USER.format(text=escape(message.text)))
        else:  # фото, файл, голосовое — копируем как есть
            await bot.copy_message(user_id, message.chat.id, message.message_id)
        await message.reply(t.MANAGER_REPLY_SENT)
    except TelegramForbiddenError:
        await db.mark_blocked(user_id)
        await message.reply(t.MANAGER_REPLY_FAILED)


@router.message(F.chat.type == "private", F.text, ~F.text.startswith("/"))
async def free_text(message: Message, bot: Bot, config: Config, db: Database):
    await handle_free_text(message, bot, config, db)


@router.message(F.chat.type == "private", F.photo | F.document | F.voice | F.video)
async def client_file(message: Message, bot: Bot, config: Config):
    """Клиент прислал меню/рецептуры файлом — копируем менеджеру с меткой для ответа."""
    tag = t.MANAGER_USER_FILE.format(tg_link=tg_link_from_user(message.from_user),
                                     user_id=message.from_user.id)
    caption = (escape(message.caption) + "\n\n" if message.caption else "") + tag
    try:
        await bot.copy_message(config.manager_chat_id, message.chat.id, message.message_id,
                               caption=caption[:1024])
    except Exception as e:
        logger.error("Не удалось переслать файл менеджеру: %s", e)
        await notify_manager(bot, config, tag)
    await message.answer(t.USER_FILE_RECEIVED)


@router.message(F.chat.type == "private")
async def unknown_message(message: Message):
    await message.answer(t.FREE_TEXT_UNKNOWN_MEDIA, reply_markup=inline.main_menu())


@router.callback_query()
async def unknown_callback(callback: CallbackQuery):
    await callback.answer(t.UNKNOWN_CALLBACK, show_alert=True)
