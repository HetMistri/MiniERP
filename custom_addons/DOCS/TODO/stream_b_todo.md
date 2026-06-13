# Stream B — Sales & Purchase Management

## Focus
Partner management, complete Sales Order lifecycle, Purchase Order lifecycle, delivery/receipt workflows, and integration with Product inventory.

---

### Phase B1 — Partner / Contact Base

- [x] Create `res.partner` extension (inherit `res.partner`):
  - `is_customer` (Boolean)
  - `is_vendor` (Boolean)
  - `partner_type` (Selection: *Individual*, *Company*)
  - Inherit `phone`, `email`, `street`, `city`, etc. from base `res.partner`
- [x] Create tree and form views for partners with customer/vendor filters
- [x] Create `partner` menu under `Sales / Customers` and `Purchase / Vendors`
- [x] Demo data: 2 customers (Suzuki India, MRF Ltd), 2 vendors (Plastofact IN, ORM Metals) — matching SVG mockup sample names

---

### Phase B2 — Sales Order Model

- [x] Create `sale.order` model (`_name = 'sale.order'`):
  - `name` (Char, sequence-generated, eg. SO-000001)
  - `partner_id` (Many2one → res.partner, domain = is_customer=True, mandatory)
  - `partner_address` (Char, max limit — stored separately per mockup)
  - `state` (Selection: *Draft → Confirmed → Partially Delivered → Fully Delivered → Cancelled*)
  - `order_line` (One2many → sale.order.line)
  - `date_order` (Datetime, default=now, auto-computed)
  - `total_amount` (Monetary, computed = sum of line subtotals, auto-recomputed)
  - `user_id` (Salesperson — Many2one → res.users, dropdown)
  - `notes` (Text)
- [x] Create `sale.order.line` model:
  - `order_id` (Many2one → sale.order)
  - `product_id` (Many2one → product.product, dropdown from product DB, track logs)
  - `description` (Text)
  - `quantity` (Float, required)
  - `delivered_qty` (Float, default=0)
  - `reserved_qty` (Float, default=0)
  - `price_unit` (Monetary, default from product.sale_price, track logs)
  - `subtotal` (Monetary, computed = qty × price_unit)
  - `stock_availability` (Char, computed — shows if Ordered Qty > Free to Use Qty)

---

### Phase B3 — Sales Order Workflow & Business Logic

- [x] **Confirm action**: `action_confirm()`
  - Validate partner and lines
  - Check product availability (free-to-use vs ordered)
  - Set `reserved_qty` on lines equal to `quantity`
  - Update each product's `reserved_qty`
  - Transition state → *Confirmed*
  - Trigger procurement evaluation (see Stream D integration)
- [x] **Deliver action**: `action_deliver()`
  - Open delivery wizard (form with delivered quantities per line)
  - On validate: write `stock.ledger` entries (— for each product), update `delivered_qty`
  - If all lines delivered → *Fully Delivered*
  - If partial → *Partially Delivered*
- [x] **Cancel action**: `action_cancel()`
  - Release reserved quantities back to free-to-use
  - Make all fields readonly
  - Transition → *Cancelled*
  - Track audit log
- [x] **On unlink restriction**: Prevent deletion of non-Draft orders
- [x] Create `_update_reserved_qty(product_id, delta)` helper used across SO/MO
- [x] Create delivery wizard model `sale.order.deliver`:
  - `order_id`, `line_ids` (One2many → deliver.line with `product_id`, `qty_delivered`, `qty_ordered`)
  - `action_validate()` — writes ledger and updates SO lines

---

### Phase B4 — Sales Order Views & Menus

> **SVG Mockup specifies:**
> - List View columns: Reference, Date, Customer, Status, Salesperson
> - Form View: Customer (many2one mandatory), Customer Address (Char max limit), Creation Date (auto), Sales Person (users dropdown)
> - Products table: Product, Availability, Ordered Qty, Unit, Sales Unit Price, Delivered Qty, Total
> - Buttons: Back, Confirm, Deliver, Cancel (context-dependent)
> - Cancel → all fields readonly
> - **"Logs" button** on form header → opens audit logs filtered by module "Sales"
> - Kanban view by status (Draft → Confirmed → Delivering → Done)
> - Search bar allows search by reference & contacts
> - "New" button creates order in Draft status

