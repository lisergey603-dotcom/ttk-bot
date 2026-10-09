"""Показ экрана: по кнопке — редактируем текущее сообщение, по команде — шлём новое."""
from aiogram.exceptions import TelegramBadRequest
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message


async def render(event: Message | CallbackQuery, text: str,
                 markup: InlineKeyboardMarkup | None = None, edit: bool = True) -> None:
    if isinstance(event, Message):
        await event.answer(text, reply_markup=markup)
        return

    msg = event.message
    await event.answer()
    # Редактировать можно только обычные текстовые сообщения бота
    if edit and isinstance(msg, Message) and msg.text:
        try:
            await msg.edit_text(text, reply_markup=markup)
            return
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                return
            # не получилось (старое сообщение и т.п.) — отправим новое
    await msg.answer(text, reply_markup=markup)
