"""FAQ: список вопросов, ответы, свободный вопрос → менеджеру."""
from html import escape

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.config import Config
from bot.database import Database
from bot.keyboards import inline, reply
from bot.states import AskQuestion
from bot.utils.helpers import find_faq, tg_link_from_user
from bot.utils.notify import notify_manager
from bot.utils.render import render

router = Router(name="faq")


@router.callback_query(F.data == "nav:faq")
async def cb_faq(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await render(callback, t.FAQ_INTRO, inline.faq_list())


@router.message(F.chat.type == "private", F.text == t.REPLY_FAQ)
@router.message(F.chat.type == "private", Command("faq"))
async def msg_faq(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.FAQ_INTRO, reply_markup=inline.faq_list())


@router.callback_query(F.data.startswith("faq:"))
async def cb_faq_item(callback: CallbackQuery):
    key = callback.data.split(":", 1)[1]
    item = t.FAQ.get(key)
    if not item:
        return await callback.answer(t.UNKNOWN_CALLBACK)
    await render(callback, item["a"], inline.faq_answer())


# ---------- вопрос менеджеру ----------
@router.callback_query(F.data == "nav:ask")
async def cb_ask(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AskQuestion.waiting)
    await callback.answer()
    await callback.message.answer(t.FAQ_ASK_PROMPT, reply_markup=reply.cancel_only())


@router.message(F.chat.type == "private", F.text == t.REPLY_MANAGER)
async def msg_manager(message: Message, state: FSMContext):
    await state.set_state(AskQuestion.waiting)
    await message.answer(t.CONTACT_MANAGER, reply_markup=reply.cancel_only())


async def forward_question(message: Message, bot: Bot, config: Config, db: Database) -> None:
    user = await db.get_user(message.from_user.id) or {}
    await notify_manager(bot, config, t.MANAGER_QUESTION.format(
        text=escape(message.text),
        tg_link=tg_link_from_user(message.from_user),
        source=escape(user.get("source") or "direct"),
        user_id=message.from_user.id,
    ))


@router.message(AskQuestion.waiting, F.text, ~F.text.startswith("/"))
async def ask_received(message: Message, state: FSMContext, bot: Bot, config: Config, db: Database):
    """Клиент сам выбрал «Задать вопрос» — всегда передаём человеку,
    а если нашли похожий ответ в FAQ — показываем его, пока ждёт."""
    await state.clear()
    await forward_question(message, bot, config, db)
    key = find_faq(message.text)
    if key:
        await message.answer(t.FAQ_HINT_PREFIX + t.FAQ[key]["a"], reply_markup=reply.main_reply())
        await message.answer("👇", reply_markup=inline.faq_answer())
    else:
        await message.answer(t.QUESTION_SENT, reply_markup=reply.main_reply())


async def handle_free_text(message: Message, bot: Bot, config: Config, db: Database) -> None:
    """Свободный текст вне сценариев: сначала ищем в FAQ, иначе — менеджеру."""
    if message.text.lower().strip(" !.,)") in t.GREETINGS:
        return await message.answer(t.GREETING_REPLY, reply_markup=inline.main_menu())
    key = find_faq(message.text)
    if key:
        await message.answer(t.FAQ_FOUND_PREFIX + t.FAQ[key]["a"],
                             reply_markup=inline.faq_answer(ask_manager=True))
    else:
        await forward_question(message, bot, config, db)
        await message.answer(t.FAQ_NOT_FOUND, reply_markup=inline.faq_answer())
