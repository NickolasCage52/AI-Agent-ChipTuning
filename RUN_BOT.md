# Запуск и проверка Parts Assistant бота

## 1. Подготовка

### 1.1 Установка зависимостей

```powershell
cd "c:\Users\nikit\OneDrive\Рабочий стол\WorkPage\AI_Apps\Ai_agent_chiptuning"
pip install -r requirements-telegram-bot.txt
```

### 1.2 Настройка .env

Убедитесь, что в `.env` есть:

```
GEMINI_API_KEY=ваш_ключ
TELEGRAM_BOT_TOKEN=токен_от_BotFather
GEMINI_MODEL=gemini-2.0-flash
```

### 1.3 База прайсов

Если прайсы уже импортированы — можно пропустить. Иначе:

```powershell
python -m scripts.import_prices
```

Файлы прайсов: `data/price_sources/base.xlsx` и `data/price_sources/defect.xlsx` (или `.csv`).

---

## 2. Запуск бота

```powershell
python -m apps.telegram_bot.bot
```

Ожидаемый вывод:
```
[INFO] __main__: Telegram bot starting...
[INFO] aiogram.dispatcher: Run polling for bot @AI_chip_tuning_bot ...
```

---

## 3. Проверка в Telegram

1. Откройте бота в Telegram (по имени из BotFather).
2. Напишите `/start` — бот ответит приветствием.
3. Напишите `/reset` — контекст сбросится.
4. Проверьте сценарии:

| Сценарий | Что написать | Ожидание |
|----------|--------------|----------|
| Запрос с авто и деталью | `тормозные колодки на Kia Rio 2017` | Результаты поиска или уточняющий вопрос |
| Только авто | `Kia Rio 2017` | Вопрос: «Что именно нужно? Укажите название детали» |
| Ответ на уточнение | `колодки` | Поиск по «тормозные колодки» |
| По артикулу | `артикул 04465-33480` | Поиск по артикулу в прайсе |

5. После результатов — кнопки «🟢 Эконом», «🟡 Оптимум», «🔵 OEM» и «🔄 Новый поиск».

---

## 4. Быстрая проверка без Telegram

Проверка поиска и intent:

```powershell
python -c "
from core.price_search import search, build_tiers
from core.intent import _fallback_extract

# Поиск
r = search(query='тормозные колодки', max_results=5)
print('Найдено:', len(r))

# Fallback intent
x = _fallback_extract('колодки на Kia Rio 2017', {}, None)
print('car_context:', x['car_context'])
print('part_type:', x['part_type'])
"
```

---

## 5. Возможные проблемы

| Симптом | Решение |
|--------|---------|
| `TELEGRAM_BOT_TOKEN is not set` | Добавить токен в .env |
| `GEMINI_API_KEY is not set` | Добавить ключ в .env (или бот будет работать только в rule-based режиме) |
| 404 / 429 от Gemini | Бот перейдёт на fallback — поиск будет работать без ИИ |
| «ничего не найдено» | Запустить `python -m scripts.import_prices`, проверить `data/parts.db` |
| Бот не отвечает | Проверить токен: `curl "https://api.telegram.org/bot{TOKEN}/getMe"` |
