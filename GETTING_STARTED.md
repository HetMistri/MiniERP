# Getting Started — Mini ERP

From zero to running Odoo 18 with the Mini ERP module.

## Prerequisites

- **Python** 3.10+ (3.14 works)
- **Git**
- **Docker** (for PostgreSQL)
- 10 GB free disk

## 1. Clone

```bash
git clone https://github.com/HetMistri/MiniERP.git
cd MiniERP
```

## 2. Bootstrap

Run the setup script for your OS:

### Linux / macOS

```bash
cd custom_addons
chmod +x bootstrap.sh
./bootstrap.sh
```

### Windows (PowerShell 7+)

```powershell
cd custom_addons
.\bootstrap.ps1
```

### What bootstrap does

1. Checks prerequisites (Python, Git, Docker)
2. Clones Odoo 18.0 source into `odoo/`
3. Creates config files: `odoo.conf`, `docker-compose.yaml` (skip if exist)
4. Creates Python virtual environment in `venv/`
5. Installs Odoo Python dependencies
6. Installs Odoo as an editable package
7. Starts PostgreSQL via Docker

> **Already set up?** Skip to step 3. You only need `docker compose up` in the project root and a venv with Odoo deps.

## 3. Start PostgreSQL

```bash
docker compose up -d
```

This starts PostgreSQL 15 on port 5432. The `init.sql` script runs automatically on first start, creating the `mini_erp` database and granting permissions.

### Reset the database

To wipe all data and start fresh:

```bash
docker compose down -v && docker compose up -d
```

## 4. Activate the virtual environment

```bash
source venv/bin/activate        # Linux / macOS
.\venv\Scripts\Activate.ps1     # Windows PowerShell
```

## 5. Initialize the database

This installs the `mini_erp` module and creates all tables:

```bash
python odoo/odoo-bin -c odoo.conf -d mini_erp -i mini_erp --stop-after-init
```

## 6. Run Odoo

```bash
python odoo/odoo-bin -c odoo.conf -d mini_erp
```

Once running, open **http://localhost:8069** — login with `admin` / `admin`.

## Quick Start (after first setup)

```bash
docker compose up -d                     # Start PostgreSQL
source venv/bin/activate                 # Activate venv
python odoo/odoo-bin -c odoo.conf        # Start Odoo server
```

## Project Structure

```
MiniERP/
├── custom_addons/        # Mini ERP Odoo module (versioned)
│   └── mini_erp/         # The module itself (models, views, etc.)
├── odoo/                 # Odoo 18 source (not versioned)
├── venv/                 # Python virtual environment (not versioned)
├── odoo.conf             # Odoo configuration
├── docker-compose.yaml   # PostgreSQL container
├── init.sql              # DB bootstrap (creates mini_erp database)
├── schema.sql            # Full data model reference (documentation only)
└── GETTING_STARTED.md    # This file
```

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `database "odoo" does not exist` | Add `db_name = mini_erp` to `odoo.conf` |
| `FATAL: database "mini_erp" does not exist` | Run `docker compose down -v && docker compose up -d` |
| Port 8069 already in use | Change `xmlrpc_port` in `odoo.conf` or kill the other process |
| `wkhtmltopdf` missing | Install it for PDF reports, or ignore if not needed |
| Module not found | Ensure `custom_addons` is in `addons_path` in `odoo.conf` |
