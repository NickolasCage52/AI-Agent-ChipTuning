=== КАРТА ПРОЕКТА ===

FRONTEND:
  path: apps/ui
  framework: Next.js 14 + React 18
  entry point: apps/ui/src/app/demo/page.tsx
  chat component: apps/ui/src/components/DemoClient.tsx, ChatWidget.tsx
  car params widget: DemoClient.tsx (inline inputs brand/model/year/engine/mileage/vin)

BACKEND:
  path: services/core-api, services/agent-orchestrator
  framework: FastAPI
  entry point: services/core-api/app/main.py
  api routes: services/core-api/app/api/*.py
  db connection: services/core-api/app/db/engine.py, deps.py
  llm/ai code: отсутствует (model-server stub)

DATABASE:
  type: postgresql (pgvector)
  migrations: services/core-api/alembic/
  supplier tables: supplier_offers, suppliers
  demo data: demo-data/suppliers/demo.csv, demo-data/docs/*.md

DOCKER:
  services: postgres, core-api, agent-orchestrator, model-server, rag-service, ui
  порты: 3000 (ui), 8000 (core-api)

ENV:
  .env.example существует: нет
  переменные: DATABASE_URL, GEMINI_API_KEY, GEMINI_MODEL и др.

=== ЧТО РАБОТАЕТ ===
- docker compose up, demo page, плашки авто, rule-based NLU, поиск по supplier_offers
- Тирация economy/optimal/oem, build estimate, RAG

=== ЧТО СЛОМАНО / ОТСУТСТВУЕТ ПО PRD ===
- Gemini LLM, PII masking, /api/chat, intent/slots via LLM
- UI технические поля (oem=, sku=), typing indicator в demo
- synonyms.json, ranking_config, event logging, smoke_test.py

=== НАЧИНАЮ С: ===
services/core-api/app/llm/gemini_adapter.py — создаю LLM-адаптер Gemini
