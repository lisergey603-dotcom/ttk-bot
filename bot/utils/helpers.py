"""Вспомогательные функции: ссылки, валидация, поиск по FAQ, CSV."""
import csv
import io
import re
from datetime import date, timedelta
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
        "amount": "Сумма, ₽", "deadline": "Срок сдачи", "note": "Заметка",
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


# ---------- CRM: сумма, оплата, срок ----------
DEADLINE_RE = re.compile(r"^\s*(\d{1,2})[./\-](\d{1,2})(?:[./\-](\d{2}|\d{4}))?\s*$")
CLOSED_STATUSES = {"done", "rejected"}


def fmt_rub(value: int | None) -> str:
    if value is None:
        return t.ADM_NOT_SET
    return f"{value:,}".replace(",", "\u00a0") + "\u00a0₽"


def parse_amount(raw: str) -> int | None:
    digits = re.sub(r"\D", "", raw.split(",")[0].split(".")[0])
    if not digits:
        return None
    value = int(digits)
    return value if 0 < value <= 100_000_000 else None


def parse_deadline(raw: str, today: date | None = None) -> str | None:
    """«17.10», «17.10.2026», «17.10.26» → '2026-10-17'. Без года — ближайшая такая дата."""
    m = DEADLINE_RE.match(raw)
    if not m:
        return None
    today = today or date.today()
    day, month, year = int(m[1]), int(m[2]), m[3]
    try:
        if year:
            y = int(year)
            return date(y + 2000 if y < 100 else y, month, day).isoformat()
        d = date(today.year, month, day)
        if d < today - timedelta(days=30):  # давно прошедшая дата — значит, следующий год
            d = date(today.year + 1, month, day)
        return d.isoformat()
    except ValueError:
        return None


def fmt_deadline(iso: str | None, status: str | None = None, today: date | None = None) -> str:
    if not iso:
        return t.ADM_NOT_SET
    try:
        d = date.fromisoformat(iso)
    except ValueError:
        return escape(iso)
    text = d.strftime("%d.%m.%Y")
    if status not in CLOSED_STATUSES and d < (today or date.today()):
        text += t.ADM_OVERDUE
    return text


def paid_amount(order: dict) -> int:
    """Сколько уже получено по заявке: правило 50/50 — предоплата половина, «Оплачено» — всё."""
    amount = order.get("amount") or 0
    if order.get("status") == "done":
        return amount
    if order.get("status") == "prepaid":
        return amount // 2
    return 0


def order_card(o: dict) -> str:
    amount = o.get("amount")
    paid = paid_amount(o)
    if amount and o.get("status") == "done":
        paid_text = t.ADM_PAID_FULL.format(paid=fmt_rub(paid))
    elif amount and o.get("status") == "prepaid":
        paid_text = t.ADM_PAID_HALF.format(paid=fmt_rub(paid))
    else:
        paid_text = fmt_rub(0) if amount else t.ADM_NOT_SET
    return t.ADM_CARD.format(
        id=o["id"],
        status=t.ORDER_STATUSES.get(o["status"], o["status"]),
        created_at=(o.get("created_at") or "")[:16],
        source=escape(o.get("source") or "direct"),
        name=escape(o["name"]),
        venue=escape(o["venue"]),
        positions=escape(o["positions"]),
        contact=escape(o["contact"]),
        package=t.PACKAGES.get(o.get("package") or "", {}).get("title", t.NO_PACKAGE),
        comment=escape(o["comment"]) if o.get("comment") else t.NO_COMMENT,
        amount=fmt_rub(amount),
        paid=paid_text,
        deadline=fmt_deadline(o.get("deadline"), o.get("status")),
        note=escape(o["note"]) if o.get("note") else t.ADM_NOT_SET,
    )


def money_summary(totals: dict[str, dict]) -> str:
    """Блок «Деньги» для статистики. totals — результат db.get_status_totals()."""
    def total(status: str) -> int:
        return (totals.get(status) or {}).get("total") or 0

    received = total("done") + total("prepaid") // 2
    expected = (total("prepaid") - total("prepaid") // 2) + total("in_work")
    rows = []
    for key, name in t.ORDER_STATUSES.items():
        r = totals.get(key)
        if not r:
            continue
        extra = t.ADM_MONEY_STATUS_TOTAL.format(total=fmt_rub(r["total"])) if r["total"] else ""
        rows.append(t.ADM_MONEY_STATUS_ROW.format(status=name, n=r["n"], total=extra))
    text = t.ADM_MONEY.format(
        received=fmt_rub(received), expected=fmt_rub(expected), statuses="\n".join(rows) or "—",
    )
    no_amount = sum((totals.get(k) or {}).get("no_amount") or 0 for k in ("in_work", "prepaid", "done"))
    if no_amount:
        text += t.ADM_MONEY_NO_AMOUNT.format(n=no_amount)
    return text
