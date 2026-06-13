# Stream A — Core Foundation & Product Management

## Focus
Module scaffolding, security model, user/group management with per-module CRUD, audit log engine, and the complete Product module with inventory tracking.

---

### Phase A1 — Project Scaffold & Security Foundation ✅

- [x] Create Odoo module `mini_erp` with `__manifest__.py` (name, description, depends, data keys)
- [x] Define security groups in XML:
  - `group_admin` — full access
  - `group_sales_user` — sales module access
  - `group_purchase_user` — purchase module access
  - `group_manufacturing_user` — manufacturing access
  - `group_inventory_manager` — stock movement access
  - `group_business_owner` — read-only dashboard & product visibility
- [x] Create `security/ir.model.access.csv` with row-level permissions for all groups per model
- [x] Create `security/security.xml` for group/category definitions
- [x] Create base `ir.sequence` for all document numbering (SO, PO, MO, BO)
- [x] Set up `__init__.py`, `models/__init__.py`, `controllers/__init__.py`
- [x] Add module category and icon

---

### Phase A1b — User Management (Admin CRUD + Per-Module Access Matrix) ✅

- [x] Extend `res.users` with `position` (Char) field
- [x] Add `mobile` field to user form view (inherited from `res.partner`)
- [x] Photo/avatar covered by existing `image_1920` field shown as `oe_avatar` in base form
- [x] Create inherited user form view (`base.view_users_form` inheritance) with Module Access page
- [x] Per-module access matrix on user form via `many2many_tags` + `many2many_checkboxes` widgets
- [x] Permission guide for each role
- [x] Uses standard Settings / Users menu (Admin only access via `group_admin`)

---

### Phase A2 — Audit Log Engine ✅

- [x] Create `audit.log` model with all required fields, Reference field, display_name, IP tracking
- [x] Create abstract mixin `audit.mixin` with `_audit_track_create()`, `_audit_track_write()`, `_audit_track_unlink()` helpers
- [x] Create tree/form/search views for `audit.log` — read-only, grouped by model/user/action, filterable by date
- [x] Add `audit.log` menu under `Settings / Audit Logs` (Admin only via `mini_erp.group_admin`)
- [x] Create access rule so only `group_admin` can read audit logs (ir.model.access.csv)
- [x] Register audit hook helpers ready for integration with core models via mixin inheritance

> **Out of scope for Stream A** (belongs to Stream D or future enhancement):
> - KPI banner with Records Created/Updated/Deleted/Total counts
> - Filter bar with Date Range picker, User/Module/Action dropdowns
> - Dashboard-level pagination with page buttons

---

### Phase A3 — Product Master Model ✅

- [x] Create `product.product` model with all fields: name, reference (auto-sequence via ir.sequence), sale_price, cost_price, uom_id, product_type, on_hand_qty (computed), reserved_qty (computed), free_to_use_qty (computed), active
- [x] Create `product.category` model with: name, parent_id (hierarchical), parent_path, child_ids, description, complete_name (computed)
- [x] Add `category_id` (Many2one) to `product.product`
- [x] Create `product.uom` model (name, code, active)
- [x] Create `product.quantity.history` model for stock snapshots
- [x] Computed quantity fields (on-hand from ledger, reserved from SO+MO, free-to-use = on-hand − reserved)
- [x] Demo data: 4 UoMs, 4 categories, 5 products (Wooden Table, Office Chair, Dining Table, Wooden Legs, Screws)
- [x] Audit mixin integrated — all product create/write/unlink tracked automatically
- [x] Procurement settings fields on product (Procure on Demand, Type, Vendor, BoM, Min Stock, Lead Time)

---

### Phase A4 — Product Views, Menus & Access ✅

- [x] Create tree view for `product.product` with all key fields
- [x] Create form view with notebook:
  - Page 1: General Info (name, reference, category, UoM, type, prices)
  - Page 2: Inventory (on-hand, reserved, free-to-use — all read-only)
  - Page 3: Procurement Settings (Procure on Demand, Procurement Type, Vendor, BoM)
- [x] Create search view with filters (type, category, low-stock, active/inactive)
- [x] Create `product.category` tree + form views
- [x] Add menus: `Mini ERP / Products / Products`, `Mini ERP / Products / Categories`, `Mini ERP / Products / Units of Measure`, `Mini ERP / Products / Stock Ledger`
- [x] Assign menu access by group (internal users via `base.group_user`)
- [x] Create demo data: 5 products, 4 UoMs, 4 categories
- [x] Add **"Logs"** button on product form header that opens audit logs filtered to Product module (Admin only)
- [ ] Smart buttons (Manufacturing n, Sales n, Purchase n) — deferred to Streams B/C

> **Inventory Dashboard** deferred to Phase D.

---

### Phase A5 — Stock Ledger Engine ✅

- [x] Create `stock.ledger` model (`_name = 'stock.ledger'`):
  - `product_id` (Many2one → product.product)
  - `reference` (Char: SOxxx, POxxx, MOxxx)
  - `transaction_type` (Selection: *Sale Delivery*, *Purchase Receipt*, *Manufacture In*, *Manufacture Out*, *Initial*, *Adjustment*)
  - `quantity` (Float, signed)
  - `balance_after` (Float)
  - `date` (Datetime, default=now)
  - `user_id`
- [x] Create read-only tree view grouped by product, ordered by date desc
- [x] Add `stock.ledger` menu under `Products / Stock Ledger` (Admin + Inventory Manager only)
- [x] Create helper method `_update_stock(product_id, qty, reference, type)` — writes ledger entry, computes `balance_after`

---

### Phase A6 — Currency & Company Settings ✅

- [x] Monetary fields use `currency_id` related from `company_id.currency_id`
- [x] `res.currency` and `res.company` provided by `base` module
- [x] Default company and currency set automatically by Odoo's base module
