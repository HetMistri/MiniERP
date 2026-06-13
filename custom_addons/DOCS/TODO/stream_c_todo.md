# Stream C — Manufacturing & Bill of Materials

## Focus
Complete BoM structure, Work Centers, Work Orders, Manufacturing Orders, component reservation, finished goods receipt, and production tracking.

---

### Phase C1 — Work Centers

- [x] Create `mrp.work.center` model (`_name = 'mrp.work.center'`):
  - `name` (Char, required)
  - `code` (Char, unique)
  - `responsible_id` (Many2one → res.users)
  - `working_hours` (Float, hours per day)
  - `cost_per_hour` (Monetary)
  - `description` (Text)
- [x] Tree + form views for work centers
- [x] Menu: `Manufacturing / Configuration / Work Centers`
- [x] Demo data: Assembly Line, Paint Floor, Packaging Unit

---

### Phase C2 — Bill of Materials (BoM)

- [x] Create `mrp.bom` model (`_name = 'mrp.bom'`):
  - `name` (Char, sequence-generated, eg. BoM00001)
  - `product_id` (Many2one → product.product, required) — finished good
  - `product_qty` (Float, default=1) — quantity this BoM produces
  - `component_ids` (One2many → mrp.bom.component)
  - `operation_ids` (One2many → mrp.bom.operation)
  - `active` (Boolean, default=True)
  - `notes` (Text)
- [x] Create `mrp.bom.component` model:
  - `bom_id` (Many2one → mrp.bom)
  - `product_id` (Many2one → product.product)
  - `quantity` (Float, required) — qty needed per `product_qty` of finished good
  - `uom_id` (related or selection)
- [x] Create `mrp.bom.operation` model:
  - `bom_id` (Many2one → mrp.bom)
  - `work_center_id` (Many2one → mrp.work.center)
  - `name` (Char) — e.g. Assembly, Painting
  - `sequence` (Integer)
  - `duration_minutes` (Float)
  - `description` (Text)
- [x] Tree + form views for BoM (notebook: components tab, operations tab)
- [x] Menu: `Manufacturing / Bill of Materials`
- [x] Demo data:
  - BoM for "Wooden Table" → components: Wooden Legs x4, Wooden Top x1, Screws x12
  - Operations: Assembly (60m), Painting (30m), Packing (20m)
  - BoM for "Office Chair" → components: Chair Base x1, Wheels x5, Screws x8
  - Operations: Assembly (45m), Packing (15m)

---

### Phase C3 — Manufacturing Order (MO) Model

- [x] Create `mrp.production` model (`_name = 'mrp.production'`):
  - `name` (Char, sequence-generated, eg. MO00001)
  - `product_id` (Many2one → product.product, required)
  - `product_qty` (Float, required)
  - `bom_id` (Many2one → mrp.bom) — auto-filled from product
  - `state` (Selection: *Draft → Confirmed → In Progress → Done → Cancelled*)
  - `component_ids` (One2many → mrp.production.component) — exploded from BoM
  - `work_order_ids` (One2many → mrp.work.order)
  - `date_planned_start` (Datetime)
  - `date_planned_finish` (Datetime)
  - `date_start` (Datetime, real)
  - `date_finished` (Datetime, real)
  - `assignee_id` (Many2one → res.users)
  - `origin` (Char) — e.g. "SO00001 — Sales Order"
  - `notes` (Text)

- [x] Create `mrp.production.component` model:
  - `production_id` (Many2one → mrp.production)
  - `product_id` (Many2one → product.product)
  - `quantity_needed` (Float)
  - `quantity_consumed` (Float, default=0)
  - `quantity_reserved` (Float, default=0)
  - `uom_id`

---

### Phase C4 — Work Orders

- [x] Create `mrp.work.order` model (`_name = 'mrp.work.order'`):
  - `production_id` (Many2one → mrp.production)
  - `work_center_id` (Many2one → mrp.work.center)
  - `name` (Char)
  - `sequence` (Integer)
  - `state` (Selection: *Pending → Ready → In Progress → Done*)
  - `duration_minutes` (Float)
  - `date_start` (Datetime)
  - `date_end` (Datetime)
  - `assignee_id` (Many2one → res.users)
- [x] Tree view for work orders inside MO form (editable in-line)
- [x] Ability to mark individual work orders as Done

---

### Phase C5 — Manufacturing Business Logic

- [x] **`action_confirm()`** on MO:
  - Validate product, BoM, qty
  - Explode BoM: copy components from BoM to `mrp.production.component`
  - Create `mrp.work.order` records from BoM operations
  - Reserve components: reduce `free_to_use_qty` of each component
  - Transition → *Confirmed*
- [x] **`action_start()`**:
  - Transition → *In Progress*
- [x] **`action_record_production()`** / **`action_finish()`**:
  - Validate all work orders are Done
  - Write `stock.ledger`: — for each component consumed (per `quantity_consumed`)
  - Write `stock.ledger`: + for finished product (`product_qty`)
  - Update product on-hand qty
  - Transition → *Done*
- [x] **`action_cancel()`**:
  - Release reserved quantities for all components
  - Only allowed in Draft/Confirmed state
- [x] Backflush component consumption: when MO finishes, auto-consume `quantity_needed` from each component
- [x] Handle over/under consumption: allow adjusting `quantity_consumed` before finishing

---

### Phase C6 — Manufacturing Views & Menus

- [x] Tree view for MO: name, product, qty, state, date, assignee
- [x] Form view with notebook:
  - Page 1: General (product, qty, BoM, dates, assignee, origin)
  - Page 2: Components (tree: product, needed, consumed, reserved)
  - Page 3: Work Orders (tree: sequence, name, center, duration, state)
  - Page 4: Notes
- [x] Action buttons: **Confirm**, **Start Production**, **Finish**, **Cancel** (context-dependent)
- [x] Search view: filter by state, product, BoM, date range
- [x] Menu: `Manufacturing / Manufacturing Orders`
- [x] Access: `group_manufacturing_user` full CRUD; `group_inventory_manager` read; `group_business_owner` read-only
- [x] Demo data: 1 MO in Draft for Wooden Table x10
