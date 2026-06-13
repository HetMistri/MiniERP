param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "=== Mini ERP — Starting PostgreSQL ===" -ForegroundColor Green
docker compose up -d
Write-Host "PostgreSQL is running on port 5432" -ForegroundColor Green

Write-Host "" -NoNewline
Write-Host "=== Mini ERP — Starting Odoo ===" -ForegroundColor Green
Write-Host "Using virtual environment: $ScriptDir\venv" -ForegroundColor Green

& "$ScriptDir\venv\Scripts\python.exe" odoo/odoo-bin -c odoo.conf @args
