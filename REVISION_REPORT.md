# ОТЧЁТ РЕВИЗИИ РЕПОЗИТОРИЯ

```
╔══════════════════════════════════════════════╗
║         ОТЧЁТ РЕВИЗИИ РЕПОЗИТОРИЯ            ║
╚══════════════════════════════════════════════╝

1. СТРУКТУРА ПРОЕКТА
   apps/
     ui/               → Next.js фронтенд (Parts Assistant, demo, operator, admin)
   services/
     core-api/         → FastAPI + PostgreSQL, chat API, parts search, suppliers, seed
     agent-orchestrator/ → сценарный агент (tool-calling, lead-based)
     channel-gateway/  → webhooks (Telegram, widget), прокси в agent-orchestrator
     model-server/     → HTTP API для LLM (stub)
     rag-service/      → документы + full-text search
   scripts/            → demo.ps1, seed.ps1, migrate.ps1, import_vehicle_catalog.py, smoke_test.py
   demo-data/          → vehicle_catalog.csv, supplier_price.csv, reglament_to.txt, docs/

2. БИЗНЕС-ЛОГИКА (ядро подбора)
   Файл intent/slot extraction: services/core-api/app/chat/intent_extractor.py
   Файл поиска по БД:          services/core-api/app/chat/parts_search.py
   Файл ранжирования / тиров:  services/core-api/app/chat/parts_search.py (rank_and_tier)
   Промпты к Gemini:           intent_extractor.py (SYSTEM_PROMPT)
   Состояние: РАБОТАЕТ — chat API /api/chat возвращает bundles (economy/optimal/oem)

3. БАЗА ДАННЫХ
   Тип: PostgreSQL (pgvector/pgvector:pg16)
   ORM: SQLAlchemy 2.0
   Таблицы поставщиков/прайсов: suppliers, supplier_offers
   Каталог авто: vehicle_makes, vehicle_models, vehicle_engines
   Таблица истории/логов: lead_events (привязана к lead), НЕТ отдельной для Parts Assistant
   Таблица сессий пользователя: widget_sessions (привязана к lead), НЕТ tg_sessions

4. LLM АДАПТЕР
   Файл: services/core-api/app/llm/gemini_adapter.py
   Модель: gemini-1.5-flash (env GEMINI_MODEL)
   Таймауты/ретраи: да (timeout 15s, tenacity 2 попытки)
   PII-маскирование: да (mask_pii внутри gemini_adapter)

5. КОНФИГИ
   .env / .env.example: GEMINI_API_KEY, GEMINI_MODEL, DATABASE_URL, ASYNC_DATABASE_URL, LOG_LEVEL
   docker-compose.yml: postgres, core-api, agent-orchestrator, model-server, rag-service, ui
   TELEGRAM_BOT_TOKEN: НЕТ в .env.example (есть в channel-gateway settings)

6. TELEGRAM
   Уже есть интеграция: ДА (channel-gateway)
   Файл: services/channel-gateway/app/telegram.py (parse_update)
   НО: channel-gateway проксирует в agent-orchestrator (lead-based), НЕ в Parts Assistant chat
   Parts Assistant chat — отдельный поток (POST /api/chat в core-api)

═══════════════════════════════════════════════
ЧТО УЖЕ РАБОТАЕТ И БУДЕТ ПЕРЕИСПОЛЬЗОВАНО:
- intent_extractor.extract_intent_and_slots (sync) — обернём в asyncio
- parts_search.search_parts, search_by_sku_oem, rank_and_tier
- gemini_adapter.call_gemini + mask_pii
- logging_events.log_event (структура событий)
- БД: suppliers, supplier_offers, AsyncSession
- chat API возвращает bundles = {economy, optimal, oem}

ЧТО НУЖНО СОЗДАТЬ С НУЛЯ:
- apps/telegram_bot/ (bot, handlers, states, formatter)
- core/ — тонкие обёртки (или импорт из app) для изоляции
- Alembic миграция: tg_sessions, tg_search_history
- Сервис telegram_bot в docker-compose
- Отдельный flow: polling бот → intent → search → tiers (без agent-orchestrator)

ЧТО НУЖНО ПОЧИНИТЬ:
- intent_extractor синхронный — обернуть в run_in_executor для asyncio
- Адаптация схемы ответа: chat API возвращает bundles, intent — другой формат (parsed_request, search_plan)
- Маппинг name → display_name в форматтере
═══════════════════════════════════════════════
```
