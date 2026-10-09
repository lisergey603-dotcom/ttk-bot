#!/usr/bin/env bash
# Установка и запуск бота на сервере Ubuntu/Debian без Docker.
# Запуск из папки проекта под root:  bash deploy/install.sh
# Повторный запуск безопасен — так же обновляются зависимости и перезапускается бот.
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/.." && pwd)"
ENV_FILE="$APP_DIR/.env"
SERVICE=/etc/systemd/system/ttk-bot.service

say() { echo -e "\n\033[1;32m==> $*\033[0m"; }
die() { echo -e "\n\033[1;31m❌ $*\033[0m"; exit 1; }

[ "$(id -u)" -eq 0 ] || die "Запустите от root: sudo bash deploy/install.sh"

# --- проверяем .env ---
[ -f "$ENV_FILE" ] || die "Нет файла .env. Создайте его (см. README) и запустите скрипт снова."
grep -qE '^BOT_TOKEN=[0-9]+:[A-Za-z0-9_-]{20,}' "$ENV_FILE" || die "В .env нет корректного BOT_TOKEN (вида 7712345678:AAH...)."
grep -q '^BOT_TOKEN=123456:' "$ENV_FILE" && die "В .env остался пример токена — вставьте токен от @BotFather."
grep -qE '^ADMIN_ID=-?[0-9]+' "$ENV_FILE" || die "В .env нет ADMIN_ID (ваш ID из @userinfobot)."
grep -q '^ADMIN_ID=123456789$' "$ENV_FILE" && die "В .env остался пример ADMIN_ID — вставьте свой ID из @userinfobot."
chmod 600 "$ENV_FILE"

# --- системные пакеты ---
say "Устанавливаю Python"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip >/dev/null
python3 -c 'import sys; assert sys.version_info >= (3, 10), sys.version' \
  || die "Нужен Python 3.10+. Переустановите сервер на Ubuntu 22.04/24.04."

# --- виртуальное окружение и зависимости ---
say "Ставлю зависимости бота (1–2 минуты)"
[ -x "$APP_DIR/.venv/bin/python" ] || python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install -q --upgrade pip
"$APP_DIR/.venv/bin/pip" install -q -r "$APP_DIR/requirements.txt"
mkdir -p "$APP_DIR/data" "$APP_DIR/logs"

# --- служба systemd: автозапуск и перезапуск при падении ---
say "Настраиваю автозапуск"
cat > "$SERVICE" <<EOF
[Unit]
Description=Telegram bot Техкарты PRO
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=$APP_DIR
ExecStart=$APP_DIR/.venv/bin/python main.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable -q ttk-bot
STARTED_AT="$(date '+%Y-%m-%d %H:%M:%S')"
systemctl restart ttk-bot

say "Проверяю запуск (до 60 секунд)"
OK=0
for _ in $(seq 1 30); do
  sleep 2
  LOG="$(journalctl -u ttk-bot --since "$STARTED_AT" --no-pager)"
  if grep -q "запущен" <<<"$LOG"; then OK=1; break; fi
done
if [ "$OK" = 1 ] && systemctl is-active -q ttk-bot; then
  grep "запущен" <<<"$LOG" | tail -1
  echo -e "\n\033[1;32m✅ Бот работает. Напишите ему /start в Telegram.\033[0m"
  echo "Логи:        journalctl -u ttk-bot -f"
  echo "Перезапуск:  systemctl restart ttk-bot"
  echo "Обновление:  cd $APP_DIR && git pull && bash deploy/install.sh"
else
  tail -15 <<<"$LOG"
  say "Проверяю связь сервера с Telegram"
  if curl -sS -m 10 -o /dev/null https://api.telegram.org 2>/dev/null; then
    echo "api.telegram.org доступен — проблема в настройках (проверьте BOT_TOKEN в .env)."
  else
    echo -e "\033[1;33mСервер НЕ достаёт до api.telegram.org — Telegram API блокируется на стороне провайдера.\033[0m"
    echo "Нужен прокси (TELEGRAM_PROXY в .env) или сервер за пределами РФ."
  fi
  die "Бот не запустился — пришлите скриншот этого экрана."
fi
