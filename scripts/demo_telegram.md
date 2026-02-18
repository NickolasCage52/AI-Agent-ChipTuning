## Demo: Telegram webhook (ngrok)

### Prereqs
- Telegram bot token (`TELEGRAM_BOT_TOKEN`)
- Public URL (например, ngrok): `PUBLIC_BASE_URL=https://xxxx.ngrok-free.app`

### Steps
1) Запустите стек:

```bash
docker compose up --build
```

2) Пробросьте порт `8004` наружу через ngrok:

```bash
ngrok http 8004
```

3) Установите env vars для `channel-gateway` (через `.env` или прямо в compose):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_WEBHOOK_SECRET` (любой секрет)
- `PUBLIC_BASE_URL` (ngrok https URL)

4) Вызовите helper endpoint:

- `GET http://localhost:8004/telegram/set-webhook`

5) Напишите боту в Telegram.

Проверка:
- В UI оператора `http://localhost:3000/operator/leads` найдите lead и откройте timeline.
- Должны появиться события:
  - `telegram.update_received`
  - `telegram.reply_sent`
  - а также агентские события `agent.*`

