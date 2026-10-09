"""Reply-клавиатуры (кнопки под полем ввода)."""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

from bot import texts as t


def main_reply() -> ReplyKeyboardMarkup:
    """Постоянное меню — чтобы клиент не терялся после длинной переписки."""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.REPLY_PRICE), KeyboardButton(text=t.REPLY_FAQ)],
            [KeyboardButton(text=t.REPLY_ORDER), KeyboardButton(text=t.REPLY_MANAGER)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


def cancel_only() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_CANCEL)]],
        resize_keyboard=True,
    )


def contact_request() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=t.BTN_SEND_PHONE, request_contact=True)],
            [KeyboardButton(text=t.BTN_CANCEL)],
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def comment_step() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=t.BTN_SKIP), KeyboardButton(text=t.BTN_CANCEL)]],
        resize_keyboard=True,
    )
