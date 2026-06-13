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

---

## Phase D3 — Procurement Triggers (Integration Points)

### 1. Work Done
- **Sales Order Confirmation Trigger:** Added logic to `action_confirm()` of `sale.order` to automatically trigger `procurement.manager.evaluate()` for any confirmed sales order lines where the product has `procure_on_demand` enabled.
- **Manual Replenishment Wizard:** Registered `product.replenish.wizard` model and registered `'wizard/product_replenish_views.xml'` in the manifest. Added a "Replenish" header button on the product form view to open this wizard, allowing manual, quick evaluations.
- **Daily Reordering Cron:** Created `data/ir_cron_data.xml` defining a daily scheduler task in Odoo (`model._cron_evaluate_reordering_rules()`) to automatically scan products with a minimum stock threshold set and trigger MTS replenishment POs/MOs if the stock drops below the threshold.

---

## Phase D4 — Dashboard Engine

### 1. Work Done
- **Dashboard Data Model:** Created `models/dashboard.py` implementing the `dashboard.data` model which dynamically computes:
  - Granular KPIs for Sales (`so_all`, `so_draft`, `so_confirmed`, `so_partial`, `so_delivered`).
  - Granular KPIs for Purchase (`po_all`, `po_draft`, `po_confirmed`, `po_partial`, `po_received`).
  - Granular KPIs for Manufacturing (`mo_all`, `mo_draft`, `mo_confirmed`, `mo_progress`, `mo_done`).
  - User-specific filters (`filter_my_sales`, `filter_my_purchases`, `filter_my_manufacturing`) which filter counts and tree views dynamically.
  - Global Search results (`search_query` string query with computed `search_sale_ids`, `search_product_ids`, `search_purchase_ids`, and `search_mo_ids`).
- **Master Menu Sidebar:** Added a custom left-hand sidebar navigation bar featuring the App Logo and branding ("Mini ERP"), with quick links to Sales Orders, Products, Manufacturing Orders, Purchase Orders, and Bills of Materials.
- **Vibrant Dashboard Form View:** Created `views/dashboard_views.xml` defining a custom, high-fidelity form view with glassmorphism styling, a global search input box with Clear/Search action buttons, "My Only" toggles for each module section, granular clickable sub-state KPI cards, and a recent audit trail list view.
- **Controller Route:** Exposed `/dashboard/data` JSON POST controller route in `controllers/controllers.py` serving dashboard analytics data.
- **Vibrant CSS Assets:** Added `static/src/css/dashboard.css` using rich gradients, modern layout columns (flex layout for Sidebar and Main Area), custom glassmorphic panels, and smooth hover scaling transitions.

---

## Phase D5 — Reports

### 1. Work Done
- **QWeb PDF Layouts:** Created `views/reports.xml` registering PDF print actions and layouts for Sales Orders, Purchase Orders, Manufacturing Orders (with component breakdown lists), Stock Ledger history, and a grand-totaled Inventory Valuation summary report.

---

## Phase D6 — End-to-End Integration Testing

### 1. Work Done
- **Python Test Cases:** Created `tests/test_procurement.py` implementing comprehensive TransactionCase tests checking:
  - Flow 1 (MTS full cycle reservation and delivery wizard execution).
  - Flow 2 (MTO purchase PO auto-generation).
  - Flow 3 (MTO manufacture MO auto-generation & BOM component reservation).
  - Flow 4 (MO workflow progress from confirmed -> progress -> done).
  - Flow 5 (PO receiving wizard stock increases).
  - Flow 6 (Access/negative stock block and inactive BOM validations).

---

## Phase D7 — Error Handling & Edge Cases

### 1. Work Done
- **Negative Stock Settings:** Added `allow_negative_stock` configuration field to the company model (`res.company`) and form view, allowing toggleable block vs warn behavior.
- **Blocking Validations:** Added logic to block Sales Order confirmation if there is no stock and MTO is not configured, and blocked Manufacturing Order confirmation if its Bill of Materials is inactive.
- **MO Cancel Reversals:** Implemented clean ledger reversals if a Manufacturing Order is cancelled from a `done` state.
- **Delivery Stock Restraints:** Updated the SO delivery wizard to block delivery validation on insufficient stock unless `allow_negative_stock` is enabled.

---

## Phase D8 — Final Polish & Documentation

### 1. Work Done
- **UI/UX Styling:** Added tooltips on computed fields (on-hand, reserved, free-to-use) and finalized colors/button styling.
- **Documentation:** Created a comprehensive `README.md` containing the architecture overview, workflow/sequence diagrams, module dependency graphs, and permissions definitions.
- **License Headers:** Added standard `LGPL-3.0` license headers to all Python files in the module.
- **Verify Registry & Imports:** Checked `__init__` files to ensure no missing imports.
- **Test Enable Run:** Ran a full test run using `--test-enable` confirming all tests compile and pass.

---

## How to Access and Check the Dashboard

### 1. Accessing through Odoo Web Client (GUI)
1. **Access Link:** Open your browser and navigate to `http://localhost:8069`.
2. **Authentication:** Log in using credentials (e.g. `admin` / `admin`).
3. **Menu Navigation:** Locate the top navigation menu bar. The **Dashboard** menu item is placed in the first position. Click on it.
4. **Interactive Dashboard Controls:**
   - **Master Menu Sidebar:** Use the left sidebar to navigate directly to major models (Sales Orders, Products, Manufacturing Orders, Purchase Orders, Bills of Materials). It has a premium glassmorphic style.
   - **Global Search Bar:** Type a query into the Search box in the top-right and click the Search button to view a grid of matching Sales Orders, Products, Purchase Orders, and Manufacturing Orders. Click the Clear (X) button to reset search results.
   - **"My Only" Filters:** Toggle the filter switch on the right side of the Sales, Purchases, or Manufacturing sections to filter the KPI counts and subsequent redirections to only records assigned to the logged-in user.
   - **Granular KPI Cards:** Click on any of the state-specific sub-cards (e.g. Draft, Confirmed, Delivered) to instantly jump to the corresponding record list filtered to that specific state.
   - **Audit Logs Trail:** Scroll to the bottom of the page to view the last 10 audit log entries tracked dynamically.
   - **CSS Styling & Animations:** The interface has a premium look using custom Harmonious Indigo/Cyan gradients, translucent card elements, and micro-animations on hover.

### 2. Accessing through the JSON Controller Endpoint
You can programmatically retrieve the dashboard counts by sending a JSON POST request to the `/dashboard/data` route:
- **Endpoint URL:** `http://localhost:8069/dashboard/data`
- **Request Headers:** `Content-Type: application/json`
- **Request Payload:**
  ```json
  {
    "params": {}
  }
  ```
- **Response Example:**
  ```json
  {
    "jsonrpc": "2.0",
    "id": null,
    "result": {
      "total_sales_orders": 12,
      "pending_deliveries": 3,
      "total_mo": 5,
      "delayed_orders": 1,
      "total_po": 4,
      "partial_receipts": 0,
      "low_stock_products": 2,
      "recent_audit_logs": [...]
    }
  }
  ```


