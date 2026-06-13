-- ============================================================================
-- Mini ERP — Full Database Bootstrap
-- Shiv Furniture Works: From Demand to Delivery
-- ============================================================================
-- Self-contained: creates mini_erp database and all tables.
-- Mount into /docker-entrypoint-initdb.d/ via docker-compose.
-- ============================================================================

CREATE DATABASE mini_erp OWNER odoo;
ALTER USER odoo CREATEDB;

\c mini_erp

-- ============================================================================
-- ENUMS
-- ============================================================================

CREATE TYPE product_type AS ENUM ('stockable', 'service', 'consumable');
CREATE TYPE transaction_type AS ENUM (
    'sale_delivery', 'purchase_receipt', 'manufacture_in',
    'manufacture_out', 'initial', 'adjustment'
);
CREATE TYPE so_state AS ENUM (
    'draft', 'confirmed', 'partially_delivered', 'fully_delivered', 'cancelled'
);
CREATE TYPE po_state AS ENUM (
    'draft', 'confirmed', 'partially_received', 'fully_received', 'cancelled'
);
CREATE TYPE mo_state AS ENUM (
    'draft', 'confirmed', 'in_progress', 'done', 'cancelled'
);
CREATE TYPE wo_state AS ENUM ('pending', 'ready', 'in_progress', 'done');
CREATE TYPE partner_type AS ENUM ('individual', 'company');
CREATE TYPE audit_action AS ENUM ('create', 'write', 'unlink');
CREATE TYPE procurement_type AS ENUM ('manufacture', 'purchase');

-- ============================================================================
-- SEQUENCES (Document Auto-Numbering)
-- ============================================================================

CREATE SEQUENCE seq_product_reference   START 10000;
CREATE SEQUENCE seq_sale_order           START 10000;
CREATE SEQUENCE seq_purchase_order       START 10000;
CREATE SEQUENCE seq_mrp_production       START 10000;
CREATE SEQUENCE seq_mrp_bom              START 10000;

-- ============================================================================
-- PRODUCT & INVENTORY MODULE
-- ============================================================================

