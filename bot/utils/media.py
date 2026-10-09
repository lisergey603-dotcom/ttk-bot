"""Отправка фото/документов с кэшем file_id — файл грузится в Telegram только один раз."""
from pathlib import Path

from aiogram import Bot
from aiogram.types import FSInputFile, Message

_file_ids: dict[str, str] = {}


async def send_cached(bot: Bot, chat_id: int, path: Path, kind: str, **kwargs) -> Message:
    key = str(path)
    media = _file_ids.get(key) or FSInputFile(path)
    send = bot.send_photo if kind == "photo" else bot.send_document
    msg = await send(chat_id, media, **kwargs)
    obj = msg.photo[-1] if kind == "photo" else msg.document
    _file_ids[key] = obj.file_id
    return msg
