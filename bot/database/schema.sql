-- Схема БД бота (SQLite)

-- Пользователи и результаты квалификации
CREATE TABLE IF NOT EXISTS users (
    id              INTEGER PRIMARY KEY,           -- Telegram user_id
    username        TEXT,
    full_name       TEXT,
    source          TEXT    DEFAULT 'direct',      -- метка из /start (ttk_landing, vk, ...)
    segment         TEXT,                          -- тип заведения: cafe/restaurant/canteen/production/other
    menu_size       TEXT,                          -- lt20 / 20_50 / 50_100 / gt100
    ttk_status      TEXT,                          -- none / old / update
    reached_price   INTEGER NOT NULL DEFAULT 0,    -- 1 = видел прайс
    is_blocked      INTEGER NOT NULL DEFAULT 0,    -- 1 = заблокировал бота (выясняется при рассылке)
    pd_consent_at   TEXT,                          -- согласие на обработку ПД (UTC), NULL = не давал
    created_at      TEXT    NOT NULL DEFAULT (datetime('now')),
    last_seen       TEXT    NOT NULL DEFAULT (datetime('now'))
);

-- Заявки
CREATE TABLE IF NOT EXISTS orders (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL REFERENCES users(id),
    name        TEXT    NOT NULL,
    venue       TEXT    NOT NULL,                  -- название заведения / город
    positions   TEXT    NOT NULL,                  -- кол-во позиций
    contact     TEXT    NOT NULL,                  -- телефон или email
    comment     TEXT,
    package     TEXT,                              -- выбранный пакет (если выбирал)
    status      TEXT    NOT NULL DEFAULT 'new',    -- new / in_work / prepaid / done / rejected
    created_at  TEXT    NOT NULL DEFAULT (datetime('now')),
    amount      INTEGER,                           -- сумма заказа, ₽
    deadline    TEXT,                              -- срок сдачи, YYYY-MM-DD
    note        TEXT                               -- заметка менеджера
);

-- Лог переписки (входящие и исходящие)
CREATE TABLE IF NOT EXISTS messages_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER NOT NULL,                  -- чат, с которым шёл обмен
    direction   TEXT    NOT NULL,                  -- in / out
    text        TEXT,
    created_at  TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_orders_user   ON orders(user_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_log_user      ON messages_log(user_id);
CREATE INDEX IF NOT EXISTS idx_users_source  ON users(source);
