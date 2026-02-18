$ErrorActionPreference = "Stop"

function Require-Docker {
  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) {
    Write-Host ""
    Write-Host "Docker не найден (команда 'docker' отсутствует)." -ForegroundColor Red
    Write-Host ""
    Write-Host "Как исправить (Windows 10/11):" -ForegroundColor Yellow
    Write-Host "1) Установите Docker Desktop: https://www.docker.com/products/docker-desktop/"
    Write-Host "   Либо через winget (если доступен): winget install -e --id Docker.DockerDesktop"
    Write-Host "2) Перезапустите PowerShell/терминал."
    Write-Host "3) Проверьте: docker --version"
    Write-Host ""
    throw "Docker CLI not found"
  }

  # Basic sanity check
  try {
    docker version | Out-Null
  } catch {
    Write-Host "Docker найден, но daemon не доступен. Откройте Docker Desktop и дождитесь запуска." -ForegroundColor Yellow
    throw
  }
}

Require-Docker

