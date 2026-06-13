param()

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== Mini ERP — Starting PostgreSQL ===" -ForegroundColor Green
docker compose up -d

# Get container ID for postgres service
$PostgresContainer = docker compose ps -q postgres

if (-not $PostgresContainer) {
    Write-Host "Could not find PostgreSQL container." -ForegroundColor Red
    exit 1
}

Write-Host "Waiting for PostgreSQL to become ready..." -ForegroundColor Yellow

$MaxRetries = 60
$Retry = 0

while ($Retry -lt $MaxRetries) {
    try {
        docker exec $PostgresContainer pg_isready -U odoo *> $null

        if ($LASTEXITCODE -eq 0) {
            Write-Host "PostgreSQL is ready." -ForegroundColor Green
            break
        }
    }
    catch {
        # Container may still be starting
    }

    Start-Sleep -Seconds 1
    $Retry++
}

if ($Retry -eq $MaxRetries) {
    Write-Host "Timed out waiting for PostgreSQL." -ForegroundColor Red

    Write-Host ""
    Write-Host "Container logs:" -ForegroundColor Yellow
    docker logs $PostgresContainer

    exit 1
}

Write-Host ""
Write-Host "=== Mini ERP — Starting Odoo ===" -ForegroundColor Green
Write-Host "Using virtual environment: $ScriptDir\venv" -ForegroundColor Green

& "$ScriptDir\venv\Scripts\python.exe" odoo/odoo-bin -c odoo.conf @args