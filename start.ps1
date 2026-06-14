# Mini ERP — Windows Startup Script
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

Write-Host "=== Mini ERP — Starting PostgreSQL ==="
docker compose up -d

Write-Host "Waiting for PostgreSQL..."
do {
    Start-Sleep -Seconds 1
} until (docker exec minierp_postgres pg_isready -U odoo 2>$null)

Write-Host "PostgreSQL is ready"
Write-Host ""
Write-Host "=== Mini ERP — Starting Odoo ==="
& ".\venv\Scripts\python.exe" odoo/odoo-bin -c odoo.conf @args
