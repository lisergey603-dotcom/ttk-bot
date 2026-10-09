"""Воронка: квиз из 3 вопросов → персональный оффер → пример/кейсы → прайс."""
import logging

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.config import Config
from bot.database import Database
from bot.keyboards import inline
from bot.utils.media import send_cached
from bot.utils.render import render

logger = logging.getLogger(__name__)
router = Router(name="funnel")

# ---------- квиз ----------
@router.callback_query(F.data == "nav:quiz")
async def quiz_start(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await render(callback, t.Q_SEGMENT, inline.quiz_segment())


@router.callback_query(F.data.startswith("q:seg:"))
async def quiz_segment(callback: CallbackQuery, db: Database):
    key = callback.data.split(":")[2]
    if key not in t.SEGMENTS:
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await db.set_user_field(callback.from_user.id, "segment", key)
    await render(callback, t.Q_MENU, inline.quiz_menu())


@router.callback_query(F.data.startswith("q:menu:"))
async def quiz_menu(callback: CallbackQuery, db: Database):
    key = callback.data.split(":")[2]
    if key not in t.MENU_SIZES:
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await db.set_user_field(callback.from_user.id, "menu_size", key)
    await render(callback, t.Q_TTK, inline.quiz_ttk())


@router.callback_query(F.data.startswith("q:ttk:"))
async def quiz_ttk(callback: CallbackQuery, db: Database):
    key = callback.data.split(":")[2]
    if key not in t.TTK_STATUSES:
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await db.set_user_field(callback.from_user.id, "ttk_status", key)
    user = await db.get_user(callback.from_user.id)
    await render(callback, build_offer(user), inline.cta())


def build_offer(user: dict) -> str:
    """Собирает персональный оффер по ответам квиза."""
    segment = user.get("segment") or "other"
    menu = user.get("menu_size") or "lt20"
    ttk = user.get("ttk_status") or "none"
    pkg = t.PACKAGES[t.RECOMMEND_BY_MENU.get(menu, "standard")]
    return t.OFFER.format(
        segment=t.SEGMENTS[segment],
        menu=t.MENU_SIZES[menu],
        ttk=t.TTK_STATUSES[ttk].lower(),
        segment_pitch=t.SEGMENT_PITCH[segment],
        ttk_pitch=t.TTK_PITCH[ttk],
        package=pkg["title"],
        package_price=pkg["price"],
    )


# ---------- прайс ----------
async def show_price(event: Message | CallbackQuery, db: Database):
    await db.mark_reached_price(event.from_user.id)
    await render(event, t.PRICE, inline.price(), edit=False)


@router.callback_query(F.data == "nav:price")
async def cb_price(callback: CallbackQuery, db: Database):
    await show_price(callback, db)


@router.message(F.chat.type == "private", F.text == t.REPLY_PRICE)
@router.message(F.chat.type == "private", Command("price"))
async def msg_price(message: Message, db: Database, state: FSMContext):
    await state.clear()
    await show_price(message, db)


# ---------- пример ТТК и кейсы ----------
@router.callback_query(F.data == "nav:example")
async def cb_example(callback: CallbackQuery, bot: Bot, config: Config):
    await callback.answer()
    chat_id = callback.message.chat.id
    preview = config.assets_dir / "example_ttk_preview.png"
    pdf = config.assets_dir / "example_ttk.pdf"
    try:
        if preview.exists():
            await send_cached(bot, chat_id, preview, "photo", caption=t.EXAMPLE_CAPTION)
        if pdf.exists():
            caption = t.EXAMPLE_FILE_CAPTION if preview.exists() else t.EXAMPLE_CAPTION
            await send_cached(bot, chat_id, pdf, "document", caption=caption,
                             reply_markup=inline.cta(show_example=False))
            return
    except Exception as e:
        logger.exception("Не удалось отправить пример ТТК: %s", e)
    await bot.send_message(chat_id, t.EXAMPLE_MISSING, reply_markup=inline.cta(show_example=False))


@router.callback_query(F.data == "nav:cases")
async def cb_cases(callback: CallbackQuery):
    await render(callback, t.CASES, inline.cta())
