# Stream D — Procurement Automation, Dashboard & Integration

## Focus
Procurement strategy engine (MTS/MTO), automated PO/MO creation on shortage, real-time dashboard, end-to-end integration testing, report generation, and final polish.

---

### Phase D1 — Procurement Configuration on Product

- [ ] Extend `product.product` with procurement fields:
  - `procure_on_demand` (Boolean) — enable auto-replenishment
  - `procurement_type` (Selection: *Manufacture*, *Purchase*)
  - `vendor_id` (Many2one → res.partner, domain = is_vendor=True) — used when proc_type = Purchase
  - `bom_id` (Many2one → mrp.bom) — used when proc_type = Manufacture
  - `min_stock_qty` (Float) — reorder point (future MTS enhancement)
  - `lead_time_days` (Integer, default=1)
- [ ] Add these fields to the Procurement Settings page in product form view

---

### Phase D2 — Procurement Engine (Core Logic)

- [ ] Create `procurement.manager` singleton / static helper:
  - `evaluate(product_id, required_qty, origin, origin_id)`
    - Calculate shortage = `required_qty - free_to_use_qty`
    - If shortage ≤ 0 → nothing to do
    - If shortage > 0 and `procure_on_demand = True`:
      - If `procurement_type = Purchase` → call `_create_purchase_order(product_id, shortage, origin)`
      - If `procurement_type = Manufacture` → call `_create_manufacturing_order(product_id, shortage, origin)`
- [ ] `_create_purchase_order(product_id, qty, origin)`:
  - Create PO in Draft state for vendor_id
  - Single line with product, qty, price = cost_price
  - Set origin text
- [ ] `_create_manufacturing_order(product_id, qty, origin)`:
  - Create MO in Draft state
  - Auto-assign BoM from product
  - Set origin text
- [ ] Handle cascading procurement: if MO components themselves are MTO, recursively trigger procurement for those too
- [ ] Prevent duplicate procurement: check for existing Draft PO/MO for same product + origin

---

### Phase D3 — Procurement Triggers (Integration Points)

- [ ] **Sales Order Confirmation trigger**:
  - After `action_confirm()` on SO, call `procurement.manager.evaluate()` for each line
  - Pass origin = "SO{name} — {product}"
- [ ] **Manual reorder button**:
  - Add "Replenish" button on product form view
  - Opens wizard: qty to order, confirms action
- [ ] **Cron-based MTS reorder (optional)**:
  - Daily cron: check products with `min_stock_qty` set, trigger if `on_hand_qty < min_stock_qty`

---

### Phase D4 — Dashboard Engine

- [ ] Create `dashboard.data` model to cache computed KPIs (or compute on‑the‑fly)
- [ ] Create controller `/dashboard/data` returning JSON:
  - `total_sales_orders` — count of all SOs
  - `pending_deliveries` — SOs in Confirmed or Partially Delivered state
  - `total_mo` — count of all MOs
  - `delayed_orders` — SOs past expected delivery date
  - `total_po` — count of all POs
  - `partial_receipts` — POs in Partially Received state
  - `low_stock_products` — products where `free_to_use_qty ≤ 0`
  - `recent_audit_logs` — last 10 audit entries
- [ ] Create dashboard view (JavaScript widget or simple QWeb template):
  - KPI cards (big numbers)
  - Quick-links to filtered lists (clicking a card opens relevant tree view)
  - Color-coded status indicators (green/amber/red)
- [ ] Menu: `Dashboard` as top-level menu item (first position)
- [ ] All users see the dashboard — data filtered by their access rights

---

### Phase D5 — Reports

- [ ] Create **Sales Order Report** (QWeb PDF):
  - Company logo, SO number, customer, date
  - Lines table (product, qty, price, subtotal)
  - Total amount
- [ ] Create **Purchase Order Report** (QWeb PDF)
- [ ] Create **Manufacturing Order Report** — includes BoM component list
- [ ] Create **Stock Ledger Report** — product-wise movement summary
- [ ] Create **Inventory Valuation Report** — product × on-hand qty × cost price

---

### Phase D6 — End-to-End Integration Testing

- [ ] **Test Flow 1 — MTS Full Cycle**:
  - Create product with stock = 100 (via ledger)
  - Create SO for 10 units → Confirm → Deliver
  - Verify: reserved_qty, free_to_use_qty, on_hand_qty, stock.ledger entries
- [ ] **Test Flow 2 — MTO Purchase**:
  - Create product: on_hand = 0, `procure_on_demand = True`, `procurement_type = Purchase`, `vendor_id` set
  - Create SO for 15 → Confirm
  - Verify: PO auto-created in Draft, origin linked
- [ ] **Test Flow 3 — MTO Manufacture**:
  - Create product with BoM, components with sufficient stock
  - `procurement_type = Manufacture`
  - Create SO for 10 → Confirm
  - Verify: MO auto-created, BoM exploded, components reserved
- [ ] **Test Flow 4 — Manufacturing Completion**:
  - Take MO from Draft → Confirm → Start → Finish
  - Verify: component stock decreased, finished product increased, work orders tracked
- [ ] **Test Flow 5 — Purchase Receipt**:
  - Confirm PO → Receive
  - Verify: stock increased, ledger updated, SO procurement satisfied
- [ ] **Test Flow 6 — Access Rights**:
  - Create users for each role (Sales, Purchase, Manufacturing, Inventory)
  - Verify each can only access their permitted menus/models
  - Verify Admin has full access including Audit Logs

---

### Phase D7 — Error Handling & Edge Cases

- [ ] Prevent SO confirmation when no stock AND no procurement configured
- [ ] Handle partial deliveries gracefully (SO Partially Delivered state)
- [ ] Handle partial receipts on PO
- [ ] Prevent MO confirmation if BoM is missing or inactive
- [ ] Handle MO cancellation with consumed components (reverse ledger if needed)
- [ ] Validate negative stock (configurable: warn vs block)
- [ ] Sequence rollover handling

---

### Phase D8 — Final Polish & Documentation

- [ ] Add loading/empty states to dashboard
- [ ] Consistent color scheme & button styling across all views
- [ ] Add tooltips on computed fields (on-hand, reserved, free-to-use)
- [ ] Create `__init__` model registry validation (no missing imports)
- [ ] Run full test suite: `--test-enable` with demo data
- [ ] Write `README.md` with:
  - Architecture overview
  - Module dependency graph
  - Setup instructions
  - User roles & permissions
  - Workflow diagrams (ascii or link to the SVG)
- [ ] Add license header to all Python files
- [ ] Verify `__manifest__.py` has all data files registered correctly
