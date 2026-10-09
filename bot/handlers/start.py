"""Старт: приветствие по UTM-метке, главное меню, общий /cancel."""
from html import escape

from aiogram import F, Router
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from bot import texts as t
from bot.database import Database
from bot.keyboards import inline, reply
from bot.utils.helpers import parse_source
from bot.utils.render import render

router = Router(name="start")
router.message.filter(F.chat.type == "private")


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, state: FSMContext, db: Database):
    await state.clear()
    source = parse_source(command.args)
    if source:
        await db.set_source(message.from_user.id, source)

    # Текст выбираем по метке; неизвестная метка → общий текст
    template = t.WELCOME.get(source or "", t.WELCOME["default"])
    name = message.from_user.first_name or "друг"
    await message.answer(template.format(name=escape(name)), reply_markup=reply.main_reply())
    await message.answer(t.MAIN_MENU, reply_markup=inline.main_menu())


@router.message(Command("menu"))
async def cmd_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t.MAIN_MENU, reply_markup=inline.main_menu())


@router.callback_query(F.data == "nav:menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await render(callback, t.MAIN_MENU, inline.main_menu())


@router.message(Command("cancel"))
@router.message(F.text == t.BTN_CANCEL)
async def cmd_cancel(message: Message, state: FSMContext):
    """Общая отмена для любого сценария (заявка, вопрос, рассылка)."""
    current = await state.get_state()
    await state.clear()
    text = t.ORDER_CANCELLED if current and current.startswith("OrderForm") else t.ADM_CANCELLED
    await message.answer(text, reply_markup=reply.main_reply())
