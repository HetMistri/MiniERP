# Mini ERP — custom_addons

Mini ERP System for "Shiv Furniture Works" — from Demand to Delivery.

## Setup

### Windows

Open **PowerShell** (7+ recommended) in the `custom_addons` directory and run:

```powershell
.\bootstrap.ps1
```

### Linux / macOS

```bash
chmod +x bootstrap.sh
./bootstrap.sh
```

> **Prerequisites**: Python 3.11+, Git, Docker Desktop (for PostgreSQL)

### What the bootstrap does

1. ⚠ Checks for Python, Git, Docker
2. 📦 Clones Odoo 18.0 source (if not present)
3. 🔧 Creates `odoo.conf`, `docker-compose.yaml`, `init-db.sql`
4. 🐍 Creates Python virtual environment (`venv/`)
5. 📥 Installs Odoo Python dependencies (`pip install -r requirements.txt`)
6. 🐘 Starts PostgreSQL via Docker

### Manual Start (after bootstrap)

```bash
# Activate venv
source venv/bin/activate          # Linux/macOS
.\venv\Scripts\Activate.ps1       # Windows PowerShell

# Init database (one time)
python odoo/odoo-bin -c odoo.conf -d mini_erp -i mini_erp --stop-after-init

# Run Odoo
python odoo/odoo-bin -c odoo.conf -d mini_erp
```

Open **http://localhost:8069** — login: `admin` / `admin`

## Module Structure

```
mini_erp/
├── __init__.py
├── __manifest__.py
├── models/          # Python models
├── views/           # XML views
├── security/        # Access rights & groups
├── data/            # Sequences, seed data
├── demo/            # Demo data
├── controllers/     # HTTP controllers
└── ... 
```

## Streams

| Stream | Area | Status |
|--------|------|--------|
| **A** | Core Foundation, Products, Audit | ✅ A1–A3 done |
| **B** | Sales & Purchase | ⏳ Not started |
| **C** | Manufacturing & BoM | ⏳ Not started |
| **D** | Procurement, Dashboard, Integration | ⏳ Not started |

See [DOCS/TODO/](DOCS/TODO/) for full task breakdown.
