#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "=== Mini ERP — Starting PostgreSQL ==="
docker compose up -d
echo "PostgreSQL is running on port 5432"

echo ""
echo "=== Mini ERP — Starting Odoo ==="
echo "Using virtual environment: $SCRIPT_DIR/venv"
"$SCRIPT_DIR/venv/bin/python" odoo/odoo-bin -c odoo.conf "$@"
