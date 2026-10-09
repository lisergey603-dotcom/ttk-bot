"""Точка входа: python main.py"""
import asyncio
import logging
import sys
from logging.handlers import RotatingFileHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import BaseStorage
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from bot import texts as t
from bot.config import BASE_DIR, Config, load_config
from bot.database import Database
from bot.handlers import get_routers
from bot.middlewares import AntiFloodMiddleware, OutgoingLogMiddleware, UserTrackingMiddleware


def setup_logging(level: str) -> None:
    log_dir = BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fmt = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    logging.basicConfig(
        level=level,
        format=fmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
            RotatingFileHandler(log_dir / "bot.log", maxBytes=5_000_000, backupCount=3, encoding="utf-8"),
        ],
    )
    logging.getLogger("aiogram.event").setLevel(logging.WARNING)


def make_storage(config: Config) -> BaseStorage:
    """Redis, если задан REDIS_URL (состояния переживают перезапуск), иначе — память."""
    if config.redis_url:
        from aiogram.fsm.storage.redis import RedisStorage
        logging.info("FSM: Redis (%s)", config.redis_url)
        return RedisStorage.from_url(config.redis_url)
    logging.info("FSM: MemoryStorage")
    return MemoryStorage()


def make_session(config: Config) -> AiohttpSession:
    """Соединение с Telegram. Если api.telegram.org недоступен с сервера —
    можно указать прокси (TELEGRAM_PROXY) или зеркало Bot API (TELEGRAM_API_URL)."""
    session = AiohttpSession(proxy=config.telegram_proxy) if config.telegram_proxy else AiohttpSession()
    if config.telegram_proxy:
        logging.info("Telegram: через прокси %s", config.telegram_proxy.split("@")[-1])
    if config.telegram_api_url:
        session.api = TelegramAPIServer.from_base(config.telegram_api_url)
        logging.info("Telegram: через сервер %s", config.telegram_api_url)
    return session


async def main() -> None:
    config = load_config()
    setup_logging(config.log_level)

    db = Database(config.db_path)
    await db.connect()

    bot = Bot(config.bot_token, session=make_session(config),
              default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    bot.session.middleware(OutgoingLogMiddleware(db))

    dp = Dispatcher(storage=make_storage(config))
    dp["db"] = db          # доступно в хендлерах как аргумент db
    dp["config"] = config  # и как config

    # Антифлуд: 5 сообщений / 10 сек. Для кнопок лимит мягче — квиз прокликивают быстро.
    staff = set(config.admin_ids) | {config.manager_chat_id}
    dp.message.outer_middleware(AntiFloodMiddleware(config.antiflood_limit, config.antiflood_period, staff))
    dp.callback_query.outer_middleware(AntiFloodMiddleware(config.callback_limit, config.antiflood_period, staff))
    # Затем учёт пользователя и лог входящих
    tracking = UserTrackingMiddleware()
    dp.message.outer_middleware(tracking)
    dp.callback_query.outer_middleware(tracking)

    dp.include_routers(*get_routers())

    logging.info("Подключаюсь к Telegram...")
    await bot.set_my_commands([BotCommand(command=c, description=d) for c, d in t.BOT_COMMANDS.items()])
    me = await bot.get_me()
    logging.info("Бот @%s запущен. Ссылка для лендинга: https://t.me/%s?start=ttk_landing", me.username, me.username)

    try:
        await bot.delete_webhook(drop_pending_updates=False)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await db.close()
        await dp.storage.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен")
    except RuntimeError as e:  # ошибки конфигурации — понятным текстом
        print(f"❌ {e}")
        sys.exit(1)
