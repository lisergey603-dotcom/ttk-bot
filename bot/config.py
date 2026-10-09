"""Загрузка настроек из .env."""
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _parse_ids(raw: str) -> list[int]:
    """'123, 456' -> [123, 456]"""
    return [int(x) for x in raw.replace(" ", "").split(",") if x.strip().lstrip("-").isdigit()]


@dataclass(frozen=True)
class Config:
    bot_token: str
    admin_ids: list[int]
    manager_chat_id: int
    db_path: Path
    redis_url: str | None
    log_level: str
    antiflood_limit: int = 5            # сообщений
    antiflood_period: float = 10.0      # за N секунд
    callback_limit: int = 12            # нажатий кнопок за тот же период
    assets_dir: Path = field(default=BASE_DIR / "bot" / "assets")


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token or token.startswith("123456:"):
        raise RuntimeError("Укажите BOT_TOKEN в файле .env (см. .env.example)")

    admin_ids = _parse_ids(os.getenv("ADMIN_ID", ""))
    if not admin_ids:
        raise RuntimeError("Укажите ADMIN_ID в .env (можно несколько через запятую)")

    # Если чат менеджеров не задан — заявки уходят первому админу
    manager_raw = os.getenv("MANAGER_CHAT_ID", "").strip()
    manager_chat_id = int(manager_raw) if manager_raw.lstrip("-").isdigit() else admin_ids[0]

    db_path = Path(os.getenv("DB_PATH", BASE_DIR / "data" / "bot.db"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        manager_chat_id=manager_chat_id,
        db_path=db_path,
        redis_url=os.getenv("REDIS_URL", "").strip() or None,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        antiflood_limit=int(os.getenv("ANTIFLOOD_LIMIT", 5)),
        antiflood_period=float(os.getenv("ANTIFLOOD_PERIOD", 10)),
        callback_limit=int(os.getenv("CALLBACK_LIMIT", 12)),
    )
