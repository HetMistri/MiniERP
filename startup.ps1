# MiniERP startup script (Windows PowerShell)
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir
& ".\venv\Scripts\Activate.ps1"
& python odoo/odoo-bin -c odoo.conf @args
