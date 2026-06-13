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
if [ -d "$SCRIPT_DIR/venv/Scripts" ]; then
    source "$SCRIPT_DIR/venv/Scripts/activate"
    PYTHON_EXEC="$SCRIPT_DIR/venv/Scripts/python"
else
    source "$SCRIPT_DIR/venv/bin/activate"
    PYTHON_EXEC="$SCRIPT_DIR/venv/bin/python"
fi
echo "Virtual environment activated"

echo ""
echo "=== Mini ERP — Starting Odoo ==="
"$PYTHON_EXEC" odoo/odoo-bin -c odoo.conf "$@"
