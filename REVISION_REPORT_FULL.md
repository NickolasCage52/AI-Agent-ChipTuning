# ОТЧЁТ РЕВИЗИИ ПРОЕКТА: Telegram Parts Assistant

```
╔══════════════════════════════════════════════════════╗
║              ОТЧЁТ РЕВИЗИИ ПРОЕКТА                  ║
╚══════════════════════════════════════════════════════╝

1. TELEGRAM BOT
   Библиотека: aiogram 3.x
   Файл точки входа: apps/telegram_bot/bot.py
   Handlers: commands.py, messages.py, callbacks.py
   FSM/состояния: есть (PartsSearch: idle, waiting_clarification, showing_results)
   Inline-кнопки: есть (tier_economy, tier_optimal, tier_oem, reset)
   Контекст: MemoryStorage (при рестарте теряется)

2. LLM ИНТЕГРАЦИЯ
   Ollama: НЕ ПОДКЛЮЧЕНА (в проекте только Gemini)
   Gemini: подключена (core/llm_adapter.py, call_gemini)
   Реально вызывается: да (core/intent.py → call_gemini)
   Влияет на извлечение сущностей: да
   Промпты: есть — core/intent.py (SYSTEM_PROMPT)
   Дефолтные значения вместо LLM: при ошибке Gemini → _fallback_extract (rule-based)
   .env.example: Ollama НЕ упоминается, требуется GEMINI_API_KEY

3. ИМПОРТ ПРАЙСОВ
   Файлы прайса найдены: data/price_sources/base.xlsx, defect.xlsx
   Текущий скрипт импорта: scripts/import_prices.py
   Колонки читаются: ЧАСТИЧНО
   
   КРИТИЧЕСКАЯ ПРОБЛЕМА — несовпадение имён колонок:
   Файл base.xlsx имеет: "Цена, руб.", "Срок поставки, дн."
   COLUMN_ALIASES ожидает: "Цена", "Срок поставки (дн.)"
   Результат: 100% строк без цены, 100% без срока
   
   Цены после импорта: NULL (колонка не маппится)
   Сроки после импорта: NULL (колонка не маппится)
   Проблема "99 дней": core/price_search.py строка 90 (_row_to_item)
   Проблема "цена по запросу": formatter.py:27, callbacks.py:41, price_search.py:36

4. ПОИСК
   Реализован: да (core/price_search.py)
   По артикулу: работает (нормализация normalize_article)
   По OEM: работает (REPLACE для сравнения)
   По названию: работает (LIKE по nomenclature, description, brand)
   Нормализация: есть (артикулы)
   Дубли: дедупликация по (id, is_defect)

5. ХРАНИЛИЩЕ
   Тип БД: SQLite (data/parts.db)
   Таблицы: products, products_defect, import_runs
   Таблица истории: НЕТ (log_event_to_db — заглушка)
   Таблица сессий: НЕТ (FSM в памяти)
   Таблица логов: НЕТ

6. ДИАГНОСТИКА ПРОБЛЕМ
   Почему бот возвращает плохие ответы:
     - Прайс импортирован БЕЗ цен и сроков (неверный маппинг колонок)
     - Economy tier пустой (нет цен)
     - Ранжирование использует price=999999, delivery_days=99 как fallback
   
   Почему LLM не влияет на качество:
     - LLM работает (Gemini), но поиск возвращает позиции без цен
     - Форматтер подставляет "цена по запросу", "уточнить" вместо честного "не указано в прайсе"
   
   Почему часто "ничего не найдено":
     - Поиск работает, но при пустых economy/optimal из-за price=0 может быть странное поведение
     - Некоторые запросы не попадают в LIKE (stopwords, длина терминов)
   
   Что нужно переписать полностью:
     - COLUMN_ALIASES в import_prices.py (+ "Цена, руб.", "Срок поставки, дн.")
     - core/price_search.py: убрать 99, 999999; использовать None
     - formatter.py, callbacks.py: "не указано в прайсе" вместо "цена по запросу"/"уточнить"
     - Добавить Ollama как primary LLM (по ТЗ)
     - Реализовать log_event_to_db, sessions в SQLite
     - scripts/smoke_test.py: сейчас тестирует core-api, не Telegram-бота
   
   Что можно переиспользовать:
     - core/intent.py (SYSTEM_PROMPT, extract_intent_and_slots, _fallback_extract)
     - core/price_search.py (search, build_tiers, normalize_article) — с правками
     - apps/telegram_bot/* — структура handlers, FSM, formatter
     - scripts/import_prices.py — логика чтения XLSX/CSV
══════════════════════════════════════════════════════
```

## Текущая статистика БД (до исправления импорта)

| Таблица          | Всего | Без цены | Без срока | delivery_days=99 |
|------------------|-------|----------|-----------|------------------|
| products         | 136773 | 100%     | 100%      | 0                |
| products_defect  | 10301  | 100%     | 100%      | 0                |

**Образец из products:** `('4U', '4UAN170004', None, None, '1')` — price=None, delivery_days=None.

## Файлы с проблемными дефолтами

| Файл              | Строка | Проблема                          |
|-------------------|--------|-----------------------------------|
| core/price_search.py | 90   | `delivery_days=99` при NULL       |
| core/price_search.py | 201  | `price or 999999`, `delivery_days or 99` |
| core/price_search.py | 204  | `delivery_days or 30`             |
| apps/telegram_bot/formatter.py | 27 | "цена по запросу"         |
| apps/telegram_bot/formatter.py | 29 | "уточнить"                |
| apps/telegram_bot/handlers/callbacks.py | 41 | "уточнить"          |
| core/price_search.py | 36, 41, 51 | display_price/delivery/stock → "цена по запросу"/"уточнить" |

## Структура проекта (Parts Assistant)

```
apps/telegram_bot/
  bot.py           — точка входа, aiogram Bot + Dispatcher
  handlers/
    commands.py    — /start, /help, /reset
    messages.py    — обработка текста, intent → search → tiers
    callbacks.py   — tier_*, reset
  formatter.py     — format_results, format_clarification
  states.py        — PartsSearch FSM

core/
  intent.py        — extract_intent_and_slots (Gemini), _fallback_extract
  llm_adapter.py   — call_gemini (только Gemini, нет Ollama)
  price_search.py  — search(), build_tiers(), PriceItem
  pii_masker.py    — mask_pii
  logger.py        — log_event, log_event_to_db (заглушка)

scripts/
  import_prices.py — импорт XLSX/CSV в SQLite
  diagnose_import.py — диагностика (создан)
  smoke_test.py    — тесты core-api /api/chat (НЕ Telegram bot)
```

## Следующие шаги (Фаза 1)

1. Добавить в COLUMN_ALIASES: `"Цена, руб.": "price"`, `"Срок поставки, дн.": "delivery_days"`
2. Перезапустить импорт
3. Убрать 99/999999 в price_search.py
4. Заменить "цена по запросу"/"уточнить" на "не указано в прайсе"
