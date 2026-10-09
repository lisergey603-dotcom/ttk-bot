"""Работа с SQLite через aiosqlite. Одно соединение на всё приложение."""
import logging
from pathlib import Path
from typing import Any

import aiosqlite

logger = logging.getLogger(__name__)
SCHEMA_PATH = Path(__file__).with_name("schema.sql")


class Database:
    def __init__(self, path: Path):
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    # ---------- жизненный цикл ----------
    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA journal_mode=WAL")
        await self.conn.execute("PRAGMA foreign_keys=ON")
        await self.conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        await self.conn.commit()
        logger.info("БД подключена: %s", self.path)

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def _exec(self, sql: str, params: tuple = ()) -> aiosqlite.Cursor:
        cur = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cur

    async def _fetchall(self, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
        async with self.conn.execute(sql, params) as cur:
            return [dict(r) for r in await cur.fetchall()]

    async def _fetchone(self, sql: str, params: tuple = ()) -> dict[str, Any] | None:
        async with self.conn.execute(sql, params) as cur:
            row = await cur.fetchone()
            return dict(row) if row else None

    # ---------- пользователи ----------
    async def upsert_user(self, user_id: int, username: str | None, full_name: str) -> None:
        """Создаёт пользователя или обновляет last_seen. Снимает флаг блокировки."""
        await self._exec(
            """INSERT INTO users (id, username, full_name) VALUES (?, ?, ?)
               ON CONFLICT(id) DO UPDATE SET username=excluded.username,
                   full_name=excluded.full_name, last_seen=datetime('now'), is_blocked=0""",
            (user_id, username, full_name),
        )

    async def set_source(self, user_id: int, source: str) -> None:
        """Источник пишем только при первом заходе — чтобы не терять атрибуцию."""
        await self._exec(
            "UPDATE users SET source=? WHERE id=? AND (source IS NULL OR source='direct')",
            (source, user_id),
        )

    async def set_user_field(self, user_id: int, field: str, value: Any) -> None:
        if field not in {"segment", "menu_size", "ttk_status"}:
            raise ValueError(field)
        await self._exec(f"UPDATE users SET {field}=? WHERE id=?", (value, user_id))

    async def mark_reached_price(self, user_id: int) -> None:
        await self._exec("UPDATE users SET reached_price=1 WHERE id=?", (user_id,))

    async def mark_blocked(self, user_id: int) -> None:
        await self._exec("UPDATE users SET is_blocked=1 WHERE id=?", (user_id,))

    async def get_user(self, user_id: int) -> dict | None:
        return await self._fetchone("SELECT * FROM users WHERE id=?", (user_id,))

    async def get_active_user_ids(self) -> list[int]:
        rows = await self._fetchall("SELECT id FROM users WHERE is_blocked=0")
        return [r["id"] for r in rows]

    # ---------- заявки ----------
    async def create_order(self, user_id: int, data: dict) -> int:
        cur = await self._exec(
            """INSERT INTO orders (user_id, name, venue, positions, contact, comment, package)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, data["name"], data["venue"], data["positions"],
             data["contact"], data.get("comment"), data.get("package")),
        )
        return cur.lastrowid

    async def set_order_status(self, order_id: int, status: str) -> None:
        await self._exec("UPDATE orders SET status=? WHERE id=?", (status, order_id))

    async def get_order(self, order_id: int) -> dict | None:
        return await self._fetchone("SELECT * FROM orders WHERE id=?", (order_id,))

    async def get_orders(self, limit: int = 10, offset: int = 0) -> list[dict]:
        return await self._fetchall(
            """SELECT o.*, u.username, u.source FROM orders o
               LEFT JOIN users u ON u.id = o.user_id
               ORDER BY o.id DESC LIMIT ? OFFSET ?""",
            (limit, offset),
        )

    async def count_orders(self) -> int:
        row = await self._fetchone("SELECT COUNT(*) AS c FROM orders")
        return row["c"]

    async def get_all_orders(self) -> list[dict]:
        return await self._fetchall(
            """SELECT o.id, o.created_at, o.status, o.name, o.venue, o.positions, o.contact,
                      o.comment, o.package, o.user_id, u.username, u.source, u.segment,
                      u.menu_size, u.ttk_status
               FROM orders o LEFT JOIN users u ON u.id = o.user_id ORDER BY o.id"""
        )

    # ---------- статистика ----------
    async def get_stats(self) -> dict:
        total = await self._fetchone(
            """SELECT COUNT(*) AS started,
                      SUM(reached_price) AS price,
                      SUM(is_blocked) AS blocked,
                      SUM(CASE WHEN created_at >= datetime('now','-1 day') THEN 1 ELSE 0 END) AS today
               FROM users"""
        )
        ordered = await self._fetchone("SELECT COUNT(DISTINCT user_id) AS c, COUNT(*) AS n FROM orders")
        by_source = await self._fetchall(
            """SELECT u.source,
                      COUNT(*) AS started,
                      SUM(u.reached_price) AS price,
                      (SELECT COUNT(DISTINCT o.user_id) FROM orders o
                         JOIN users u2 ON u2.id=o.user_id WHERE u2.source=u.source) AS ordered
               FROM users u GROUP BY u.source ORDER BY started DESC"""
        )
        return {
            "started": total["started"] or 0,
            "price": total["price"] or 0,
            "blocked": total["blocked"] or 0,
            "today": total["today"] or 0,
            "ordered_users": ordered["c"] or 0,
            "orders": ordered["n"] or 0,
            "by_source": by_source,
        }

    # ---------- лог сообщений ----------
    async def log_message(self, user_id: int, direction: str, text: str | None) -> None:
        await self._exec(
            "INSERT INTO messages_log (user_id, direction, text) VALUES (?, ?, ?)",
            (user_id, direction, (text or "")[:4000]),
        )
