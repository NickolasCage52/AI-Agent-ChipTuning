## Autoshop AI Agent (on‑prem) — MVP

Монорепо с локально разворачиваемой системой (Docker Compose): Telegram/Web обращения → агент → lead → черновик сметы → approval оператором.  
Смета **никогда не считается “фактом”** без инструментов; любые деньги/закуп — **draft → requires_approval → approve**.

### Состав

- **`services/core-api`**: FastAPI + PostgreSQL + Alembic, OpenAPI, таблицы по ТЗ, импорт прайсов, поиск/сравнение, сметы, `agent_runs`
- **`services/agent-orchestrator`**: сценарный агент (tool-calling), логирует tool-calls, работает в рамках `lead_id`
- **`services/model-server`**: HTTP API для LLM (MVP stub, опционально прокси в Ollama)
- **`services/rag-service`**: загрузка документов + поиск по чанкам (MVP Postgres full-text search, хранение в Postgres)
- **`apps/ui`**: Next.js + Tailwind + простой demo UX (`/demo`, `/operator/leads`, `/admin`)

### Быстрый старт

Требования: Docker Desktop (чтобы работал `docker compose`).

```bash
docker compose up --build
```

Если у вас в PowerShell ошибка `docker: The term 'docker' is not recognized...` — установите Docker Desktop и откройте новый терминал. Для проверки можно запустить `.\scripts\up.ps1` — он покажет понятную подсказку.

Удобные команды:

```bash
make up
make down
make logs
make migrate
make seed
make smoke
make fmt
make lint
make test
```

Windows PowerShell аналоги:

```powershell
.\scripts\up.ps1
.\scripts\down.ps1
.\scripts\logs.ps1
.\scripts\migrate.ps1
.\scripts\seed.ps1
.\scripts\smoke_test.ps1
```

### Если IDE ругается на TypeScript (например, `Cannot find type definition file for 'node'`)

Это значит, что зависимости UI не установлены локально (нет `apps/ui/node_modules`). Для комфортной работы в IDE:

```powershell
cd apps/ui
npm install
```

Открыть:
- UI demo: `http://localhost:3000/demo`
- core-api OpenAPI: `http://localhost:8000/docs`
- agent-orchestrator OpenAPI: `http://localhost:8001/docs`
- rag-service OpenAPI: `http://localhost:8003/docs`

### Demo-steps (UI)

1) Откройте `http://localhost:3000/demo`
2) Нажмите быстрые кнопки **ТО / Запчасти / Проблема** (или введите текст)
3) Убедитесь, что появился `lead_id` и **черновик сметы** (справа)
4) Откройте `http://localhost:3000/operator/leads` → выберите лид → посмотрите **agent_runs timeline** + **events**
5) В `http://localhost:3000/admin` можно повторно импортировать CSV прайса и загрузить документы для RAG

### E2E демо (Windows / PowerShell)

```powershell
docker compose up --build
.\scripts\demo.ps1
```

### Smoke test (blocking)

```powershell
.\scripts\smoke_test.ps1
```

Runbook для демо: `scripts/demo.md`

Что происходит:
- сообщение → `agent-orchestrator /api/agent/message`
- создаётся lead в `core-api`
- агент **не ходит в public API**: он вызывает только `core-api /internal/tools/*` и пишет аудит в `agent_runs`
- импорт прайса `/api/suppliers/import` (CSV из `demo-data/`)
- (опционально) импорт прайса XLSX из `demo-data/supplier_price.xlsx` (20+ строк)
- поиск/сравнение офферов `/api/parts/search` + `/api/parts/compare`
- загрузка demo-документа в RAG (чтобы в ответах появился “Источник: ...”)
- оператор подтверждает смету в UI (`/operator`) кнопкой **Approve**

### Где смотреть логи agent_runs

В UI: `/operator/leads` → карточка лида → блок **agent_runs timeline** (там полный `tool_calls` массив).  
Через API:
- `GET /api/agent_runs?lead_id=...`

### Internal tools boundary

Для чистой границы “agent ↔ core” агент обращается только к:
- `POST /internal/tools/create_lead`
- `POST /internal/tools/update_lead`
- `POST /internal/tools/get_catalog_jobs`
- `POST /internal/tools/build_estimate`
- `POST /internal/tools/import_supplier_price`
- `POST /internal/tools/search_parts`
- `POST /internal/tools/compare_supplier_offers`
- `POST /internal/tools/save_estimate`
- `POST /internal/tools/request_approval`
- `POST /internal/tools/log_agent_run`

Public endpoints (`/api/*`) остаются для UI/оператора/админа.

### Observability

- Все Python-сервисы пишут **JSON-логи** в stdout.
- Корреляция запросов: заголовок `X-Request-Id` (генерируется, если не задан). Он прокидывается между сервисами и сохраняется в `agent_runs.tool_calls[].request_id`.

### Известные ограничения MVP

- **Токены дизайна**: прямой fetch CSS с `chiptuned.ru` может блокироваться; в MVP токены в `apps/ui/src/styles/variables.css` сделаны **максимально близкими по визуальной логике** (тёмная палитра + красный CTA). Их легко заменить на точные.
- **RAG**: MVP на Postgres full-text search (`tsvector` + GIN) по чанкам; embeddings/pgvector зарезервированы.
- **Supplier upsert**: упрощённый upsert (по sku/oem/name) для демо-объёмов.
- **Agent NLU**: stub (model-server) + rule-based fallback. Факты/смета — только через tools.

### Demo data

- **Прайсы**:
  - `demo-data/suppliers/demo.csv` (20 строк, импортируется автоматически при первом запуске)
  - `demo-data/supplier_price.csv` и `demo-data/supplier_price.xlsx` (legacy demo файлы, можно импортировать вручную)
- **Документы** (RAG):
  - `demo-data/docs/to_reglament.md`
  - `demo-data/docs/suspension_symptoms.md`

### Troubleshooting

- **`docker` не найден**: установите Docker Desktop и перезапустите терминал. Проверьте `docker --version`.
- **Proxy 407 при `pip`/`npm`**: в корпоративной сети может требоваться proxy аутентификация. Для локальной установки зависимостей настройте `HTTPS_PROXY`/`HTTP_PROXY` (или используйте Docker с доступом к registry/pypi/npm). В этом репо зависимости подразумеваются внутри Docker-образов.

