param(
  [switch]$NoOpen,
  [int]$TimeoutSec = 120
)

$ErrorActionPreference = "Stop"

& "$PSScriptRoot\check_docker.ps1"

function Wait-HttpOk {
  param(
    [Parameter(Mandatory = $true)][string]$Url,
    [Parameter(Mandatory = $true)][int]$TimeoutSec
  )

  $deadline = (Get-Date).AddSeconds($TimeoutSec)
  while ((Get-Date) -lt $deadline) {
    try {
      $r = Invoke-WebRequest -Proxy $null -UseBasicParsing -TimeoutSec 5 -Uri $Url
      if ($r.StatusCode -ge 200 -and $r.StatusCode -lt 500) {
        return $true
      }
    } catch {
      Start-Sleep -Seconds 2
    }
  }
  return $false
}

Write-Host "Starting containers (detached)..."
docker compose up -d --build
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "docker compose up failed. See build output above." -ForegroundColor Yellow
  Write-Host "Try: docker compose build ui" -ForegroundColor Yellow
  throw "docker compose up failed"
}

Write-Host "Waiting for services to become ready..."
$okCore  = Wait-HttpOk -Url "http://127.0.0.1:8000/health" -TimeoutSec $TimeoutSec
$okAgent = Wait-HttpOk -Url "http://127.0.0.1:8001/health" -TimeoutSec $TimeoutSec
$okRag   = Wait-HttpOk -Url "http://127.0.0.1:8003/health" -TimeoutSec $TimeoutSec
$okUi    = Wait-HttpOk -Url "http://127.0.0.1:3000/demo"  -TimeoutSec $TimeoutSec

if (-not ($okCore -and $okAgent -and $okRag -and $okUi)) {
  Write-Host ""
  Write-Host "Some services did not become ready in time." -ForegroundColor Yellow
  docker compose ps
  Write-Host ""
  Write-Host "Tips:" -ForegroundColor Yellow
  Write-Host "- See logs: .\\scripts\\logs.ps1"
  Write-Host "- Stop stack: docker compose down"
  throw "Startup timeout"
}

Write-Host "Seeding demo data (idempotent)..."
docker compose run --rm core-api python -c "import asyncio; from app.seed import ensure_seed; asyncio.run(ensure_seed()); print('seed ok')"
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Seed step failed. Stack is still running; you can present UI, but data may be incomplete." -ForegroundColor Yellow
  Write-Host "See logs: .\\scripts\\logs.ps1" -ForegroundColor Yellow
  throw "Seed failed"
}

Write-Host ""
Write-Host "Ready. Open these pages:"
Write-Host "- Demo:      http://localhost:3000/demo"
Write-Host "- Operator:  http://localhost:3000/operator/leads"
Write-Host "- Admin:     http://localhost:3000/admin"
Write-Host ""
Write-Host "Stop: docker compose down"

if (-not $NoOpen) {
  Start-Process "http://localhost:3000/demo" | Out-Null
}

