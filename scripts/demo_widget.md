## Demo: Web Widget (local)

1) Запустите стек:

```bash
docker compose up --build
```

2) Откройте виджет напрямую:

- `http://localhost:8004/widget`

3) Или вставьте embed-скрипт на любую локальную страницу:

```html
<script src="http://localhost:8004/widget.js"></script>
```

4) Напишите сообщение в виджете.

Проверка:
- В UI оператора откройте `http://localhost:3000/operator/leads` → выберите lead → смотрите **Event Timeline**
- Должны появиться события:
  - `widget.session_created`
  - `widget.message_received`
  - `widget.reply_sent`

