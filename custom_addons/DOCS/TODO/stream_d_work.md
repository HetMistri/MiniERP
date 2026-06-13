# Stream D Work Log — Procurement Automation, Dashboard & Integration

## Phase D1 — Procurement Configuration on Product

### 1. Work Done
- **Res Partner Extension:** Created `models/partner.py` which inherits from Odoo's core `res.partner`. Added `partner_type`, `is_customer`, and `is_vendor` fields. This maps perfectly to the Postgres table columns defined in the bootstrap schema (`schema.sql`).
- **MRP BOM Model Creation:** Created `models/mrp_bom.py` defining the `mrp.bom` Odoo model with `name`, `product_id`, `product_qty`, `active`, and `notes` fields. Inherited `audit.mixin` to enable automated creation, modification, and deletion logs for BoM records. Added sequence auto-generation logic for the `name` field using the `mrp.bom` sequence code defined in Odoo sequences data.
- **Product Model Extension:** Modified `models/product.py` to add procurement options to `product.product`:
  - `procure_on_demand` (Boolean) - enable auto-replenishment (MTO/MTS trigger)
  - `procurement_type` (Selection) - `manufacture` or `purchase`
  - `vendor_id` (Many2one -> `res.partner` with domain filter `is_vendor = True`)
  - `bom_id` (Many2one -> `mrp.bom` specifying the recipe for manufacturing)
  - `min_stock_qty` (Float) - reordering threshold qty
  - `lead_time_days` (Integer) - default to 1 day lead time
- **Views Integration:** Added the new notebook page `"Procurement Settings"` on the product form view (`views/product_views.xml`). Configured dynamic group/field visibility using Odoo 18 client-side expressions:
  - `procurement_type` only shows if `procure_on_demand` is enabled.
  - `vendor_id` (Purchase Details) only shows and becomes required if `procure_on_demand` is true and `procurement_type == 'purchase'`.
  - `bom_id` (Manufacturing Details) only shows and becomes required if `procure_on_demand` is true and `procurement_type == 'manufacture'`.
- **Security Access:** Defined a default full-access rule for `mrp.bom` in `security/ir.model.access.csv`.

---

### 2. Tech Stack & Odoo 18 Framework Logic
- **Odoo ORM / API:** Inherited `audit.mixin` on `mrp.bom` for automatic lifecycle logging, matching existing module audit logs pattern.
- **Dynamic Views:** Used Odoo 18's python-style conditional logic in views (e.g. `invisible="not procure_on_demand"` and `required="procure_on_demand and procurement_type == 'purchase'"`).
- **Sequences:** Utilized `self.env['ir.sequence'].next_by_code('mrp.bom')` to assign automatic sequence IDs on record creation.

---

## Phase D2 — Procurement Engine (Core Logic)

### 1. Work Done
- **Python Models Definitions for DB Mapping:** Created the following Odoo models in python corresponding to PG tables:
  - `mrp.bom.component` (in `models/mrp_bom.py` with One2many link on `mrp.bom`)
  - `mrp.work.center`, `mrp.work.order`, `mrp.production` (MO), and `mrp.production.component` (in `models/mrp.py`)
  - `purchase.order`, `purchase.order.line` (in `models/purchase.py`)
  - `sale.order`, `sale.order.line` (in `models/sale.py`)
- **Product Model Field Updates:** Changed quantity fields (`on_hand_qty`, `reserved_qty`, and `free_to_use_qty`) in `product.product` to standard fields instead of computed fields, so that Odoo reads them directly from the database columns populated by PG triggers.
- **Procurement Manager Implementation:** Created `models/procurement.py` with the abstract model `procurement.manager`.
  - Implemented `evaluate(product, required_qty, origin)` to compute shortage against `free_to_use_qty`.
  - Implemented `_create_purchase_order` to create Draft POs for configured vendors.
  - Implemented `_create_manufacturing_order` to create Draft MOs, explode the BoM components into the MO component list, and recursively execute `evaluate` on any components that have MTO (`procure_on_demand`) enabled (cascading procurement).
  - Added checks to prevent duplicate procurement if a draft document with the same product and origin already exists.
- **Security Mapping:** Added access permissions in `security/ir.model.access.csv` for all the new models.

### 2. Tech Stack & Odoo 18 Framework Logic
- **Odoo ORM Database Mappings:** Mapped Odoo Python classes exactly to the pre-existing SQL tables and constraints (e.g. `name` fields automatically fetching sequence values, relations, constraints, and currency fields).
- **Recursion & Search API:** Leveraged `self.env[model].search(...)` to prevent duplicate document generation and recursively trigger cascading procurement for sub-assembly components during BOM explosion.

