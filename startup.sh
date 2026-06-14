#!/bin/bash
# MiniERP startup script (Linux/Mac)
cd "$(dirname "$0")" || exit 1
source venv/bin/activate
exec python odoo/odoo-bin -c odoo.conf "$@"
