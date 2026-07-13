# ⚡ VDS Reseller Bot

Production-ready Telegram-бот для перепродажи VDS/VPS серверов **Vultr** и **Hetzner Cloud** с автоматической наценкой **+35%**, внутренним балансом, автоматической выдачей серверов и веб-админкой.

## Возможности

**Для клиентов (Telegram):**
- 📦 Каталог с живыми ценами из API провайдеров (+35% наценка автоматически)
- 🛒 Полный цикл заказа: провайдер → локация → тариф → ОС → hostname → SSH-ключ/пароль → период (1/3/6/12 мес. со скидками)
- ⚡ Автоматическое создание сервера после оплаты (cloud-init: обновление системы, ufw, fail2ban, SSH-ключи)
- 🖥 Управление серверами: перезагрузка, переустановка ОС, сброс пароля, продление, удаление
- 💰 Внутренний баланс с историей транзакций (+ хук для CryptoBot / YooKassa / Telegram Stars)
- 🤝 Реферальная программа (бонус с первой покупки реферала)
- 🆘 Поддержка через тикеты
- ⏳ Уведомления об истечении (за 7 и 1 день), автопродление

**Для администратора:**
- 🌐 Веб-админка (FastAPI + Jinja2 + HTMX + Tailwind): дашборд с выручкой/прибылью, пользователи, заказы, серверы, ручные действия
- 🤖 Telegram-команды: `/admin`, `/find`, `/addbalance`, `/ban`, `/reply`, `/orders`

## Стек

Python 3.12 · aiogram 3 · PostgreSQL · SQLAlchemy 2 (async) · Alembic · FastAPI · APScheduler · Docker · loguru · pydantic v2

## Структура проекта

```
app/
├── bot/            # Telegram-бот: handlers, keyboards, middlewares, FSM
├── web/            # Веб-админка: FastAPI + Jinja2 + HTMX
├── providers/      # Клиенты API Vultr и Hetzner (единый интерфейс)
├── services/       # Бизнес-логика: заказы, баланс, provisioning, каталог
├── models/         # SQLAlchemy-модели: User, Order, Server, Transaction, SupportTicket
├── scheduler/      # Фоновые задачи APScheduler
├── core/           # Конфиг, БД, безопасность, ценообразование, логи
└── utils/          # cloud-init, форматирование
alembic/            # Миграции БД
examples/           # Пример cloud-init
```

## Быстрый старт

### 1. Получите API-ключи

**Telegram Bot:**
1. Напишите [@BotFather](https://t.me/BotFather) → `/newbot` → получите токен.

**Vultr:**
1. Зарегистрируйтесь на [vultr.com](https://www.vultr.com).
2. [Account → API](https://my.vultr.com/settings/#settingsapi) → Enable API → скопируйте **Personal Access Token**.
3. ⚠️ В разделе Access Control добавьте IP вашего сервера в whitelist (или разрешите все: `0.0.0.0/0` — менее безопасно).

**Hetzner Cloud:**
1. Зарегистрируйтесь на [hetzner.com](https://www.hetzner.com/cloud).
2. [Cloud Console](https://console.hetzner.cloud) → выберите проект → **Security → API Tokens** → Generate API Token с правами **Read & Write**.

### 2. Настройте окружение

```bash
git clone <repo-url> && cd vds-reseller-bot
cp .env.example .env
```

Заполните `.env`:
- `BOT_TOKEN`, `ADMIN_IDS` (ваш Telegram ID — узнать: [@userinfobot](https://t.me/userinfobot))
- `VULTR_API_KEY`, `HETZNER_API_TOKEN` (можно указать только одного провайдера)
- `POSTGRES_PASSWORD`, `WEB_ADMIN_PASSWORD`, `WEB_SECRET_KEY`
- `ENCRYPTION_KEY` — сгенерируйте:
  ```bash
  python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  ```
- `MASTER_SSH_PUBLIC_KEY` — ваш публичный ключ для аварийного доступа к серверам клиентов (рекомендуется)

### 3. Запустите через Docker

```bash
docker compose up -d --build
```

Поднимутся: PostgreSQL → миграции Alembic → бот → веб-админка на `http://localhost:8000`.

### 4. Проверьте

- Напишите боту `/start` — увидите главное меню.
- Откройте `http://localhost:8000` — войдите с паролем из `WEB_ADMIN_PASSWORD`.
- Начислите себе тестовый баланс: `/addbalance <ваш_telegram_id> 100` в боте.
- Закажите сервер через «📦 Каталог серверов».

## Запуск без Docker (разработка)

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# PostgreSQL должен быть запущен, POSTGRES_HOST=localhost в .env
alembic upgrade head

python -m app.bot.main                                   # бот + планировщик
uvicorn app.web.main:app --reload --port 8000            # веб-админка (отдельный терминал)
```

## Ценообразование

- Внутренняя валюта — **USD**. Цены Hetzner (EUR) конвертируются по курсу `EUR_USD_RATE`.
- Цена клиента = себестоимость провайдера × (1 + `MARKUP_PERCENT`/100), по умолчанию **+35%**.
- Скидки за период настраиваются в `PERIOD_DISCOUNTS` (по умолчанию: 3 мес. −3%, 6 мес. −5%, 12 мес. −10%).

## Подключение платёжных систем

Пополнение сейчас — заглушка (ручное зачисление через поддержку/админку). Для автоматизации:

1. Создайте инвойс у провайдера в `app/bot/handlers/balance.py` (`deposit_stub`).
2. В webhook-обработчике платежа вызовите:
   ```python
   from app.services.balance import deposit
   await deposit(session, user, amount, "Пополнение через CryptoBot", external_payment_id=invoice_id)
   ```
Подходит для CryptoBot, YooKassa, Telegram Stars — вся логика транзакций уже готова.

## Фоновые задачи

| Задача | Расписание | Что делает |
|---|---|---|
| Автопродление | ежедневно 08:00 UTC | продлевает серверы с включённым автопродлением |
| Уведомления об истечении | ежедневно 09:00 UTC | предупреждения за 7 и 1 день, пометка истёкших |
| Удаление истёкших | ежедневно 10:00 UTC | удаляет серверы через 2 дня после истечения (grace-период) |
| Синхронизация статусов | каждые 10 мин | статусы и IP из API провайдеров |
| Подхват заказов | каждые 2 мин | доделывает provisioning «зависших» оплаченных заказов |

## Безопасность

- API-ключи и секреты — только в `.env` (в `.gitignore`).
- Root-пароли серверов хранятся в БД **зашифрованными** (Fernet).
- Веб-админка: пароль + подписанные cookie-сессии; admin-команды бота — whitelist Telegram ID.
- Rate-limit на все действия в боте (анти-спам).
- На каждый созданный сервер ставится ufw (открыт только SSH) и fail2ban.

## Лицензия

MIT
