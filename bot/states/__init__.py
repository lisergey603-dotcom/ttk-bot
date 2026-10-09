"""Состояния FSM."""
from aiogram.fsm.state import State, StatesGroup


class OrderForm(StatesGroup):
    name = State()
    venue = State()
    positions = State()
    contact = State()
    comment = State()
    confirm = State()


class AskQuestion(StatesGroup):
    waiting = State()


class Broadcast(StatesGroup):
    waiting_content = State()
    confirm = State()
