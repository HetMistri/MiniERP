/** @odoo-module **/

import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";
import { Component, onMounted, onWillUnmount, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { rpc } from "@web/core/network/rpc";

// ─────────────────────────────────────────────
//  Helpers
// ─────────────────────────────────────────────

const STATE_LABELS = {
    // sale.order
    draft: "Draft",
    confirmed: "Confirmed",
    partially_delivered: "Partial",
    fully_delivered: "Delivered",
    cancelled: "Cancelled",
    // purchase.order
    partially_received: "Partial",
    fully_received: "Received",
    // mrp.production
    progress: "In Progress",
    done: "Done",
    cancel: "Cancelled",
};

const STATE_CSS = {
    draft: "badge-state-draft",
    confirmed: "badge-state-confirmed",
    partially_delivered: "badge-state-partial",
    fully_delivered: "badge-state-done",
    cancelled: "badge-state-cancelled",
    cancel: "badge-state-cancelled",
    partially_received: "badge-state-partial",
    fully_received: "badge-state-done",
    progress: "badge-state-progress",
    done: "badge-state-done",
};

function stateLabel(s) { return STATE_LABELS[s] || s; }
function stateCss(s)   { return STATE_CSS[s] || "badge-state-draft"; }

// ─────────────────────────────────────────────
//  SectionViewWidget OWL Component
// ─────────────────────────────────────────────

export class SectionViewWidget extends Component {
    static template = "mini_erp.SectionViewWidget";
    static props = { ...standardFieldProps };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");

        // Each key is a section id
        this.state = useState({
            viewMode: {
                products:      "kanban",
                sales:         "kanban",
                purchases:     "kanban",
                manufacturing: "kanban",
                inventory:     "kanban",
            },
            data: {
                products:      [],
                sales:         [],
                purchases:     [],
                manufacturing: [],
                inventory:     [],
            },
            loading: {
                products:      true,
                sales:         true,
                purchases:     true,
                manufacturing: true,
                inventory:     true,
            },
        });

        onMounted(() => this._loadAll());
    }

    // ── Data loading ──────────────────────────

    async _loadAll() {
        await Promise.all([
            this._load("products",      "product.product",  [], ["name","reference","product_type","sale_price","cost_price","free_to_use_qty","on_hand_qty"]),
            this._load("sales",         "sale.order",       [], ["name","partner_id","date_order","state","total_amount","currency_id"]),
            this._load("purchases",     "purchase.order",   [], ["name","partner_id","date_order","state","total_amount","currency_id"]),
            this._load("manufacturing", "mrp.production",   [], ["name","product_id","product_qty","state","date_planned_start","assignee_id"]),
            this._load("inventory",     "product.product",  [["product_type","=","stockable"]], ["name","reference","on_hand_qty","reserved_qty","free_to_use_qty","product_type"]),
        ]);
    }

    async _load(section, model, domain, fields) {
        try {
            this.state.loading[section] = true;
            const records = await this.orm.searchRead(model, domain, fields, { limit: 40, order: "id desc" });
            this.state.data[section] = records;
        } catch (e) {
            console.error(`[SectionViewWidget] Failed loading ${section}:`, e);
            this.state.data[section] = [];
        } finally {
            this.state.loading[section] = false;
        }
    }

    // ── Helpers exposed to template ───────────

    setView(section, mode) {
        this.state.viewMode[section] = mode;
    }

    isKanban(section) { return this.state.viewMode[section] === "kanban"; }
    isTable(section)  { return this.state.viewMode[section] === "table"; }
    isLoading(section){ return this.state.loading[section]; }
    rows(section)     { return this.state.data[section]; }

    stateLabel(s) { return stateLabel(s); }
    stateCss(s)   { return stateCss(s); }

    fmt(val) {
        if (val === undefined || val === null || val === false) return "—";
        return val;
    }

    fmtCurrency(val) {
        if (val === undefined || val === null || val === false) return "—";
        return new Intl.NumberFormat("en-US", {
            style: "currency", currency: "USD", maximumFractionDigits: 2
        }).format(val);
    }

    fmtDate(val) {
        if (!val) return "—";
        try {
            return new Date(val).toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" });
        } catch { return val; }
    }

    m2oName(val) {
        // Many2one fields come as [id, display_name] or false
        if (!val || val === false) return "—";
        if (Array.isArray(val)) return val[1] || "—";
        return val;
    }

    // ── Navigation (open record) ──────────────

    async openRecord(model, id) {
        await this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: model,
            res_id: id,
            views: [[false, "form"]],
            target: "current",
        });
    }
}

registry.category("fields").add("section_view_widget", {
    component: SectionViewWidget,
});
