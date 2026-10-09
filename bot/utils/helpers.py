"""Вспомогательные функции: ссылки, валидация, поиск по FAQ, CSV."""
import csv
import io
import re
from html import escape

from aiogram.types import User

from bot import texts as t

PHONE_RE = re.compile(r"^\+?[\d\s\-()]{10,20}$")
EMAIL_RE = re.compile(r"^[\w.+-]+@[\w-]+\.[\w.-]+$")
USER_ID_TAG_RE = re.compile(r"#id(\d+)")
START_PAYLOAD_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def tg_link(user_id: int, full_name: str | None, username: str | None = None) -> str:
    """Кликабельная ссылка на пользователя для менеджера."""
    name = escape(full_name or str(user_id))
    if username:
        return f'<a href="tg://user?id={user_id}">{name}</a> (@{username})'
    return f'<a href="tg://user?id={user_id}">{name}</a>'


def tg_link_from_user(user: User) -> str:
    return tg_link(user.id, user.full_name, user.username)


def normalize_contact(raw: str) -> str | None:
    """Возвращает телефон/email в аккуратном виде или None, если не похоже."""
    value = raw.strip()
    if EMAIL_RE.match(value):
        return value.lower()
    if PHONE_RE.match(value):
        digits = re.sub(r"\D", "", value)
        if 10 <= len(digits) <= 15:
            if len(digits) == 11 and digits[0] == "8":  # 8XXX → +7XXX
                digits = "7" + digits[1:]
            elif len(digits) == 10:  # без кода страны — считаем РФ
                digits = "7" + digits
            return "+" + digits
    return None


def parse_source(payload: str | None) -> str | None:
    """Метка из /start <payload>. Telegram допускает A-Z a-z 0-9 _ - до 64 символов."""
    if payload and START_PAYLOAD_RE.match(payload):
        return payload.lower()
    return None


def find_faq(text: str) -> str | None:
    """Ищет FAQ по ключевым словам. Возвращает ключ лучшего совпадения или None."""
    text = text.lower().replace("ё", "е")
    best_key, best_score = None, 0
    for key, item in t.FAQ.items():
        score = sum(1 for kw in item["kw"] if kw.replace("ё", "е") in text)
        if score > best_score:
            best_key, best_score = key, score
    return best_key


def extract_user_id(text: str | None) -> int | None:
    """Находит #id123 в сообщении бота (для ответов менеджера реплаем)."""
    if not text:
        return None
    m = USER_ID_TAG_RE.search(text)
    return int(m.group(1)) if m else None


def label(mapping: dict, key: str | None, default: str = "—") -> str:
    return mapping.get(key, default) if key else default


def orders_to_csv(rows: list[dict]) -> bytes:
    """CSV в UTF-8 с BOM и разделителем «;» — корректно открывается в русском Excel."""
    buf = io.StringIO()
    headers = {
        "id": "№", "created_at": "Дата (UTC)", "status": "Статус", "name": "Имя",
        "venue": "Заведение / город", "positions": "Позиций", "contact": "Контакт",
        "comment": "Комментарий", "package": "Пакет", "user_id": "Telegram ID",
        "username": "Username", "source": "Источник", "segment": "Тип заведения",
        "menu_size": "Размер меню", "ttk_status": "Наличие ТТК",
    }
    writer = csv.DictWriter(buf, fieldnames=list(headers), delimiter=";", extrasaction="ignore")
    writer.writerow(headers)
    for r in rows:
        r = dict(r)
        r["status"] = t.ORDER_STATUSES.get(r.get("status"), r.get("status"))
        r["package"] = t.PACKAGES.get(r.get("package"), {}).get("title", r.get("package") or "")
        r["segment"] = label(t.SEGMENTS, r.get("segment"), "")
        r["menu_size"] = label(t.MENU_SIZES, r.get("menu_size"), "")
        r["ttk_status"] = label(t.TTK_STATUSES, r.get("ttk_status"), "")
        writer.writerow(r)
    return buf.getvalue().encode("utf-8-sig")
