"""Inline-клавиатуры. callback_data — короткие строки с префиксами:
nav:* — навигация, q:* — квиз, faq:* — вопросы, pkg:* — выбор пакета,
ord:* — шаги заявки, st:* — статус заявки (для менеджера), adm:* / bc:* — админка.
"""
from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot import texts as t


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_START_QUIZ, callback_data="nav:quiz")
    kb.button(text=t.BTN_PRICE, callback_data="nav:price")
    kb.button(text=t.BTN_EXAMPLE, callback_data="nav:example")
    kb.button(text=t.BTN_CASES, callback_data="nav:cases")
    kb.button(text=t.BTN_FAQ, callback_data="nav:faq")
    kb.button(text=t.BTN_ORDER, callback_data="nav:order")
    kb.adjust(1, 2, 2, 1)
    return kb.as_markup()


def cta(show_price: bool = True, show_example: bool = True) -> InlineKeyboardMarkup:
    """Основные кнопки призыва к действию под оффером/примером/кейсами."""
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_ORDER, callback_data="nav:order")
    kb.button(text=t.BTN_ASK, callback_data="nav:ask")
    if show_example:
        kb.button(text=t.BTN_EXAMPLE, callback_data="nav:example")
    if show_price:
        kb.button(text=t.BTN_PRICE, callback_data="nav:price")
    kb.button(text=t.BTN_MENU, callback_data="nav:menu")
    if show_price and show_example:
        kb.adjust(1, 1, 2, 1)
    else:
        kb.adjust(1, 1, 1, 1)
    return kb.as_markup()


def _options(prefix: str, options: dict[str, str], cols: int = 2) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, label in options.items():
        kb.button(text=label, callback_data=f"{prefix}:{key}")
    kb.adjust(cols)
    return kb.as_markup()


def quiz_segment() -> InlineKeyboardMarkup:
    return _options("q:seg", t.SEGMENTS, 2)


def quiz_menu() -> InlineKeyboardMarkup:
    return _options("q:menu", t.MENU_SIZES, 4)


def quiz_ttk() -> InlineKeyboardMarkup:
    return _options("q:ttk", t.TTK_STATUSES, 1)


def price() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, pkg in t.PACKAGES.items():
        kb.button(text=t.BTN_PACKAGE.format(title=pkg["title"]), callback_data=f"pkg:{key}")
    kb.button(text=t.BTN_EXAMPLE, callback_data="nav:example")
    kb.button(text=t.BTN_ASK, callback_data="nav:ask")
    kb.button(text=t.BTN_MENU, callback_data="nav:menu")
    kb.adjust(1, 1, 1, 2, 1)
    return kb.as_markup()


def faq_list() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for key, item in t.FAQ.items():
        kb.button(text=item["q"], callback_data=f"faq:{key}")
    kb.button(text=t.BTN_ASK, callback_data="nav:ask")
    kb.button(text=t.BTN_MENU, callback_data="nav:menu")
    kb.adjust(1)
    return kb.as_markup()


def faq_answer(ask_manager: bool = False) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if ask_manager:  # ответ подобран автоматически — даём выход на живого человека
        kb.button(text=t.BTN_ASK_MANAGER, callback_data="nav:ask")
    kb.button(text=t.BTN_ASK_OTHER, callback_data="nav:faq")
    kb.button(text=t.BTN_ORDER, callback_data="nav:order")
    kb.button(text=t.BTN_PRICE, callback_data="nav:price")
    kb.adjust(*( [1, 1, 2] if ask_manager else [1, 2] ))
    return kb.as_markup()


def order_positions() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for i, label in enumerate(t.POSITIONS_OPTIONS):
        kb.button(text=label, callback_data=f"ord:pos:{i}")
    kb.button(text=t.BTN_CANCEL, callback_data="ord:cancel")
    kb.adjust(4, 1)
    return kb.as_markup()


def order_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_CONFIRM, callback_data="ord:confirm")
    kb.button(text=t.BTN_RESTART_ORDER, callback_data="nav:order")
    kb.button(text=t.BTN_CANCEL, callback_data="ord:cancel")
    kb.adjust(1, 2)
    return kb.as_markup()


def order_status(order_id: int) -> InlineKeyboardMarkup:
    """Кнопки смены статуса под уведомлением менеджеру."""
    kb = InlineKeyboardBuilder()
    for key, label in t.ORDER_STATUSES.items():
        if key != "new":
            kb.button(text=label, callback_data=f"st:{order_id}:{key}")
    kb.adjust(3)
    return kb.as_markup()


# ---------- админка ----------
def admin_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.ADM_BTN_ORDERS, callback_data="adm:orders:1")
    kb.button(text=t.ADM_BTN_STATS, callback_data="adm:stats")
    kb.button(text=t.ADM_BTN_BROADCAST, callback_data="adm:broadcast")
    kb.button(text=t.ADM_BTN_EXPORT, callback_data="adm:export")
    kb.adjust(2)
    return kb.as_markup()


def admin_pages(page: int, pages: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if page > 1:
        kb.button(text="⬅️", callback_data=f"adm:orders:{page - 1}")
    if page < pages:
        kb.button(text="➡️", callback_data=f"adm:orders:{page + 1}")
    kb.button(text=t.ADM_BTN_EXPORT, callback_data="adm:export")
    kb.button(text=t.BTN_BACK, callback_data="adm:menu")
    kb.adjust(2, 2)
    return kb.as_markup()


def admin_back() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.BTN_BACK, callback_data="adm:menu")
    return kb.as_markup()


def broadcast_confirm() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=t.ADM_BTN_SEND, callback_data="bc:send")
    kb.button(text=t.ADM_BTN_CANCEL, callback_data="bc:cancel")
    kb.adjust(2)
    return kb.as_markup()
