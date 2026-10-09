# Бот продаж «Составление ТТК для общепита»

Telegram-бот на aiogram 3: прогревает лида с лендинга, квалифицирует его тремя вопросами,
показывает персональный оффер, пример ТТК и прайс, отвечает на вопросы, собирает заявку
и передаёт горячего клиента менеджеру. Есть админ-панель со статистикой воронки, рассылкой и экспортом в CSV.

## Как устроена воронка

```
Лендинг → t.me/<бот>?start=ttk_landing
        ↓
Приветствие под источник (ttk_landing / vk / default)
        ↓
Квиз: кто вы? → сколько позиций? → есть ли ТТК?
        ↓
Персональный оффер + рекомендованный пакет
        ↓
Пример ТТК (картинка + PDF) · Кейсы · Прайс · FAQ
        ↓
Заявка (5 шагов + подтверждение) → уведомление в чат менеджеров
        ↓
Менеджер меняет статус кнопками и отвечает клиенту реплаем прямо из чата
```

## Структура проекта

```
ttk_bot/
├── main.py                    # точка входа
├── requirements.txt
├── .env.example
├── Dockerfile
├── docker-compose.yml         # бот + Redis
├── deploy/ttk-bot.service     # unit для systemd
└── bot/
    ├── config.py              # чтение .env
    ├── texts.py               # ВСЕ тексты и кнопки — правьте здесь
    ├── assets/                # пример ТТК: example_ttk.pdf + превью .png
    ├── handlers/
    │   ├── start.py           # /start с UTM-меткой, меню, /cancel
    │   ├── funnel.py          # квиз, оффер, пример, кейсы, прайс
    │   ├── faq.py             # FAQ и вопросы менеджеру
    │   ├── order.py           # заявка (FSM) + статусы заявок
    │   ├── admin.py           # админка
    │   ├── common.py          # ответы менеджера реплаем, свободный текст, файлы
    │   └── errors.py          # глобальный обработчик ошибок
    ├── keyboards/inline.py, reply.py
    ├── states/                # OrderForm, AskQuestion, Broadcast
    ├── database/db.py, schema.sql
    ├── middlewares/
    │   ├── antiflood.py       # 5 сообщений / 10 сек
    │   ├── user_tracking.py   # регистрация юзера + лог входящих
    │   └── outgoing_log.py    # лог исходящих
    └── utils/                 # фильтры, уведомления, валидация, CSV
```

## Почему так

**SQLite (aiosqlite), а не PostgreSQL.** Бот на одном сервере, нагрузка — десятки-сотни лидов в день.
SQLite в режиме WAL с этим справляется с запасом, не требует отдельного сервера, бэкап — копия одного файла.
Если появится несколько экземпляров бота или CRM-интеграция с тяжёлой аналитикой — переезд на PostgreSQL
затронет только `bot/database/db.py`.

**FSM: MemoryStorage по умолчанию, Redis — по флагу.** Без настроек бот запускается сразу.
Минус памяти — при перезапуске клиент, заполнявший заявку, начнёт её заново. Чтобы этого не было,
задайте `REDIS_URL` (в docker-compose Redis уже включён).

**Антифлуд.** Сообщения — 5 за 10 секунд, как в ТЗ. Для нажатий кнопок лимит мягче (12 за 10 сек):
иначе клиент, быстро прокликивающий квиз, упирался бы в ограничение. Админы и чат менеджеров не ограничиваются.

**Свободный текст.** Сначала ищем ответ в FAQ по ключевым словам. Нашли — отвечаем и даём кнопку
«Спросить менеджера». Не нашли — пересылаем менеджеру. Если клиент сам нажал «Задать вопрос», вопрос
всегда уходит человеку (а подходящий ответ из FAQ показываем, пока он ждёт).

## Схема БД

| Таблица | Поля |
|---|---|
| `users` | id (Telegram ID), username, full_name, source (метка), segment, menu_size, ttk_status, reached_price, is_blocked, created_at, last_seen |
| `orders` | id, user_id, name, venue, positions, contact, comment, package, status (new / in_work / done / rejected), created_at |
| `messages_log` | id, user_id, direction (in / out), text, created_at |

Полный SQL — в `bot/database/schema.sql`, таблицы создаются автоматически при запуске.

## Быстрый старт (локально)

