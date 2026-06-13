# Stream A — Core Foundation & Product Management

## Focus
Module scaffolding, security model, user/group management with per-module CRUD, audit log engine with KPI dashboard, and the complete Product module with inventory tracking.

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

### Phase A1b — User Management (Admin CRUD + Per-Module Access Matrix) ⬜

> SVG Mockup shows a **System Administrator Dashboard** with user management where Admin manages:
> - User list (Mahesh Gupta, Nisarg Verma, Dinesh Patel, Sweta Kediva, Trisha K.)
> - User form: Name, Address, Position, Email ID, Mobile Number, Photo
> - Per-module CRUD matrix (Create/View/Edit/Delete for Sales, Purchase, Manufacturing, Product)
> - Email ID read-only (matches signup), Position editable only by Admin

- [ ] Create `res.users` extension (inherit) or standalone user management view:
  - `mobile` (Char)
  - `photo` (Binary — image)
  - `position` (Char) — editable only by Admin
- [ ] Create Admin-only user list view with search
- [ ] Create Admin-only user form view (Name, Address, Position, Email read-only, Mobile, Photo)
- [ ] Create per-module access matrix on user form:
  - Sales: Create/View/Edit/Delete checkboxes (maps to `group_sales_user` + finer controls)
  - Purchase: Create/View/Edit/Delete checkboxes
  - Manufacturing: Create/View/Edit/Delete checkboxes
  - Product: Create/View/Edit/Delete checkboxes
- [ ] Menu: `Settings / Users` (Admin only)

---

### Phase A2 — Audit Log Engine ⚠️

- [x] Create `audit.log` model with all required fields, Reference field, display_name, IP tracking
- [x] Create abstract mixin `audit.mixin` with `_audit_track_create()`, `_audit_track_write()`, `_audit_track_unlink()` helpers
- [x] Create tree/form/search views for `audit.log` — read-only, grouped by model/user/action, filterable by date
- [x] Add `audit.log` menu under `Settings / Audit Logs` (Admin only via `mini_erp.group_admin`)
- [x] Create access rule so only `group_admin` can read audit logs (ir.model.access.csv)
- [x] Register audit hook helpers ready for integration with core models via mixin inheritance

> **SVG Mockup enhancements needed:**
> - [ ] Add KPI banner at top: **Records Created** (n), **Records Updated** (n), **Records Deleted** (n), **Total Logs** (n)
> - [ ] Add filter bar: Date Range (picker), User (dropdown, default "All Users"), Module (dropdown, default "All Modules"), Actions (dropdown: All Actions / Create / Update / Delete) + Filter + Reset buttons
> - [ ] Add pagination footer: "100" per page with page number buttons (06 08 style)
> - [ ] Show date range context: e.g. "01 May 2026 - 26 May 2026"
> - [ ] Show "All time logs" summary section

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

### Phase A4 — Product Views, Menus & Access ⚠️

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

> **SVG Mockup enhancements needed (product form):**
> - [ ] Add **"Logs"** button/link on product form header that opens audit logs filtered to Product module
> - [ ] Add smart buttons on product form: Manufacturing (n), Sales (n), Purchase (n) — deferred until Streams B/C exist

> **Inventory Dashboard** deferred to Phase D (dashboard engine).

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
