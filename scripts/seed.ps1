& "$PSScriptRoot\check_docker.ps1"
docker compose run --rm core-api python -c "import asyncio; from app.seed import ensure_seed; asyncio.run(ensure_seed()); print('seed ok')"

