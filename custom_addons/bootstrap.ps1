# Mini ERP - Windows Bootstrap Script
# Run this from the custom_addons directory (where this script lives)
# PowerShell 7+ recommended

$ErrorActionPreference = "Stop"
$ProjectDir = Split-Path -Parent $PSScriptRoot
$ScriptDir = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Mini ERP Bootstrap - Windows Setup    " -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Project root: $ProjectDir" -ForegroundColor Green

# --- Step 1: Prerequisites check ---
Write-Host "`n[1/6] Checking prerequisites..." -ForegroundColor Yellow

$hasDocker = Get-Command docker -ErrorAction SilentlyContinue
$hasPython = Get-Command python -ErrorAction SilentlyContinue
$hasGit = Get-Command git -ErrorAction SilentlyContinue

if (-not $hasPython) {
    Write-Host "ERROR: Python 3.11+ is required. Install from https://www.python.org/downloads/" -ForegroundColor Red
    Write-Host "Make sure 'Add Python to PATH' is checked during installation." -ForegroundColor Red
    exit 1
}

$pyVersion = python --version
Write-Host "  [OK] $pyVersion" -ForegroundColor Green

if (-not $hasGit) {
    Write-Host "ERROR: Git is required. Install from https://git-scm.com/download/win" -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Git" -ForegroundColor Green

if (-not $hasDocker) {
    Write-Host "  [WARN] Docker not found. PostgreSQL will need manual setup." -ForegroundColor Yellow
    Write-Host "    Install Docker Desktop: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
    $useDocker = $false
} else {
    Write-Host "  [OK] Docker" -ForegroundColor Green
    $useDocker = $true
}

# --- Step 2: Clone Odoo 18 source ---
Write-Host "`n[2/6] Setting up Odoo 18 source..." -ForegroundColor Yellow
$odooDir = Join-Path $ProjectDir "odoo"

if (Test-Path $odooDir) {
    Write-Host "  [OK] Odoo source already exists at: $odooDir" -ForegroundColor Green
} else {
    Write-Host "  Cloning Odoo 18 (this may take a while)..." -ForegroundColor Yellow
    git clone --depth 1 --branch 18.0 https://github.com/odoo/odoo.git $odooDir
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Failed to clone Odoo. Check your internet connection." -ForegroundColor Red
        exit 1
    }
    Write-Host "  [OK] Odoo 18 cloned" -ForegroundColor Green
}

# --- Step 3: Create project config files ---
Write-Host "`n[3/6] Creating project config files..." -ForegroundColor Yellow

$configPath = Join-Path $ProjectDir "odoo.conf"
if (-not (Test-Path $configPath)) {
    $cfg = @"
[options]
admin_passwd = admin
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
db_name = mini_erp
addons_path = $($odooDir -replace '\\', '/')/odoo/addons,$($odooDir -replace '\\', '/')/addons,$($ScriptDir -replace '\\', '/')
debug_mode = True
max_cron_threads = 0
"@
    Set-Content -Path $configPath -Value $cfg
    Write-Host "  [OK] odoo.conf created" -ForegroundColor Green
} else {
    Write-Host "  [OK] odoo.conf already exists" -ForegroundColor Green
}

$dcPath = Join-Path $ProjectDir "docker-compose.yaml"
if ($useDocker -and -not (Test-Path $dcPath)) {
    $dc = @"
services:
  db:
    image: postgres:15
    container_name: minierp_postgres
    environment:
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
      - POSTGRES_DB=postgres
    ports:
      - "5432:5432"
    volumes:
      - minierp_db_data:/var/lib/postgresql/data
      - ./init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  minierp_db_data:
"@
    Set-Content -Path $dcPath -Value $dc
    Write-Host "  [OK] docker-compose.yaml created" -ForegroundColor Green
} elseif ($useDocker) {
    Write-Host "  [OK] docker-compose.yaml already exists" -ForegroundColor Green
}

$initPath = Join-Path $ProjectDir "init.sql"
if (-not (Test-Path $initPath)) {
    Write-Host "  [WARN] init.sql not found. It should be committed to the repo." -ForegroundColor Yellow
    Write-Host "    Run: git checkout -- init.sql" -ForegroundColor Yellow
} else {
    Write-Host "  [OK] init.sql found" -ForegroundColor Green
}

# --- Step 4: Python virtual environment ---
Write-Host "`n[4/6] Setting up Python virtual environment..." -ForegroundColor Yellow
$venvDir = Join-Path $ProjectDir "venv"

if (Test-Path $venvDir) {
    Write-Host "  [OK] Virtual environment already exists" -ForegroundColor Green
} else {
    python -m venv $venvDir
    Write-Host "  [OK] Virtual environment created" -ForegroundColor Green
}

# --- Step 5: Install Python dependencies ---
Write-Host "`n[5/6] Installing Python dependencies..." -ForegroundColor Yellow
$pip = Join-Path $venvDir "Scripts\pip.exe"
$reqFile = Join-Path $odooDir "requirements.txt"

if ((Test-Path $pip) -and (Test-Path $reqFile)) {
    Write-Host "  Installing Odoo requirements (this may take a while)..." -ForegroundColor Yellow
    & $pip install --no-cache-dir -r $reqFile
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Python dependencies installed" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Some packages may have failed. Check errors above." -ForegroundColor Yellow
    }

    $escapedOdooDir = $odooDir -replace '\\', '/'
    Write-Host "  Installing Odoo package (editable)..." -ForegroundColor Yellow
    & $pip install --no-cache-dir --no-deps -e $escapedOdooDir
    Write-Host "  [OK] Odoo package installed (editable)" -ForegroundColor Green
} else {
    Write-Host "  [WARN] Cannot find pip or requirements.txt. Install manually:" -ForegroundColor Yellow
    Write-Host "    $pip install -r $reqFile" -ForegroundColor Yellow
    Write-Host "    $pip install --no-deps -e $odooDir" -ForegroundColor Yellow
}

# --- Step 6: Start PostgreSQL via Docker ---
Write-Host "`n[6/6] Starting PostgreSQL..." -ForegroundColor Yellow
if ($useDocker) {
    Push-Location $ProjectDir
    & docker compose up -d
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] PostgreSQL started on localhost:5432" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] Docker start failed. Make sure Docker Desktop is running." -ForegroundColor Yellow
    }
    Pop-Location
} else {
    Write-Host "  [WARN] Skipped. Start PostgreSQL manually or install Docker Desktop." -ForegroundColor Yellow
    Write-Host "    Docker Desktop: https://docs.docker.com/desktop/install/windows-install/" -ForegroundColor Yellow
}

# --- Complete ---
Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Bootstrap Complete!" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Green
Write-Host ""
Write-Host "  1. Activate the virtual environment:"
Write-Host "     .\venv\Scripts\activate"
Write-Host ""
Write-Host "  2. Start Odoo (initialize database):"
Write-Host "     python odoo/odoo-bin -c odoo.conf -d mini_erp -i mini_erp --stop-after-init"
Write-Host ""
Write-Host "  3. Run Odoo server:"
Write-Host "     python odoo/odoo-bin -c odoo.conf -d mini_erp"
Write-Host ""
Write-Host "  4. Open http://localhost:8069 - login: admin / admin"
Write-Host ""
