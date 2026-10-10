"""Сбор заявки (FSM): имя → заведение/город → позиции → контакт → комментарий → подтверждение."""
import re
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.config import Config
from bot.database import Database
from bot.keyboards import inline, reply
from bot.states import OrderForm
from bot.utils.filters import IsStaff
from bot.utils.helpers import label, normalize_contact, tg_link_from_user
from bot.utils.notify import notify_manager

router = Router(name="order")

# Текст шага: не команда и не кнопка постоянного меню
STEP_TEXT = F.text & ~F.text.startswith("/") & ~F.text.in_(
    {t.REPLY_PRICE, t.REPLY_FAQ, t.REPLY_ORDER, t.REPLY_MANAGER, t.BTN_CANCEL}
)


# ---------- вход в сценарий ----------
async def start_order(message: Message, state: FSMContext, package: str | None = None):
    await state.clear()
    await state.set_state(OrderForm.name)
    await state.update_data(package=package)
    prefix = t.ORDER_START_PKG.format(package=t.PACKAGES[package]["title"]) if package else ""
    await message.answer(prefix + t.ORDER_START, reply_markup=reply.cancel_only())


@router.callback_query(F.data == "nav:order")
async def cb_order(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    package = (await state.get_data()).get("package")  # сохраняем пакет при «Заполнить заново»
    await start_order(callback.message, state, package)


@router.callback_query(F.data.startswith("pkg:"))
async def cb_package(callback: CallbackQuery, state: FSMContext):
    key = callback.data.split(":", 1)[1]
    if key not in t.PACKAGES:
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await callback.answer()
    await start_order(callback.message, state, key)


@router.message(F.chat.type == "private", F.text == t.REPLY_ORDER)
@router.message(F.chat.type == "private", Command("order"))
async def msg_order(message: Message, state: FSMContext):
    await start_order(message, state)


@router.callback_query(F.data == "ord:cancel")
async def cb_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer(t.ORDER_CANCELLED, reply_markup=reply.main_reply())


# ---------- шаги ----------
@router.message(OrderForm.name, STEP_TEXT)
async def step_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if not 2 <= len(name) <= 50:
        return await message.answer(t.ORDER_ERR_NAME)
    await state.update_data(name=name)
    await state.set_state(OrderForm.venue)
    await message.answer(t.ORDER_VENUE)


@router.message(OrderForm.venue, STEP_TEXT)
async def step_venue(message: Message, state: FSMContext):
    venue = message.text.strip()
    if not 3 <= len(venue) <= 200:
        return await message.answer(t.ORDER_ERR_VENUE)
    await state.update_data(venue=venue)
    await state.set_state(OrderForm.positions)
    await message.answer(t.ORDER_POSITIONS, reply_markup=inline.order_positions())


async def _ask_contact(message: Message, state: FSMContext, positions: str):
    await state.update_data(positions=positions)
    await state.set_state(OrderForm.contact)
    await message.answer(t.ORDER_CONTACT, reply_markup=reply.contact_request())


@router.callback_query(OrderForm.positions, F.data.startswith("ord:pos:"))
async def step_positions_btn(callback: CallbackQuery, state: FSMContext):
    idx = int(callback.data.split(":")[2])
    positions = t.POSITIONS_OPTIONS[idx]
    await callback.answer()
    await callback.message.edit_text(f"{t.ORDER_POSITIONS}\n\n➡️ <b>{positions}</b>")
    await _ask_contact(callback.message, state, positions)


@router.message(OrderForm.positions, STEP_TEXT)
async def step_positions_text(message: Message, state: FSMContext):
    m = re.search(r"\d{1,4}", message.text)
    if not m:
        return await message.answer(t.ORDER_ERR_POSITIONS, reply_markup=inline.order_positions())
    await _ask_contact(message, state, m.group())


@router.message(OrderForm.contact, F.contact)
async def step_contact_shared(message: Message, state: FSMContext):
    phone = normalize_contact(message.contact.phone_number) or message.contact.phone_number
    await _ask_comment(message, state, phone)


@router.message(OrderForm.contact, F.text == t.BTN_CONTACT_TG)
async def step_contact_telegram(message: Message, state: FSMContext):
    user = message.from_user
    contact = f"Telegram @{user.username}" if user.username else "Telegram (ответить реплаем в боте)"
    await _ask_comment(message, state, contact)


@router.message(OrderForm.contact, STEP_TEXT)
async def step_contact_text(message: Message, state: FSMContext):
    contact = normalize_contact(message.text)
    if not contact:
        return await message.answer(t.ORDER_ERR_CONTACT)
    await _ask_comment(message, state, contact)


async def _ask_comment(message: Message, state: FSMContext, contact: str):
    await state.update_data(contact=contact)
    await state.set_state(OrderForm.comment)
    await message.answer(t.ORDER_COMMENT, reply_markup=reply.comment_step())


@router.message(OrderForm.comment, STEP_TEXT)
async def step_comment(message: Message, state: FSMContext):
    comment = None if message.text == t.BTN_SKIP else message.text.strip()[:1000]
    await state.update_data(comment=comment)
    await state.set_state(OrderForm.confirm)
    data = await state.get_data()
    await message.answer("👌", reply_markup=reply.main_reply())  # убираем клавиатуру шага
    await message.answer(t.ORDER_CONFIRM.format(
        name=escape(data["name"]),
        venue=escape(data["venue"]),
        positions=escape(data["positions"]),
        contact=escape(data["contact"]),
        package=t.PACKAGES.get(data.get("package") or "", {}).get("title", t.NO_PACKAGE),
        comment=escape(comment) if comment else t.NO_COMMENT,
    ), reply_markup=inline.order_confirm())


@router.message(OrderForm.confirm, STEP_TEXT)
async def step_confirm_text(message: Message):
    await message.answer(t.ORDER_CONFIRM_HINT)


@router.message(OrderForm.name, ~F.text)
@router.message(OrderForm.venue, ~F.text)
@router.message(OrderForm.positions, ~F.text)
@router.message(OrderForm.contact, ~F.text, ~F.contact)
@router.message(OrderForm.comment, ~F.text)
async def step_not_text(message: Message):
    await message.answer(t.ORDER_ERR_TEXT)


# ---------- подтверждение ----------
@router.callback_query(OrderForm.confirm, F.data == "ord:confirm")
async def step_confirm(callback: CallbackQuery, state: FSMContext, bot: Bot, config: Config, db: Database):
    data = await state.get_data()
    await state.clear()
    await callback.answer()
    await callback.message.edit_reply_markup(reply_markup=None)

    order_id = await db.create_order(callback.from_user.id, data)
    user = await db.get_user(callback.from_user.id) or {}

    await notify_manager(bot, config, t.MANAGER_NEW_ORDER.format(
        order_id=order_id,
        name=escape(data["name"]),
        venue=escape(data["venue"]),
        positions=escape(data["positions"]),
        contact=escape(data["contact"]),
        package=t.PACKAGES.get(data.get("package") or "", {}).get("title", t.NO_PACKAGE),
        comment=escape(data["comment"]) if data.get("comment") else t.NO_COMMENT,
        segment=label(t.SEGMENTS, user.get("segment")),
        menu=label(t.MENU_SIZES, user.get("menu_size")),
        ttk=label(t.TTK_STATUSES, user.get("ttk_status")),
        source=escape(user.get("source") or "direct"),
        tg_link=tg_link_from_user(callback.from_user),
        user_id=callback.from_user.id,
    ), inline.order_status(order_id))

    await callback.message.answer(t.ORDER_DONE.format(order_id=order_id), reply_markup=reply.main_reply())


@router.callback_query(F.data == "ord:confirm")
async def stale_confirm(callback: CallbackQuery):
    await callback.answer(t.UNKNOWN_CALLBACK, show_alert=True)


# ---------- смена статуса менеджером ----------
@router.callback_query(F.data.startswith("st:"), IsStaff())
async def cb_status(callback: CallbackQuery, db: Database):
    _, order_id, status = callback.data.split(":")
    if status not in t.ORDER_STATUSES or not await db.get_order(int(order_id)):
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await db.set_order_status(int(order_id), status)
    who = escape(callback.from_user.full_name)
    base = (callback.message.html_text or "").split("\n\nСтатус:")[0]
    await callback.message.edit_text(
        base + "\n\n" + t.STATUS_CHANGED.format(status=t.ORDER_STATUSES[status], who=who),
        reply_markup=inline.order_status(int(order_id)),
    )
    await callback.answer(t.ORDER_STATUSES[status])
