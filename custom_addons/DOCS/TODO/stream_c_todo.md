# Stream C — Manufacturing & Bill of Materials

## Focus
Complete BoM structure, Work Centers, Work Orders, Manufacturing Orders, component reservation, finished goods receipt, and production tracking.

---

### Phase C1 — Work Centers ✅

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

### Phase C2 — Bill of Materials (BoM) ⚠️

- [x] Create `mrp.bom` model with all fields (name seq-generated, product_id, product_qty, component_ids, operation_ids, active, notes)
- [x] Create `mrp.bom.component` model (bom_id, product_id, quantity, uom_id)
- [x] Create `mrp.bom.operation` model (bom_id, work_center_id, name, sequence, duration_minutes, description)
- [x] Tree + form views for BoM (notebook: components tab, operations tab)
- [x] Menu: `Manufacturing / Bill of Materials`
- [x] Demo data: BoM for Wooden Table, BoM for Office Chair
- [ ] **Mockup addition**: Add **"Logs" button** on BoM form → opens audit logs filtered by module "BoM"
- [ ] **Mockup addition**: BoM form should have explicit "Save" button
- [ ] **Mockup addition**: Operations section should have "Add a line" button

---

### Phase C3 — Manufacturing Order (MO) Model ✅

- [x] Create `mrp.production` model (`_name = 'mrp.production'`):
  - `name` (Char, sequence-generated, eg. MO-000001)
  - `product_id` (Many2one → product.product, required) — "Finished Product"
  - `product_qty` (Float, required) — "Quantity"
  - `bom_id` (Many2one → mrp.bom) — auto-filled from product
  - `state` (Selection: *Draft → Confirmed → In Progress → Done → Cancelled*)
  - `component_ids` (One2many → mrp.production.component)
  - `work_order_ids` (One2many → mrp.work.order)
  - `date_planned_start` (Datetime) — "Schedule Date"
  - `date_planned_finish` (Datetime)
  - `date_start` (Datetime, real)
  - `date_finished` (Datetime, real)
  - `assignee_id` (Many2one → res.users)
  - `origin` (Char) — e.g. "SO-000001 — Sales Order"
  - `notes` (Text)
- [x] Create `mrp.production.component` model:
  - `production_id` (Many2one → mrp.production)
  - `product_id` (Many2one → product.product)
  - `quantity_needed` (Float) — "To Consume"
  - `quantity_consumed` (Float, default=0) — "Consumed"
  - `quantity_reserved` (Float, default=0)
  - `uom_id`

---

### Phase C4 — Work Orders ✅

- [x] Create `mrp.work.order` model with all fields (production_id, work_center_id, name, sequence, state, duration_minutes, date_start, date_end, assignee_id)
- [x] Tree view for work orders inside MO form (editable in-line)
- [x] Ability to mark individual work orders as Done

---

### Phase C5 — Manufacturing Business Logic ⚠️

- [x] **`action_confirm()`** on MO
- [x] **`action_start()`**
- [x] **`action_record_production()`** / **`action_finish()`**
- [x] **`action_cancel()`**
- [x] Backflush component consumption
- [ ] **Mockup addition**: Add **`action_produce()`** button (labelled "Produce") as alternative/convenience to Finish — marks MO as Done, makes all fields readonly
- [ ] **Mockup addition**: Cancel makes all fields readonly
- [ ] **Mockup addition**: Track audit logs for all MO state changes, qty changes, assignee changes

---

### Phase C6 — Manufacturing Views & Menus ⚠️

> **SVG Mockup specifies additional details:**
> - List View columns: Reference, Date, Finished Product, Status, **Component Status** (Available / Not Available)
> - Form View: Product, Quantity, Bill of Material, Schedule Date, Assignee
> - Components section: "To Consume" qty populated from BoM, "Consumed" qty
> - Work Orders section: Name, Work Center, Duration, Real Duration, Start button per work order
> - Buttons: **Confirm**, **Start**, **Produce** (→ Done), **Cancel** (context-dependent)
> - **"Logs" button** on form header → opens audit logs filtered by module "Manufacturing"
> - Kanban view by status
> - Reference auto-generated following sequence on "New"

- [x] Tree view for MO: name, product, qty, state, date, assignee
- [ ] **Mockup addition**: Add **Component Status** column to MO tree view (Available / Not Available — computed from free_to_use_qty of each component)
- [x] Form view with notebook:
  - Page 1: General (product, qty, BoM, dates, assignee, origin)
  - Page 2: Components (tree: product, needed/to-consume, consumed, reserved)
  - Page 3: Work Orders (tree: sequence, name, center, duration, state, real duration)
  - Page 4: Notes
- [x] Action buttons: **Confirm**, **Start Production**, **Finish**, **Cancel** (context-dependent)
- [ ] **Mockup addition**: Rename "Finish" to **"Produce"** (or add as separate button) — marks MO Done, all fields readonly
- [ ] **Mockup addition**: Add **"Logs" button** — opens `audit.log` tree view filtered by module = "Manufacturing"
- [ ] Add Kanban view for MO by state
- [x] Search view: filter by state, product, BoM, date range
- [x] Menu: `Manufacturing / Manufacturing Orders`
- [x] Access: `group_manufacturing_user` full CRUD; `group_inventory_manager` read; `group_business_owner` read-only
- [x] Demo data: 1 MO in Draft for Wooden Table x10