1. Создайте бота у [@BotFather](https://t.me/BotFather), получите токен.
2. Узнайте свой Telegram ID у [@userinfobot](https://t.me/userinfobot).
3. Создайте группу для менеджеров, добавьте туда бота. ID группы можно узнать, переслав из неё
   сообщение боту [@getidsbot](https://t.me/getidsbot) — он начинается с `-100`.
4. Установите и запустите (нужен Python 3.11+):

```bash
cd ttk_bot
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # впишите BOT_TOKEN, ADMIN_ID, MANAGER_CHAT_ID
python main.py
```

В логе появится готовая ссылка для лендинга: `https://t.me/<бот>?start=ttk_landing`.

## Деплой на VPS

### Вариант 1: Docker (рекомендуется)

```bash
# на сервере (Ubuntu 22.04+)
sudo apt update && sudo apt install -y docker.io docker-compose-v2
git clone <ваш-репозиторий> ttk_bot && cd ttk_bot   # или загрузите архив через scp
cp .env.example .env && nano .env
docker compose up -d --build
docker compose logs -f bot          # смотреть логи
```

Обновление: `git pull && docker compose up -d --build`. База и логи лежат в `./data` и `./logs` на хосте.

### Вариант 2: systemd

```bash
sudo apt update && sudo apt install -y python3 python3-venv
sudo useradd -r -m -d /opt/ttk_bot ttkbot
sudo cp -r ttk_bot/. /opt/ttk_bot/ && sudo chown -R ttkbot:ttkbot /opt/ttk_bot
sudo -u ttkbot bash -c "cd /opt/ttk_bot && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
sudo -u ttkbot cp /opt/ttk_bot/.env.example /opt/ttk_bot/.env && sudo -u ttkbot nano /opt/ttk_bot/.env

sudo cp /opt/ttk_bot/deploy/ttk-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now ttk-bot
journalctl -u ttk-bot -f            # логи
```

Бэкап базы: `cp /opt/ttk_bot/data/bot.db ~/backup_$(date +%F).db` (можно повесить на cron).

## Как пользоваться

**Клиент:** `/start`, `/price`, `/faq`, `/order`, `/cancel` + постоянные кнопки внизу экрана.

**Менеджер (в группе менеджеров):**
- под каждой заявкой кнопки «В работе / Закрыта / Отказ» — статус пишется в базу;
- чтобы ответить клиенту, ответьте **реплаем** на заявку, вопрос или файл от клиента — бот перешлёт ответ (текст, фото, документ, голосовое).

**Админ (в личке с ботом):**
- `/admin` — панель: заявки с пагинацией, статистика, рассылка, экспорт;
- `/orders`, `/stats`, `/export` — короткие команды;
- статистика показывает воронку start → прайс → заявка в целом и по каждому источнику;
- рассылка: пришлите любое сообщение (текст, фото с подписью, видео), бот покажет превью и попросит подтвердить. Тех, кто заблокировал бота, отмечает автоматически;
- CSV открывается в Excel без «кракозябр» (UTF-8 с BOM, разделитель `;`).

Ошибки в коде приходят админам в личку с трейсбеком, клиент видит вежливое сообщение.

## Что настроить под себя

Всё в `bot/texts.py`:

- `BRAND` — название;
- `PACKAGES` и `PRICE` — **цены и сроки в файле — пример**, поставьте свои;
- `CASES` — сейчас там описание работы по форматам заведений. Когда появятся реальные проекты,
  замените на настоящие кейсы с цифрами (с согласия клиентов);
- `WELCOME` — тексты под источники. Новая метка = новый ключ: например, `"avito": "..."`
  и ссылка `t.me/<бот>?start=avito`. Метки: латиница, цифры, `_` и `-`, до 64 символов;
- `FAQ` — вопросы, ответы и ключевые слова (`kw`) для распознавания свободного текста;
- `RECOMMEND_BY_MENU` — какой пакет рекомендовать при каком размере меню.

Пример ТТК — `bot/assets/example_ttk.pdf` (с водяным знаком «ОБРАЗЕЦ») и превью `example_ttk_preview.png`.
Замените своими файлами с теми же именами. Если файлов нет, бот предложит получить пример у менеджера.

## Замечания

- Нормативка в текстах: ГОСТ 31987-2012 (технологические документы общепита), ГОСТ 30390-2013,
  СанПиН 2.3/2.4.4282-26 (действует с 01.09.2026). Перед запуском сверьте формулировки с актуальными документами.
- Время в базе — UTC.
- Если клиент пришлёт альбом из 6+ фото разом, сработает антифлуд — поднимите `ANTIFLOOD_LIMIT` при необходимости.
