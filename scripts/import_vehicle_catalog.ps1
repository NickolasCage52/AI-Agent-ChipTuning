& "$PSScriptRoot\check_docker.ps1"
$root = Split-Path $PSScriptRoot -Parent
docker compose run --rm -v "${root}/scripts:/scripts" -v "${root}/demo-data:/demo-data" core-api python /scripts/import_vehicle_catalog.py --file /demo-data/vehicle_catalog.csv @args
