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
