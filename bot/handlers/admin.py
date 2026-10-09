"""Админ-панель: заявки, статистика, рассылка, экспорт CSV. Доступ только ADMIN_ID."""
import asyncio
import logging
import math
from datetime import datetime
from html import escape

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError, TelegramRetryAfter
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import BufferedInputFile, CallbackQuery, Message

from bot import texts as t
from bot.database import Database
from bot.keyboards import inline
from bot.states import Broadcast
from bot.utils.filters import IsAdmin
from bot.utils.helpers import orders_to_csv
from bot.utils.render import render

logger = logging.getLogger(__name__)
router = Router(name="admin")
router.message.filter(IsAdmin(), F.chat.type == "private")
router.callback_query.filter(IsAdmin())

PAGE_SIZE = 5
_tasks: set[asyncio.Task] = set()  # держим ссылки на фоновые рассылки


@router.message(Command("admin"))
@router.callback_query(F.data == "adm:menu")
async def admin_menu(event: Message | CallbackQuery, state: FSMContext):
    await state.clear()
    await render(event, t.ADMIN_MENU, inline.admin_menu())


# ---------- заявки ----------
@router.message(Command("orders"))
@router.callback_query(F.data.startswith("adm:orders:"))
async def admin_orders(event: Message | CallbackQuery, db: Database):
    page = int(event.data.split(":")[2]) if isinstance(event, CallbackQuery) else 1
    total = await db.count_orders()
    if not total:
        return await render(event, t.ADM_NO_ORDERS, inline.admin_back())
    pages = max(1, math.ceil(total / PAGE_SIZE))
    page = min(max(page, 1), pages)
    rows = await db.get_orders(PAGE_SIZE, (page - 1) * PAGE_SIZE)

    text = t.ADM_ORDERS_HEADER.format(page=page, pages=pages, total=total)
    for o in rows:
        text += t.ADM_ORDER_ROW.format(
            id=o["id"],
            status=t.ORDER_STATUSES.get(o["status"], o["status"]),
            created_at=o["created_at"][:16],
            name=escape(o["name"]),
            venue=escape(o["venue"]),
            positions=escape(o["positions"]),
            contact=escape(o["contact"]),
            package=t.PACKAGES.get(o["package"] or "", {}).get("title", t.NO_PACKAGE),
        ) + "\n"
    await render(event, text, inline.admin_pages(page, pages))


# ---------- статистика ----------
def _pct(part: int, whole: int) -> str:
    return f"{part / whole * 100:.1f}" if whole else "0"


@router.message(Command("stats"))
@router.callback_query(F.data == "adm:stats")
async def admin_stats(event: Message | CallbackQuery, db: Database):
    s = await db.get_stats()
    sources = "\n".join(
        t.ADM_STATS_SOURCE_ROW.format(
            source=escape(r["source"] or "direct"),
            started=r["started"], price=r["price"] or 0, ordered=r["ordered"] or 0,
        ) for r in s["by_source"]
    ) or "—"
    text = t.ADM_STATS.format(
        **{k: v for k, v in s.items() if k != "by_source"},
        price_cr=_pct(s["price"], s["started"]),
        order_cr=_pct(s["ordered_users"], s["started"]),
        sources=sources,
    )
    await render(event, text, inline.admin_back())


# ---------- экспорт ----------
@router.message(Command("export"))
@router.callback_query(F.data == "adm:export")
async def admin_export(event: Message | CallbackQuery, db: Database, bot: Bot):
    if isinstance(event, CallbackQuery):
        await event.answer()
    chat_id = event.from_user.id
    rows = await db.get_all_orders()
    if not rows:
        return await bot.send_message(chat_id, t.ADM_EXPORT_EMPTY)
    filename = f"orders_{datetime.now():%Y-%m-%d_%H-%M}.csv"
    await bot.send_document(
        chat_id,
        BufferedInputFile(orders_to_csv(rows), filename=filename),
        caption=t.ADM_EXPORT_CAPTION.format(count=len(rows)),
    )


# ---------- рассылка ----------
@router.callback_query(F.data == "adm:broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext, db: Database):
    if any(not task.done() for task in _tasks):
        return await callback.answer(t.ADM_BROADCAST_BUSY, show_alert=True)
    count = len(await db.get_active_user_ids())
    await state.set_state(Broadcast.waiting_content)
    await render(callback, t.ADM_BROADCAST_ASK.format(count=count), edit=False)


@router.message(Broadcast.waiting_content, Command("cancel"))
@router.message(Broadcast.confirm, Command("cancel"))
async def broadcast_cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.ADM_BROADCAST_CANCELLED)


@router.message(Broadcast.waiting_content)
async def broadcast_content(message: Message, state: FSMContext, bot: Bot, db: Database):
    await state.update_data(from_chat=message.chat.id, msg_id=message.message_id)
    await state.set_state(Broadcast.confirm)
    count = len(await db.get_active_user_ids())
    await bot.copy_message(message.chat.id, message.chat.id, message.message_id)  # превью
    await message.answer(t.ADM_BROADCAST_PREVIEW.format(count=count), reply_markup=inline.broadcast_confirm())


@router.callback_query(Broadcast.confirm, F.data == "bc:cancel")
@router.callback_query(F.data == "bc:cancel")
async def broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await render(callback, t.ADM_BROADCAST_CANCELLED)


@router.callback_query(Broadcast.confirm, F.data == "bc:send")
async def broadcast_send(callback: CallbackQuery, state: FSMContext, bot: Bot, db: Database):
    data = await state.get_data()
    await state.clear()
    await render(callback, t.ADM_BROADCAST_STARTED)
    task = asyncio.create_task(
        run_broadcast(bot, db, data["from_chat"], data["msg_id"], callback.from_user.id)
    )
    _tasks.add(task)
    task.add_done_callback(_tasks.discard)


async def run_broadcast(bot: Bot, db: Database, from_chat: int, msg_id: int, report_to: int) -> None:
    """Копирует сообщение всем активным пользователям (~20 сообщений/сек — в пределах лимитов Telegram)."""
    ok = blocked = failed = 0
    for user_id in await db.get_active_user_ids():
        for attempt in range(2):
            try:
                await bot.copy_message(user_id, from_chat, msg_id)
                ok += 1
                break
            except TelegramRetryAfter as e:
                await asyncio.sleep(e.retry_after + 1)
            except TelegramForbiddenError:
                await db.mark_blocked(user_id)
                blocked += 1
                break
            except TelegramBadRequest as e:
                logger.warning("Рассылка: %s → %s", user_id, e)
                failed += 1
                break
        else:
            failed += 1
        await asyncio.sleep(0.05)
    logger.info("Рассылка завершена: ok=%s blocked=%s failed=%s", ok, blocked, failed)
    await bot.send_message(report_to, t.ADM_BROADCAST_DONE.format(ok=ok, blocked=blocked, failed=failed))
