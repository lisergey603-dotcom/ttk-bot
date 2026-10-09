"""Порядок роутеров важен: сначала админка и старт, в конце — «всё остальное»."""
from aiogram import Router

from . import admin, common, errors, faq, funnel, order, start


def get_routers() -> list[Router]:
    return [
        errors.router,
        admin.router,
        start.router,
        order.router,
        funnel.router,
        faq.router,
        common.router,  # последним: ответы менеджера и свободный текст
    ]
