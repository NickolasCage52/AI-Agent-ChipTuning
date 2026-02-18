.PHONY: up down logs ps rebuild migrate makemigrations seed fmt lint test smoke

.RECIPEPREFIX := >

up:
>docker compose up --build

down:
>docker compose down -v

logs:
>docker compose logs -f --tail=200

ps:
>docker compose ps

rebuild:
>docker compose build --no-cache

migrate:
>docker compose run --rm core-api alembic upgrade head

makemigrations:
>docker compose run --rm core-api alembic revision --autogenerate -m "$(msg)"

seed:
>docker compose run --rm core-api python -c "import asyncio; from app.seed import ensure_seed; asyncio.run(ensure_seed()); print('seed ok')"

fmt:
>docker compose run --rm core-api black /app/app /app/tests
>docker compose run --rm agent-orchestrator black /app/app
>docker compose run --rm ui npm run format

lint:
>docker compose run --rm core-api ruff check /app/app /app/tests
>docker compose run --rm agent-orchestrator ruff check /app/app
>docker compose run --rm ui npm run lint

test:
>docker compose up -d postgres
>docker compose run --rm core-api sh -c "alembic upgrade head && python -m pytest -q"
>docker compose run --rm agent-orchestrator python -m pytest -q

smoke:
>powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1

