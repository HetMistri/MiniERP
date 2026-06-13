#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Mini ERP — Starting PostgreSQL ==="
docker compose up -d

echo "Waiting for PostgreSQL..."

until docker exec minierp_postgres pg_isready -U odoo >/dev/null 2>&1
do
    sleep 1
done

echo "PostgreSQL is ready"

echo ""
echo "=== Mini ERP — Starting venv ==="

source "$SCRIPT_DIR/.venv/bin/activate"
echo "Virtual environment activated"

echo ""
echo "=== Mini ERP — Starting Odoo ==="
echo "Using virtual environment: $SCRIPT_DIR/.venv"
"$SCRIPT_DIR/.venv/bin/python" odoo/odoo-bin -c odoo.conf "$@"
