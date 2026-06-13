# Stream B — Sales & Purchase Management

## Focus
Partner management, complete Sales Order lifecycle, Purchase Order lifecycle, delivery/receipt workflows, and integration with Product inventory.

---

### Phase B1 — Partner / Contact Base

- [ ] Create `res.partner` extension (inherit `res.partner`) or use base:
  - Add `is_customer` (Boolean)
  - Add `is_vendor` (Boolean)
  - Add `partner_type` (Selection: *Individual*, *Company*)
  - Add `phone`, `email`, `address` fields if not inherited
- [ ] Create tree and form views for partners with customer/vendor filters
- [ ] Create `partner` menu under `Sales / Customers` and `Purchase / Vendors`
- [ ] Demo data: 2 customers (Rajesh Interiors, Sita Homes), 2 vendors (Timber Mart, Hardware Hub)

---

### Phase B2 — Sales Order Model

- [ ] Create `sale.order` model (`_name = 'sale.order'`):
  - `name` (Char, sequence-generated, eg. SO00001)
  - `partner_id` (Many2one → res.partner, domain = is_customer=True)
  - `state` (Selection: *Draft → Confirmed → Partially Delivered → Fully Delivered → Cancelled*)
  - `order_line` (One2many → sale.order.line)
  - `date_order` (Datetime, default=now)
  - `total_amount` (Monetary, computed = sum of line subtotals)
  - `user_id` (Salesperson)
  - `notes` (Text)
- [ ] Create `sale.order.line` model:
  - `order_id` (Many2one → sale.order)
  - `product_id` (Many2one → product.product)
  - `description` (Text)
  - `quantity` (Float, required)
  - `delivered_qty` (Float, default=0)
  - `reserved_qty` (Float, default=0)
  - `price_unit` (Monetary, default from product.sale_price)
  - `subtotal` (Monetary, computed = qty × price_unit)
  - `stock_availability` (Char, computed — shows on-hand / free-to-use)

---

### Phase B3 — Sales Order Workflow & Business Logic

- [ ] **Confirm action**: `action_confirm()`
  - Validate partner and lines
  - Check product availability (free-to-use vs ordered)
  - Set `reserved_qty` on lines equal to `quantity`
  - Update each product's `reserved_qty`
  - Transition state → *Confirmed*
  - Trigger procurement evaluation (see Stream D integration)
- [ ] **Deliver action**: `action_deliver()`
  - Open delivery wizard (form with delivered quantities per line)
  - On validate: write `stock.ledger` entries (— for each product), update `delivered_qty`
  - If all lines delivered → *Fully Delivered*
  - If partial → *Partially Delivered*
- [ ] **Cancel action**: `action_cancel()`
  - Release reserved quantities back to free-to-use
  - Transition → *Cancelled*
- [ ] **On unlink restriction**: Prevent deletion of non-Draft orders
- [ ] Create `_update_reserved_qty(product_id, delta)` helper used across SO/MO
- [ ] Create delivery wizard model `sale.order.deliver`:
  - `order_id`, `line_ids` (One2many → deliver.line with `product_id`, `qty_delivered`, `qty_ordered`)
  - `action_validate()` — writes ledger and updates SO lines

---

### Phase B4 — Sales Order Views & Menus

- [ ] Tree view for SO: name, partner, date, state, total
- [ ] Form view with notebook:
  - Page 1: Order Lines (editable tree)
  - Page 2: Delivery / Status (read-only delivery tracking)
  - Page 3: Notes
- [ ] Kanban view: columns by state (Draft → Confirmed → Delivering → Done)
- [ ] Search view: filter by state, partner, date range
- [ ] Action buttons in header: **Confirm**, **Deliver**, **Cancel** (context-dependent)
- [ ] Smart buttons: `Deliveries (n)`, `Manufacturing Orders (n)`, `Purchase Orders (n)`
- [ ] Menu: `Sales / Sales Orders`, `Sales / Customers`
- [ ] Access: `group_sales_user` full CRUD; `group_business_owner` read-only
- [ ] Demo data: 2 sales orders in different states (one Draft, one Confirmed)

---

### Phase B5 — Purchase Order Model

- [ ] Create `purchase.order` model (`_name = 'purchase.order'`):
  - `name` (Char, sequence-generated, eg. PO00001)
  - `partner_id` (Many2one → res.partner, domain = is_vendor=True)
  - `state` (Selection: *Draft → Confirmed → Partially Received → Fully Received*)
  - `order_line` (One2many → purchase.order.line)
  - `date_order` (Datetime)
  - `total_amount` (Monetary, computed)
  - `user_id`
  - `notes`
- [ ] Create `purchase.order.line` model:
  - `order_id` (Many2one)
  - `product_id`
  - `description`
  - `quantity` (Float, required)
  - `received_qty` (Float, default=0)
  - `price_unit` (Monetary, default from product.cost_price)
  - `subtotal` (Monetary, computed)

---

### Phase B6 — Purchase Order Workflow & Business Logic

- [ ] **Confirm action**: Validate, transition → *Confirmed*
- [ ] **Receive action**: `action_receive()`
  - Receipt wizard with quantities per line
  - On validate: write `stock.ledger` entries (+ for each product), increase `on_hand_qty`
  - Update `received_qty` on each line
  - Transition → *Partially Received* or *Fully Received*
- [ ] **Cancel action**: (only Draft/Confirmed allowed)
- [ ] Create purchase receipt wizard model `purchase.order.receive` similar to SO delivery

---

### Phase B7 — Purchase Order Views & Menus

- [ ] Tree, form (notebook: lines, receipt status), search views
- [ ] Kanban by state
- [ ] Action buttons: **Confirm**, **Receive**, **Cancel**
- [ ] Menu: `Purchase / Purchase Orders`, `Purchase / Vendors`
- [ ] Access: `group_purchase_user` full CRUD; `group_inventory_manager` read; `group_business_owner` read-only
- [ ] Demo data: 1 purchase order in Draft, 1 in Confirmed

---

### Phase B8 — Sales ↔ Purchase Integration

- [ ] Relate SO lines to automatically generated POs (via procurement)
- [ ] Show procurement origin on PO (e.g. "Generated from SO00001 — Dining Table x15")
- [ ] Add smart button on SO form: `Purchase Orders` count
- [ ] Add smart button on PO form: `Source Sales Orders` if applicable
