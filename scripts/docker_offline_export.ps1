param(
  [Parameter(Mandatory=$false)]
  [string]$Tag = $(if ($env:PLANOPT_TAG) { $env:PLANOPT_TAG } else { "offline" })
)

$ErrorActionPreference = "Continue"

Write-Host "[check] docker info"
try {
  docker info | Out-Null
} catch {
  Write-Host "Ошибка: Docker недоступен. Проверьте, что Docker Engine запущен."
  exit 10
}

$Out = "planopt-images-$Tag.tar"

Write-Host "[1/4] Build compose images... (может занять несколько минут)"
docker compose build

Write-Host "[2/4] Detect compose image names and tag..."

# Docker Compose по умолчанию использует имя директории как project name (обычно в lowercase).
$prefix = (Get-Location | Split-Path -Leaf).ToLowerInvariant()
$webImg = $prefix + "-web:latest"
$workerImg = $prefix + "-worker:latest"
$frontendImg = $prefix + "-frontend:latest"

function Has-Image([string]$Ref) {
  & docker image inspect $Ref *> $null
  return ($LASTEXITCODE -eq 0)
}

if (-not (Has-Image $webImg) -or -not (Has-Image $workerImg) -or -not (Has-Image $frontendImg)) {
  Write-Host "Compose image names were not found by expected prefix. Fallback to docker images scanning..."
  $all = docker images --format "{{.Repository}}:{{.Tag}}"
  $webCand = ($all -split "`n" | Where-Object { $_ -match '-web:latest$' } | Select-Object -First 1)
  $workerCand = ($all -split "`n" | Where-Object { $_ -match '-worker:latest$' } | Select-Object -First 1)
  $frontendCand = ($all -split "`n" | Where-Object { $_ -match '-frontend:latest$' } | Select-Object -First 1)

  if ($webCand) { $webImg = $webCand }
  if ($workerCand) { $workerImg = $workerCand }
  if ($frontendCand) { $frontendImg = $frontendCand }
}

if (-not (Has-Image $webImg) -or -not (Has-Image $workerImg) -or -not (Has-Image $frontendImg)) {
  Write-Host "Failed to detect image names web/worker/frontend."
  Write-Host ("Expected: " + "${prefix}-web:latest / " + "${prefix}-worker:latest / " + "${prefix}-frontend:latest")
  Write-Host "Current docker images snapshot:"
  docker images | Select-Object -First 50
  exit 1
}

docker tag $webImg "planopt/web:$Tag" | Out-Null
docker tag $workerImg "planopt/web:$Tag" | Out-Null
docker tag $frontendImg "planopt/frontend:$Tag" | Out-Null

Write-Host "[3/4] Ensure base images for offline mode..."
$skipPullBase = $false
if ($env:SKIP_PULL_BASE -and ($env:SKIP_PULL_BASE -eq "true")) { $skipPullBase = $true }

function Ensure-Image([string]$Img) {
  $exists = $false
  & docker image inspect $Img *> $null
  if ($LASTEXITCODE -eq 0) {
    $exists = $true
  }
  if ($exists) {
    Write-Host "  - already present: $Img"
    return
  }
  if ($skipPullBase) {
    Write-Host "  - missing and SKIP_PULL_BASE=true: $Img"
    return
  }
  Write-Host "  - pulling: $Img"
  docker pull $Img | Out-Null
}

Ensure-Image "postgres:14"
Ensure-Image "redis:7"
Ensure-Image "nginx:1.27-alpine"
Ensure-Image "python:3.12-slim"
Ensure-Image "node:20-alpine"

Write-Host "[4/4] Export to $Out..."
docker save -o $Out `
  "planopt/web:$Tag" `
  "planopt/frontend:$Tag" `
  "postgres:14" "redis:7" "nginx:1.27-alpine" "python:3.12-slim" "node:20-alpine" | Out-Null

Write-Host "Done: $Out"