-- Unit of Measure
CREATE TABLE product_uom (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(64) NOT NULL,
    code            VARCHAR(8) NOT NULL,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE product_uom IS 'Units of Measure (e.g. pcs, kg, m, box)';

-- Product Category (hierarchical via parent_path)
CREATE TABLE product_category (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    parent_id       INTEGER REFERENCES product_category(id) ON DELETE RESTRICT,
    parent_path     VARCHAR(512),
    description     TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_category_parent_path ON product_category USING btree (parent_path);
COMMENT ON TABLE product_category IS 'Hierarchical product categories';

-- Product Master
CREATE TABLE product_product (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(256) NOT NULL,
    reference       VARCHAR(32) NOT NULL DEFAULT 'PROD-' || nextval('seq_product_reference')::TEXT,
    category_id     INTEGER REFERENCES product_category(id) ON DELETE RESTRICT,
    uom_id          INTEGER NOT NULL REFERENCES product_uom(id) ON DELETE RESTRICT,
    product_type    product_type NOT NULL DEFAULT 'stockable',
    sale_price      NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (sale_price >= 0),
    cost_price      NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (cost_price >= 0),
    currency_id     INTEGER NOT NULL DEFAULT 1,
    company_id      INTEGER NOT NULL DEFAULT 1,
    on_hand_qty     NUMERIC(16,4) NOT NULL DEFAULT 0,
    reserved_qty    NUMERIC(16,4) NOT NULL DEFAULT 0,
    free_to_use_qty NUMERIC(16,4) GENERATED ALWAYS AS (on_hand_qty - reserved_qty) STORED,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    -- Procurement settings (Phase D)
    procure_on_demand   BOOLEAN NOT NULL DEFAULT FALSE,
    procurement_type    procurement_type,
    vendor_id           INTEGER,
    bom_id              INTEGER,
    min_stock_qty       NUMERIC(16,4) DEFAULT 0,
    lead_time_days      INTEGER NOT NULL DEFAULT 1,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (reference)
);
CREATE INDEX idx_product_category ON product_product (category_id);
CREATE INDEX idx_product_uom ON product_product (uom_id);
CREATE INDEX idx_product_active ON product_product (active);
CREATE INDEX idx_product_procure ON product_product (procure_on_demand)
    WHERE procure_on_demand = TRUE;
COMMENT ON TABLE product_product IS 'Master product catalog';
COMMENT ON COLUMN product_product.free_to_use_qty
    IS 'Computed: on_hand_qty - reserved_qty';

-- Product Quantity History (Snapshot)
CREATE TABLE product_quantity_history (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE CASCADE,
    quantity        NUMERIC(16,4) NOT NULL,
    reason          VARCHAR(256),
    user_id         INTEGER NOT NULL DEFAULT 1,
    date            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_qty_history_product ON product_quantity_history (product_id);
CREATE INDEX idx_qty_history_date ON product_quantity_history USING btree (date DESC);

-- Stock Ledger (Single Source of Truth for Inventory)
CREATE TABLE stock_ledger (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    reference       VARCHAR(64),
    transaction_type transaction_type NOT NULL,
    quantity        NUMERIC(16,4) NOT NULL,  -- signed: +inbound, -outbound
    balance_after   NUMERIC(16,4) NOT NULL,
    user_id         INTEGER NOT NULL DEFAULT 1,
    date            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    notes           TEXT,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_ledger_product ON stock_ledger (product_id);
CREATE INDEX idx_ledger_date ON stock_ledger USING btree (date DESC);
CREATE INDEX idx_ledger_type ON stock_ledger (transaction_type);
COMMENT ON TABLE stock_ledger IS 'Single source of truth for all stock movements';

-- ============================================================================
-- AUDIT MODULE
-- ============================================================================

CREATE TABLE audit_log (
    id              SERIAL PRIMARY KEY,
    model_name      VARCHAR(128) NOT NULL,
    record_id       INTEGER NOT NULL,
    field_name      VARCHAR(128),
    old_value       TEXT,
    new_value       TEXT,
    action          audit_action NOT NULL,
    user_id         INTEGER NOT NULL DEFAULT 1,
    ip_address      VARCHAR(45),
    timestamp       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_model ON audit_log (model_name);
CREATE INDEX idx_audit_record ON audit_log (record_id);
CREATE INDEX idx_audit_action ON audit_log (action);
CREATE INDEX idx_audit_timestamp ON audit_log USING btree (timestamp DESC);
CREATE INDEX idx_audit_user ON audit_log (user_id);
COMMENT ON TABLE audit_log IS 'Complete audit trail for all business documents';

-- ============================================================================
-- PARTNER MODULE (Customers & Vendors)
-- ============================================================================

CREATE TABLE res_partner (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(256) NOT NULL,
    partner_type    partner_type NOT NULL DEFAULT 'individual',
    is_customer     BOOLEAN NOT NULL DEFAULT FALSE,
    is_vendor       BOOLEAN NOT NULL DEFAULT FALSE,
    phone           VARCHAR(32),
    email           VARCHAR(128),
    address         TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_partner_customer ON res_partner (is_customer) WHERE is_customer = TRUE;
CREATE INDEX idx_partner_vendor ON res_partner (is_vendor) WHERE is_vendor = TRUE;
COMMENT ON TABLE res_partner IS 'Customers, vendors, and contacts';

-- ============================================================================
-- SALES MODULE
-- ============================================================================

CREATE TABLE sale_order (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32) NOT NULL
                        DEFAULT 'SO-' || LPAD(nextval('seq_sale_order')::TEXT, 5, '0'),
    partner_id      INTEGER NOT NULL REFERENCES res_partner(id) ON DELETE RESTRICT,
    state           so_state NOT NULL DEFAULT 'draft',
    date_order      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expected_date   DATE,
    total_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    user_id         INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    company_id      INTEGER NOT NULL DEFAULT 1,
    currency_id     INTEGER NOT NULL DEFAULT 1,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name)
);
CREATE INDEX idx_so_partner ON sale_order (partner_id);
CREATE INDEX idx_so_state ON sale_order (state);
CREATE INDEX idx_so_date ON sale_order USING btree (date_order DESC);
COMMENT ON TABLE sale_order IS 'Sales Orders — customer demand';

CREATE TABLE sale_order_line (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES sale_order(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL DEFAULT 10,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    description     TEXT,
    quantity        NUMERIC(16,4) NOT NULL CHECK (quantity > 0),
    delivered_qty   NUMERIC(16,4) NOT NULL DEFAULT 0 CHECK (delivered_qty >= 0),
    reserved_qty    NUMERIC(16,4) NOT NULL DEFAULT 0 CHECK (reserved_qty >= 0),
    price_unit      NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (price_unit >= 0),
    subtotal        NUMERIC(16,2) GENERATED ALWAYS AS (quantity * price_unit) STORED,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_so_line_order ON sale_order_line (order_id);
CREATE INDEX idx_so_line_product ON sale_order_line (product_id);

-- Sales Order Delivery Wizard
CREATE TABLE sale_order_deliver (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES sale_order(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL DEFAULT 1,
    date            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE sale_order_deliver_line (
    id              SERIAL PRIMARY KEY,
    deliver_id      INTEGER NOT NULL REFERENCES sale_order_deliver(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    qty_ordered     NUMERIC(16,4) NOT NULL,
    qty_delivered   NUMERIC(16,4) NOT NULL CHECK (qty_delivered >= 0),
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_deliver_line_deliver ON sale_order_deliver_line (deliver_id);

-- ============================================================================
-- PURCHASE MODULE
-- ============================================================================

CREATE TABLE purchase_order (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32) NOT NULL
                        DEFAULT 'PO-' || LPAD(nextval('seq_purchase_order')::TEXT, 5, '0'),
    partner_id      INTEGER NOT NULL REFERENCES res_partner(id) ON DELETE RESTRICT,
    state           po_state NOT NULL DEFAULT 'draft',
    date_order      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    total_amount    NUMERIC(16,2) NOT NULL DEFAULT 0,
    user_id         INTEGER NOT NULL DEFAULT 1,
    notes           TEXT,
    origin          VARCHAR(256),
    company_id      INTEGER NOT NULL DEFAULT 1,
    currency_id     INTEGER NOT NULL DEFAULT 1,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name)
);
CREATE INDEX idx_po_partner ON purchase_order (partner_id);
CREATE INDEX idx_po_state ON purchase_order (state);
CREATE INDEX idx_po_date ON purchase_order USING btree (date_order DESC);
COMMENT ON TABLE purchase_order IS 'Purchase Orders — vendor supply';

CREATE TABLE purchase_order_line (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES purchase_order(id) ON DELETE CASCADE,
    sequence        INTEGER NOT NULL DEFAULT 10,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    description     TEXT,
    quantity        NUMERIC(16,4) NOT NULL CHECK (quantity > 0),
    received_qty    NUMERIC(16,4) NOT NULL DEFAULT 0 CHECK (received_qty >= 0),
    price_unit      NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (price_unit >= 0),
    subtotal        NUMERIC(16,2) GENERATED ALWAYS AS (quantity * price_unit) STORED,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_po_line_order ON purchase_order_line (order_id);
CREATE INDEX idx_po_line_product ON purchase_order_line (product_id);

-- Purchase Receipt Wizard
CREATE TABLE purchase_order_receive (
    id              SERIAL PRIMARY KEY,
    order_id        INTEGER NOT NULL REFERENCES purchase_order(id) ON DELETE CASCADE,
    user_id         INTEGER NOT NULL DEFAULT 1,
    date            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE purchase_order_receive_line (
    id              SERIAL PRIMARY KEY,
    receive_id      INTEGER NOT NULL REFERENCES purchase_order_receive(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    qty_ordered     NUMERIC(16,4) NOT NULL,
    qty_received    NUMERIC(16,4) NOT NULL CHECK (qty_received >= 0),
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_receive_line_receive ON purchase_order_receive_line (receive_id);

-- ============================================================================
-- MANUFACTURING MODULE
-- ============================================================================

-- Work Centers
CREATE TABLE mrp_work_center (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL,
    code            VARCHAR(32) NOT NULL UNIQUE,
    responsible_id  INTEGER NOT NULL DEFAULT 1,
    working_hours   NUMERIC(6,2) NOT NULL DEFAULT 8 CHECK (working_hours > 0),
    cost_per_hour   NUMERIC(16,2) NOT NULL DEFAULT 0 CHECK (cost_per_hour >= 0),
    description     TEXT,
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
COMMENT ON TABLE mrp_work_center IS 'Production work centers / cells';

-- Bill of Materials
CREATE TABLE mrp_bom (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32) NOT NULL
                        DEFAULT 'BoM-' || LPAD(nextval('seq_mrp_bom')::TEXT, 5, '0'),
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    product_qty     NUMERIC(16,4) NOT NULL DEFAULT 1 CHECK (product_qty > 0),
    active          BOOLEAN NOT NULL DEFAULT TRUE,
    notes           TEXT,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name)
);
CREATE INDEX idx_bom_product ON mrp_bom (product_id);
COMMENT ON TABLE mrp_bom IS 'Bill of Materials — defines how a product is made';

CREATE TABLE mrp_bom_component (
    id              SERIAL PRIMARY KEY,
    bom_id          INTEGER NOT NULL REFERENCES mrp_bom(id) ON DELETE CASCADE,
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    quantity        NUMERIC(16,4) NOT NULL CHECK (quantity > 0),
    uom_id          INTEGER NOT NULL REFERENCES product_uom(id) ON DELETE RESTRICT,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_bom_component_bom ON mrp_bom_component (bom_id);
CREATE INDEX idx_bom_component_product ON mrp_bom_component (product_id);

CREATE TABLE mrp_bom_operation (
    id              SERIAL PRIMARY KEY,
    bom_id          INTEGER NOT NULL REFERENCES mrp_bom(id) ON DELETE CASCADE,
    work_center_id  INTEGER NOT NULL REFERENCES mrp_work_center(id) ON DELETE RESTRICT,
    sequence        INTEGER NOT NULL DEFAULT 10,
    name            VARCHAR(128) NOT NULL,
    duration_minutes NUMERIC(8,2) NOT NULL DEFAULT 0 CHECK (duration_minutes >= 0),
    description     TEXT,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_bom_operation_bom ON mrp_bom_operation (bom_id);

-- Manufacturing Orders
CREATE TABLE mrp_production (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(32) NOT NULL
                        DEFAULT 'MO-' || LPAD(nextval('seq_mrp_production')::TEXT, 5, '0'),
    product_id      INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    product_qty     NUMERIC(16,4) NOT NULL CHECK (product_qty > 0),
    bom_id          INTEGER REFERENCES mrp_bom(id) ON DELETE RESTRICT,
    state           mo_state NOT NULL DEFAULT 'draft',
    date_planned_start  TIMESTAMPTZ,
    date_planned_finish TIMESTAMPTZ,
    date_start      TIMESTAMPTZ,
    date_finished   TIMESTAMPTZ,
    assignee_id     INTEGER NOT NULL DEFAULT 1,
    origin          VARCHAR(256),
    notes           TEXT,
    company_id      INTEGER NOT NULL DEFAULT 1,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (name)
);
CREATE INDEX idx_mo_product ON mrp_production (product_id);
CREATE INDEX idx_mo_state ON mrp_production (state);
CREATE INDEX idx_mo_bom ON mrp_production (bom_id);
COMMENT ON TABLE mrp_production IS 'Manufacturing Orders — production schedule';

CREATE TABLE mrp_production_component (
    id                  SERIAL PRIMARY KEY,
    production_id       INTEGER NOT NULL REFERENCES mrp_production(id) ON DELETE CASCADE,
    product_id          INTEGER NOT NULL REFERENCES product_product(id) ON DELETE RESTRICT,
    quantity_needed     NUMERIC(16,4) NOT NULL CHECK (quantity_needed > 0),
    quantity_consumed   NUMERIC(16,4) NOT NULL DEFAULT 0 CHECK (quantity_consumed >= 0),
    quantity_reserved   NUMERIC(16,4) NOT NULL DEFAULT 0 CHECK (quantity_reserved >= 0),
    uom_id              INTEGER NOT NULL REFERENCES product_uom(id) ON DELETE RESTRICT,
    create_uid          INTEGER NOT NULL DEFAULT 1,
    create_date         TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid           INTEGER NOT NULL DEFAULT 1,
    write_date          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_mo_component_production ON mrp_production_component (production_id);
CREATE INDEX idx_mo_component_product ON mrp_production_component (product_id);

-- Work Orders
CREATE TABLE mrp_work_order (
    id              SERIAL PRIMARY KEY,
    production_id   INTEGER NOT NULL REFERENCES mrp_production(id) ON DELETE CASCADE,
    work_center_id  INTEGER NOT NULL REFERENCES mrp_work_center(id) ON DELETE RESTRICT,
    sequence        INTEGER NOT NULL DEFAULT 10,
    name            VARCHAR(128) NOT NULL,
    state           wo_state NOT NULL DEFAULT 'pending',
    duration_minutes NUMERIC(8,2) NOT NULL DEFAULT 0 CHECK (duration_minutes >= 0),
    date_start      TIMESTAMPTZ,
    date_end        TIMESTAMPTZ,
    assignee_id     INTEGER NOT NULL DEFAULT 1,
    create_uid      INTEGER NOT NULL DEFAULT 1,
    create_date     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    write_uid       INTEGER NOT NULL DEFAULT 1,
    write_date      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_wo_production ON mrp_work_order (production_id);
CREATE INDEX idx_wo_center ON mrp_work_order (work_center_id);
CREATE INDEX idx_wo_state ON mrp_work_order (state);

-- ============================================================================
-- TRIGGERS
-- ============================================================================

-- Auto-update write_date on any row modification
CREATE OR REPLACE FUNCTION update_write_date()
RETURNS TRIGGER AS $$
BEGIN
    NEW.write_date = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to all business tables
DO $$
DECLARE
    tbl TEXT;
BEGIN
    FOR tbl IN
        SELECT unnest(ARRAY[
            'product_uom', 'product_category', 'product_product',
            'res_partner',
            'sale_order', 'sale_order_line',
            'purchase_order', 'purchase_order_line',
            'mrp_work_center', 'mrp_bom', 'mrp_bom_component', 'mrp_bom_operation',
            'mrp_production', 'mrp_production_component', 'mrp_work_order'
        ])
    LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%s_write_date
             BEFORE UPDATE ON %I
             FOR EACH ROW EXECUTE FUNCTION update_write_date()',
            tbl, tbl
        );
    END LOOP;
END;
$$;

-- Auto-update free_to_use_qty on product when on_hand or reserved changes
CREATE OR REPLACE FUNCTION update_product_quantities()
RETURNS TRIGGER AS $$
BEGIN
    NEW.free_to_use_qty = NEW.on_hand_qty - NEW.reserved_qty;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_product_quantities
    BEFORE UPDATE OF on_hand_qty, reserved_qty ON product_product
    FOR EACH ROW
    EXECUTE FUNCTION update_product_quantities();

-- ============================================================================
-- SEED DATA
-- ============================================================================

-- Default UoMs
INSERT INTO product_uom (name, code) VALUES
    ('Pieces', 'pcs'),
    ('Kilograms', 'kg'),
    ('Meters', 'm'),
    ('Box', 'box'),
    ('Litres', 'l'),
    ('Pairs', 'pr');

-- Default product categories
INSERT INTO product_category (name, parent_path) VALUES
    ('All Products', '/'),
    ('Furniture', '/1/'),
    ('Raw Materials', '/2/'),
    ('Hardware', '/3/');

INSERT INTO product_category (name, parent_id, parent_path) VALUES
    ('Tables', 2, '/1/4/'),
    ('Chairs', 2, '/1/5/'),
    ('Wood', 3, '/2/6/'),
    ('Metal', 3, '/2/7/'),
    ('Screws & Fasteners', 4, '/3/8/');

-- Sample Work Centers
INSERT INTO mrp_work_center (name, code, cost_per_hour) VALUES
    ('Assembly Line', 'ASSY', 50.00),
    ('Paint Floor', 'PAINT', 30.00),
    ('Packaging Unit', 'PACK', 20.00);
