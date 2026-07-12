# ULTIMA HOST

Сайт-каталог и Telegram-бот для ресейла VDS на базе Hetzner Cloud. Клиент выбирает тариф в боте, оплачивает картой/СБП/криптовалютой — сервер создаётся автоматически через Hetzner API, доступы приходят в Telegram.

## Структура монорепозитория

```
apps/
  web/    — сайт на Next.js (лендинг + каталог тарифов)
  bot/    — Telegram-бот (grammY): каталог, заказ, оплата, выдача сервера
packages/
  db/     — Prisma-схема и клиент БД (Postgres), общая для web и bot
  core/   — бизнес-логика: Hetzner API, ценообразование, платёжные провайдеры, сервис заказов
```

## Как это работает

1. Пользователь открывает бота → видит тарифы → жмёт «Заказать» → выбирает способ оплаты (карта / СБП / крипто).
2. Создаётся заказ в БД, бот показывает ссылку на оплату (Platega) или реквизиты для ручной оплаты.
3. После подтверждения оплаты (вебхуком Platega, либо вручную админом) вызывается `confirmOrderPayment`, который создаёт сервер через Hetzner Cloud API и отправляет клиенту IP/пароль.
4. Сайт — витрина тарифов и лендинг; сама покупка проходит через бота.

Пока не подключены реальные ключи Hetzner/Platega, всё работает в **demo-режиме**: сервер «создаётся» с фейковым IP, а оплата подтверждается вручную командой админа в боте — это позволяет протестировать весь сценарий целиком уже сейчас.

## Ценообразование

Цена тарифа считается автоматически из себестоимости Hetzner:

```
priceRub = costEur × (курс EUR/RUB × 1.05) × 1.30
```

- **`costEur`** — реальная цена `server_type` в Hetzner Cloud (EUR/мес), задаётся по каждому тарифу в `packages/db/prisma/seed.ts`. Сверяйте с [console.hetzner.cloud/pricing](https://console.hetzner.cloud) при изменении прайса Hetzner.
- **Курс** берётся из ЦБ РФ (`EXCHANGE_RATE_SOURCE_URL`, по умолчанию cbr-xml-daily.ru) и кэшируется в таблице `ExchangeRate`, чтобы не дёргать внешний API на каждый показ тарифа.
- **+5%** — наценка на курс валюты, **+30%** — наценка ресейла. Обе константы — в `packages/core/src/pricing.ts` (`EXCHANGE_MARKUP`, `RESALE_MARKUP`), меняйте под свою модель.

Курс и цены пересчитываются автоматически при старте бота и затем каждые 6 часов (`apps/bot/src/index.ts`). Обновить вручную:

```bash
pnpm price:refresh
```

Для продакшена вместо интервала внутри процесса бота можно повесить `pnpm price:refresh` на cron/systemd timer.

## Оплата

Основной провайдер — **[Platega](https://platega.io)** (карты, СБП, криптовалюта: BTC/USDT/TON и др. — конкретный актив клиент выбирает уже на хостед-странице оплаты). Реализация в `packages/core/src/payments/platega.ts` собрана по [документации Platega](https://docs.platega.io/): эндпоинт `POST /transaction/process`, авторизация заголовками `X-MerchantId`/`X-Secret`. **Перед продакшеном сверьте актуальные детали API в личном кабинете Platega** — у агрегаторов такого типа контракт иногда меняется, а часть деталей (например, набор доступных крипто-сетей) настраивается на стороне мерчанта.

Логика выбора провайдера (`packages/core/src/payments/index.ts`):
- Если заданы `PLATEGA_MERCHANT_ID` и `PLATEGA_SECRET` — все способы оплаты (карта/СБП/крипто) идут через Platega.
- Если Platega не настроена, а способ оплаты — «крипто» и задан `CRYPTOBOT_TOKEN` — используется [@CryptoBot](https://t.me/CryptoBot) (Crypto Pay API).
- Иначе — ручная оплата по реквизитам (`MANUAL_PAYMENT_INSTRUCTIONS`) с подтверждением админом в боте.

Вебхук Platega: `apps/web/app/api/payments/platega/webhook`. Настройте его URL (`https://<ваш-домен>/api/payments/platega/webhook`) в личном кабинете Platega.

## Быстрый старт

Требования: Node.js 20+, pnpm 9+, Docker (для Postgres).

```bash
pnpm install
cp .env.example .env   # заполните BOT_TOKEN и ADMIN_CHAT_ID

docker compose up -d           # поднять Postgres
pnpm db:migrate                # применить миграции
pnpm db:seed                   # засеять тестовые тарифы (примерные цены)
pnpm price:refresh              # подставить актуальный курс и пересчитать цены

pnpm dev:web                   # сайт на http://localhost:3000
pnpm dev:bot                   # бот (long polling)
```

## Настройка переменных окружения (`.env`)

Скопируйте `.env.example` в `.env` и заполните:

- **`BOT_TOKEN`** — токен бота от [@BotFather](https://t.me/BotFather).
- **`ADMIN_CHAT_ID`** — ваш Telegram user id (узнать у [@userinfobot](https://t.me/userinfobot)) или id группы для уведомлений об оплате.
- **`HETZNER_API_TOKEN`** — токен из Hetzner Cloud Console → ваш проект → Security → API Tokens (права Read & Write). Пока пусто — бот работает в demo-режиме.
- **`PLATEGA_MERCHANT_ID` / `PLATEGA_SECRET`** — данные мерчанта Platega. Пока пусто — оплата работает в ручном режиме (см. выше).
- **`CRYPTOBOT_TOKEN`** — опциональный резервный способ оплаты криптовалютой, если не используете Platega.

## Тарифы

Тарифы (название, CPU/RAM/диск, себестоимость в EUR, `server_type` и локация Hetzner) заданы в `packages/db/prisma/seed.ts`. Цена в рублях считается автоматически (см. «Ценообразование» выше) — вручную её задавать не нужно.

## Деплой

- **web** и **bot** — независимые Node-процессы, можно развернуть на одном VPS (например, том же Hetzner) через `pm2`/`systemd`/Docker.
- Постоянная БД — Postgres (см. `docker-compose.yml`), для продакшена вынесите её на отдельный managed-инстанс или volume с бэкапами.
- Для вебхука Platega (`apps/web/app/api/payments/platega/webhook`) и общего вебхука других провайдеров (`apps/web/app/api/payments/webhook`) убедитесь, что домен сайта доступен извне и настроен HTTPS.
