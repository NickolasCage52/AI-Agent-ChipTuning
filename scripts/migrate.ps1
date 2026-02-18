& "$PSScriptRoot\check_docker.ps1"
docker compose run --rm core-api alembic upgrade head

