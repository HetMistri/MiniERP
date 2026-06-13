# Stream A — Core Foundation & Product Management

## Focus
Module scaffolding, security model, user/group management, audit log engine, and the complete Product module with inventory tracking.

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

### Phase A2 — Audit Log Engine ✅

- [x] Create `audit.log` model with all required fields, Reference field, display_name, IP tracking
- [x] Create abstract mixin `audit.mixin` with `_audit_track_create()`, `_audit_track_write()`, `_audit_track_unlink()` helpers
- [x] Create tree/form/search views for `audit.log` — read-only, grouped by model/user/action, filterable by date
- [x] Add `audit.log` menu under `Settings / Audit Logs` (Admin only via `mini_erp.group_admin`)
- [x] Create access rule so only `group_admin` can read audit logs (ir.model.access.csv)
- [x] Register audit hook helpers ready for integration with core models via mixin inheritance

---

### Phase A3 — Product Master Model ✅

- [x] Create `product.product` model with all fields: name, reference (auto-sequence via ir.sequence), sale_price, cost_price, uom_id, product_type, on_hand_qty (computed→0, Phase A5), reserved_qty (computed→0, Phase B2/C5), free_to_use_qty (computed), active
- [x] Create `product.category` model with: name, parent_id (hierarchical), parent_path, child_ids, description, complete_name (computed)
- [x] Add `category_id` (Many2one) to `product.product`
- [x] Create `product.uom` model (name, code, active)
- [x] Create `product.quantity.history` model for stock snapshots
- [x] Stub implementations for `_compute_on_hand_qty` / `_compute_reserved_qty` — return 0 pending Stock Ledger (Phase A5)
- [x] Demo data: 4 UoMs, 4 categories, 5 products (Wooden Table, Office Chair, Dining Table, Wooden Legs, Screws)
- [x] Audit mixin integrated — all product create/write/unlink tracked automatically

---

### Phase A4 — Product Views, Menus & Access

- [ ] Create tree view for `product.product` with all key fields
- [ ] Create form view with notebook:
  - Page 1: General Info (name, reference, category, UoM, type, prices)
  - Page 2: Inventory (on-hand, reserved, free-to-use — all read-only)
  - Page 3: Procurement Settings (Procure on Demand, Procurement Type, Vendor, BoM)
- [ ] Create search view with filters (type, category, low-stock, active/inactive)
- [ ] Create `product.category` tree + form views
- [ ] Add menus: `Products / Products`, `Products / Categories`, `Products / Inventory Dashboard`
- [ ] Assign menu access by group (Admin + Business Owner + Inventory Manager see all; Sales/Purchase users see read-only)
- [ ] Create demo data: 5 products (Wooden Table, Office Chair, Dining Table, Wooden Legs, Screws)

---

### Phase A5 — Stock Ledger Engine

- [ ] Create `stock.ledger` model (`_name = 'stock.ledger'`):
  - `product_id` (Many2one → product.product)
  - `reference` (Char: SOxxx, POxxx, MOxxx)
  - `transaction_type` (Selection: *Sale Delivery*, *Purchase Receipt*, *Manufacture In*, *Manufacture Out*, *Initial*, *Adjustment*)
  - `quantity` (Float, signed: + for inbound, — for outbound)
  - `balance_after` (Float)
  - `date` (Datetime, default=now)
  - `user_id`
- [ ] Create `stock.ledger` tree view (read-only, grouped by product, ordered by date desc)
- [ ] Add `stock.ledger` menu under `Products / Stock Ledger` (Inventory Manager + Admin only)
- [ ] Create helper method `_update_stock(product_id, qty, reference, type)` that writes ledger and updates product `on_hand_qty`

---

### Phase A6 — Currency & Company Settings

- [ ] Define company currency (Monetary fields rely on this)
- [ ] Create/resue `res.currency` if not already available via `base` module
- [ ] Set default company in demo data
- [ ] Ensure all monetary fields use `currency_id` as related from company