- [x] Tree view for SO: reference, partner, date, state, total, salesperson
- [x] Form view with notebook:
  - Page 1: Order Lines (editable tree with product, availability, qty, price, delivered, total)
  - Page 2: Delivery / Status (read-only delivery tracking)
  - Page 3: Notes
- [x] Kanban view: columns by state (Draft → Confirmed → Delivering → Done)
- [x] Search view: filter by state, partner, date range, reference
- [x] Action buttons in header: **Confirm**, **Deliver**, **Cancel** (context-dependent)
- [x] **"Logs" button** — opens `audit.log` tree view filtered by module = "Sales"
- [x] Smart buttons (deferred until Stream C/D): `Purchase Orders (n)`
- [x] Menu: `Sales / Sales Orders`, `Sales / Customers`
- [x] Access: `group_sales_user` full CRUD; `group_business_owner` read-only
- [x] Demo data: 2 sales orders — one Draft (SO-000001), one Confirmed (SO-000002) — matching mockup sample

---

### Phase B5 — Purchase Order Model

- [x] Create `purchase.order` model (`_name = 'purchase.order'`):
  - `name` (Char, sequence-generated, eg. PO-000001)
  - `partner_id` (Many2one → res.partner, domain = is_vendor=True, mandatory)
  - `partner_address` (Char, max limit — stored separately per mockup)
  - `state` (Selection: *Draft → Confirmed → Partially Received → Fully Received*)
  - `order_line` (One2many → purchase.order.line)
  - `date_order` (Datetime, auto-computed)
  - `total_amount` (Monetary, computed)
  - `user_id` (Responsible Person — Many2one → res.users, dropdown)
  - `notes`
- [x] Create `purchase.order.line` model:
  - `order_id` (Many2one)
  - `product_id`
  - `description`
  - `quantity` (Float, required)
  - `received_qty` (Float, default=0)
  - `price_unit` (Monetary, default from product.cost_price, track logs)
  - `subtotal` (Monetary, computed)

---

### Phase B6 — Purchase Order Workflow & Business Logic

- [x] **Confirm action**: Validate, transition → *Confirmed*
- [x] **Receive action**: `action_receive()`
  - Receipt wizard with quantities per line
  - On validate: write `stock.ledger` entries (+ for each product), increase `on_hand_qty`
  - Update `received_qty` on each line
  - Transition → *Partially Received* or *Fully Received*
- [x] **Cancel action**: (only Draft/Confirmed allowed), make all fields readonly
- [x] Create purchase receipt wizard model `purchase.order.receive` similar to SO delivery

---

### Phase B7 — Purchase Order Views & Menus

> **SVG Mockup specifies:**
> - List View columns: Reference, Date, Vendor, Status, Responsible
> - Form View: Vendor (many2one mandatory), Vendor Address (Char max limit), Creation Date (auto), Responsible Person (users dropdown)
> - Products table: Product, Ordered Qty, Unit, Cost Unit Price, Received Qty, Total
> - Buttons: Back, Confirm, Received, Cancel (context-dependent)
> - Cancel → all fields readonly
> - **"Logs" button** on form header → opens audit logs filtered by module "Purchase"
> - Kanban view by status

- [x] Tree, form (notebook: lines, receipt status), search views
- [x] Kanban by state
- [x] Action buttons: **Confirm**, **Receive**, **Cancel**
- [x] **"Logs" button** — opens `audit.log` tree view filtered by module = "Purchase"
- [x] Menu: `Purchase / Purchase Orders`, `Purchase / Vendors`
- [x] Access: `group_purchase_user` full CRUD; `group_inventory_manager` read; `group_business_owner` read-only
- [x] Demo data: 1 PO in Draft (PO-000001 — Plastofact IN), 1 in Confirmed (PO-000002 — ORM Metals) — matching mockup sample

---

### Phase B8 — Sales ↔ Purchase Integration

- [x] Relate SO lines to automatically generated POs (via procurement)
- [x] Show procurement origin on PO (e.g. "Generated from SO-000001 — Dining Table x15")
- [x] Add smart button on SO form: `Purchase Orders` count
- [x] Add smart button on PO form: `Source Sales Orders` if applicable
