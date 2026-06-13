#!/usr/bin/env bash
set -euo pipefail

# Mini ERP — Linux/macOS Bootstrap Script
# Run from the custom_addons directory

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

echo "========================================"
echo "  Mini ERP Bootstrap"
echo "========================================"
echo ""
echo "Project root: $PROJECT_DIR"

# ─── Step 1: Prerequisites ───
echo ""
echo "[1/6] Checking prerequisites..."

if ! command -v python3 &>/dev/null && ! command -v python &>/dev/null; then
    echo "ERROR: Python 3.11+ is required."
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)
echo "  ✓ $($PYTHON --version)"

if ! command -v git &>/dev/null; then
    echo "ERROR: Git is required."
    exit 1
fi
echo "  ✓ Git"

USE_DOCKER=false
if command -v docker &>/dev/null; then
    USE_DOCKER=true
    echo "  ✓ Docker"
else
    echo "  ⚠ Docker not found. Install PostgreSQL manually."
fi

# ─── Step 2: Clone Odoo 18 ───
echo ""
echo "[2/6] Setting up Odoo 18 source..."
ODOO_DIR="$PROJECT_DIR/odoo"

if [ -d "$ODOO_DIR" ]; then
    echo "  ✓ Odoo source already exists at $ODOO_DIR"
else
    echo "  Cloning Odoo 18 (this may take a while)..."
    git clone --depth 1 --branch 18.0 https://github.com/odoo/odoo.git "$ODOO_DIR"
    echo "  ✓ Odoo 18 cloned"
fi

# ─── Step 3: Config files ───
echo ""
echo "[3/6] Creating project config files..."

if [ ! -f "$PROJECT_DIR/odoo.conf" ]; then
    cat > "$PROJECT_DIR/odoo.conf" << ODOOCFG
[options]
admin_passwd = admin
db_host = localhost
db_port = 5432
db_user = odoo
db_password = odoo
addons_path = $ODOO_DIR/addons,$SCRIPT_DIR
debug_mode = True
max_cron_threads = 0
ODOOCFG
    echo "  ✓ odoo.conf created"
else
    echo "  ✓ odoo.conf already exists"
fi

if [ "$USE_DOCKER" = true ] && [ ! -f "$PROJECT_DIR/docker-compose.yaml" ]; then
    cat > "$PROJECT_DIR/docker-compose.yaml" << DOCKERCOMPOSE
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
      - ./init-db.sql:/docker-entrypoint-initdb.d/init-db.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U odoo"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  minierp_db_data:
DOCKERCOMPOSE
    echo "  ✓ docker-compose.yaml created"
fi

if [ "$USE_DOCKER" = true ] && [ ! -f "$PROJECT_DIR/init-db.sql" ]; then
    cat > "$PROJECT_DIR/init-db.sql" << INITSQL
CREATE DATABASE mini_erp OWNER odoo;
ALTER USER odoo CREATEDB;
INITSQL
    echo "  ✓ init-db.sql created"
fi

# ─── Step 4: Virtual environment ───
echo ""
echo "[4/6] Setting up Python virtual environment..."
VENV_DIR="$PROJECT_DIR/venv"
if [ ! -d "$VENV_DIR" ]; then
    $PYTHON -m venv "$VENV_DIR"
    echo "  ✓ Virtual environment created"
else
    echo "  ✓ Virtual environment already exists"
fi

# ─── Step 5: Install dependencies ───
echo ""
echo "[5/6] Installing Python dependencies..."
PIP="$VENV_DIR/bin/pip"

if [ -f "$ODOO_DIR/requirements.txt" ]; then
    echo "  Installing Odoo requirements..."
    $PIP install --no-cache-dir -r "$ODOO_DIR/requirements.txt"
    echo "  ✓ Python dependencies installed"

    echo "  Installing Odoo package (editable)..."
    $PIP install --no-cache-dir --no-deps -e "$ODOO_DIR"
    echo "  ✓ Odoo package installed"
else
    echo "  ⚠ requirements.txt not found at $ODOO_DIR"
fi

# ─── Step 6: Start PostgreSQL ───
echo ""
echo "[6/6] Starting PostgreSQL..."
if [ "$USE_DOCKER" = true ]; then
    cd "$PROJECT_DIR"
    docker compose up -d
    echo "  ✓ PostgreSQL started on localhost:5432"
else
    echo "  ⚠ Skipped. Start PostgreSQL manually."
fi

# ─── Done ───
echo ""
echo "========================================"
echo "  Bootstrap Complete!"
echo "========================================"
echo ""
echo "Next steps:"
echo ""
echo "  1. Activate the virtual environment:"
echo "     source $PROJECT_DIR/venv/bin/activate"
echo ""
echo "  2. Initialize database:"
echo "     python odoo/odoo-bin -c odoo.conf -d mini_erp -i mini_erp --stop-after-init"
echo ""
echo "  3. Run Odoo:"
echo "     python odoo/odoo-bin -c odoo.conf -d mini_erp"
echo ""
echo "  4. Open http://localhost:8069 — login: admin / admin"
echo ""
