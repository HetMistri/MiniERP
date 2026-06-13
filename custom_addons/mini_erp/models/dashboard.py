# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api
from odoo.exceptions import AccessError


class DashboardData(models.TransientModel):
    _name = 'dashboard.data'
    _description = 'Dashboard Data'

    # Filter Toggles
    filter_my_sales = fields.Boolean(string="My Sales Only", default=False)
    filter_my_purchases = fields.Boolean(string="My Purchases Only", default=False)
    filter_my_manufacturing = fields.Boolean(string="My MOs Only", default=False)

    # Search Bar
    search_query = fields.Char(string="Global Search", default="")
    search_sale_ids = fields.Many2many('sale.order', compute='_compute_search_results')
    search_product_ids = fields.Many2many('product.product', compute='_compute_search_results')
    search_purchase_ids = fields.Many2many('purchase.order', compute='_compute_search_results')
    search_mo_ids = fields.Many2many('mrp.production', compute='_compute_search_results')

    # Granular KPIs - Sales
    so_all = fields.Integer(string="All Sales", compute='_compute_sale_kpis')
    so_draft = fields.Integer(string="Draft Sales", compute='_compute_sale_kpis')
    so_confirmed = fields.Integer(string="Confirmed Sales", compute='_compute_sale_kpis')
    so_partial = fields.Integer(string="Partially Delivered", compute='_compute_sale_kpis')
    so_delivered = fields.Integer(string="Fully Delivered", compute='_compute_sale_kpis')

    # Granular KPIs - Purchase
    po_all = fields.Integer(string="All Purchases", compute='_compute_purchase_kpis')
    po_draft = fields.Integer(string="Draft Purchases", compute='_compute_purchase_kpis')
    po_confirmed = fields.Integer(string="Confirmed Purchases", compute='_compute_purchase_kpis')
    po_partial = fields.Integer(string="Partially Received", compute='_compute_purchase_kpis')
    po_received = fields.Integer(string="Fully Received", compute='_compute_purchase_kpis')
    po_late = fields.Integer(string="Late Purchases", compute='_compute_purchase_kpis')

    # Granular KPIs - Manufacturing
    mo_all = fields.Integer(string="All MOs", compute='_compute_mfg_kpis')
    mo_draft = fields.Integer(string="Draft MOs", compute='_compute_mfg_kpis')
    mo_confirmed = fields.Integer(string="Confirmed MOs", compute='_compute_mfg_kpis')
    mo_progress = fields.Integer(string="In Progress MOs", compute='_compute_mfg_kpis')
    mo_done = fields.Integer(string="Done MOs", compute='_compute_mfg_kpis')
    mo_to_close = fields.Integer(string="To Close MOs", compute='_compute_mfg_kpis')

    # Other KPIs
    delayed_orders = fields.Integer(string='Delayed Orders', compute='_compute_global_kpis')
    low_stock_products = fields.Integer(string='Low Stock Products', compute='_compute_global_kpis')
    
    # Last 10 audit logs
    recent_audit_log_ids = fields.Many2many('audit.log', compute='_compute_recent_audit_logs')

    @api.depends('filter_my_sales')
    def _compute_sale_kpis(self):
        sale_order_model = self.env['sale.order']
        for rec in self:
            domain = []
            if rec.filter_my_sales:
                domain.append(('user_id', '=', self.env.user.id))
            
            sales = sale_order_model.search(domain)
            rec.so_all = len(sales)
            rec.so_draft = len(sales.filtered(lambda s: s.state == 'draft'))
            rec.so_confirmed = len(sales.filtered(lambda s: s.state == 'confirmed'))
            rec.so_partial = len(sales.filtered(lambda s: s.state == 'partially_delivered'))
            rec.so_delivered = len(sales.filtered(lambda s: s.state == 'fully_delivered'))

    @api.depends('filter_my_purchases')
    def _compute_purchase_kpis(self):
        purchase_order_model = self.env['purchase.order']
        for rec in self:
            domain = []
            if rec.filter_my_purchases:
                domain.append(('user_id', '=', self.env.user.id))
            
            purchases = purchase_order_model.search(domain)
            rec.po_all = len(purchases)
            rec.po_draft = len(purchases.filtered(lambda p: p.state == 'draft'))
            rec.po_confirmed = len(purchases.filtered(lambda p: p.state == 'confirmed'))
            rec.po_partial = len(purchases.filtered(lambda p: p.state == 'partially_received'))
            rec.po_received = len(purchases.filtered(lambda p: p.state == 'fully_received'))
            rec.po_late = len(purchases.filtered(lambda p: p.state == 'confirmed' and p.date_order and p.date_order.date() < fields.Date.today()))

    @api.depends('filter_my_manufacturing')
    def _compute_mfg_kpis(self):
        mrp_production_model = self.env['mrp.production'] if 'mrp.production' in self.env else None
        for rec in self:
            if mrp_production_model is not None:
                domain = []
                if rec.filter_my_manufacturing:
                    domain.append(('assignee_id', '=', self.env.user.id))
                
                mos = mrp_production_model.search(domain)
                rec.mo_all = len(mos)
                rec.mo_draft = len(mos.filtered(lambda m: m.state == 'draft'))
                rec.mo_confirmed = len(mos.filtered(lambda m: m.state == 'confirmed'))
                rec.mo_progress = len(mos.filtered(lambda m: m.state == 'progress'))
                rec.mo_done = len(mos.filtered(lambda m: m.state == 'done'))
                rec.mo_to_close = len(mos.filtered(lambda m: m.state == 'progress' and all(wo.state == 'done' for wo in m.work_order_ids)))
            else:
                rec.mo_all = rec.mo_draft = rec.mo_confirmed = rec.mo_progress = rec.mo_done = rec.mo_to_close = 0

    @api.depends('filter_my_sales')
    def _compute_global_kpis(self):
        sale_order_model = self.env['sale.order']
        product_product_model = self.env['product.product']
        try:
            sale_order_model.check_access('read')
            has_sale = True
        except AccessError:
            has_sale = False

        try:
            product_product_model.check_access('read')
            has_product = True
        except AccessError:
            has_product = False
            
            
        for rec in self:
            if has_sale:
                so_domain = [
                    ('state', 'in', ('confirmed', 'partially_delivered')),
                    ('expected_date', '<', fields.Date.today())
                ]
                if rec.filter_my_sales:
                    so_domain.append(('user_id', '=', self.env.user.id))
                rec.delayed_orders = sale_order_model.search_count(so_domain)
            else:
                rec.delayed_orders = 0
                
            
            if has_product:
                products = product_product_model.search([('product_type', '=', 'stockable')])
                rec.low_stock_products = len(products.filtered(lambda p: p.free_to_use_qty <= 0))
            else:
                rec.low_stock_products = 0
 
    def _compute_recent_audit_logs(self):
        try:
            self.env['audit.log'].check_access('read')
            has_access = True
        except AccessError:
            has_access = False
            
        for rec in self:
            if has_access:
                rec.recent_audit_log_ids = self.env['audit.log'].search([], limit=10).ids
            else:
                rec.recent_audit_log_ids = False

    @api.depends('search_query')
    def _compute_search_results(self):
        for rec in self:
            q = rec.search_query.strip() if rec.search_query else ""
            if not q or len(q) < 2:
                rec.search_sale_ids = self.env['sale.order']
                rec.search_product_ids = self.env['product.product']
                rec.search_purchase_ids = self.env['purchase.order']
                rec.search_mo_ids = self.env['mrp.production']
                continue

            rec.search_sale_ids = self.env['sale.order'].search([('name', 'ilike', q)], limit=5)
            rec.search_product_ids = self.env['product.product'].search([
                '|', ('name', 'ilike', q), ('reference', 'ilike', q)
            ], limit=5)
            rec.search_purchase_ids = self.env['purchase.order'].search([('name', 'ilike', q)], limit=5)
            if 'mrp.production' in self.env:
                rec.search_mo_ids = self.env['mrp.production'].search([('name', 'ilike', q)], limit=5)
            else:
                rec.search_mo_ids = self.env['mrp.production']

    @api.model
    def action_open_dashboard(self):
        record = self.create({})
        return {
            'name': 'Dashboard',
            'type': 'ir.actions.act_window',
            'res_model': 'dashboard.data',
            'view_mode': 'form',
            'res_id': record.id,
            'target': 'current',
            'context': {'form_view_ref': 'mini_erp.view_dashboard_data_form'},
        }

    # Search Actions
    def action_search(self):
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_clear_search(self):
        self.write({'search_query': ''})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    # Sidebar Navigation Actions
    def action_view_products(self):
        return {
            'name': 'Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_boms(self):
        return {
            'name': 'Bills of Materials',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.bom',
            'view_mode': 'list,form',
            'target': 'current',
        }

    # Redirection Action Helpers
    def _action_view_sales_by_state(self, state=None):
        domain = []
        if state:
            domain.append(('state', '=', state))
        if self.filter_my_sales:
            domain.append(('user_id', '=', self.env.user.id))
        return {
            'name': f'Sales Orders ({state or "All"})',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'domain': domain,
            'target': 'current',
        }

    def action_view_sales(self):
        return self._action_view_sales_by_state()

    def action_view_so_draft(self):
        return self._action_view_sales_by_state('draft')

    def action_view_so_confirmed(self):
        return self._action_view_sales_by_state('confirmed')

    def action_view_so_partial(self):
        return self._action_view_sales_by_state('partially_delivered')

    def action_view_so_delivered(self):
        return self._action_view_sales_by_state('fully_delivered')

    def _action_view_purchase_by_state(self, state=None, domain_override=None):
        domain = []
        if domain_override is not None:
            domain.extend(domain_override)
        elif state:
            domain.append(('state', '=', state))
        if self.filter_my_purchases:
            domain.append(('user_id', '=', self.env.user.id))
        return {
            'name': f'Purchase Orders ({state or "All"})',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_pos(self):
        return self._action_view_purchase_by_state()

    def action_view_po_draft(self):
        return self._action_view_purchase_by_state('draft')

    def action_view_po_confirmed(self):
        return self._action_view_purchase_by_state('confirmed')

    def action_view_po_partial(self):
        return self._action_view_purchase_by_state('partially_received')

    def action_view_po_received(self):
        return self._action_view_purchase_by_state('fully_received')

    def action_view_po_late(self):
        domain_override = [
            ('state', '=', 'confirmed'),
            ('date_order', '<', fields.Date.today())
        ]
        return self._action_view_purchase_by_state(state='Late', domain_override=domain_override)

    def _action_view_mrp_by_state(self, state=None, domain_override=None):
        domain = []
        if domain_override is not None:
            domain.extend(domain_override)
        elif state:
            domain.append(('state', '=', state))
        if self.filter_my_manufacturing:
            domain.append(('assignee_id', '=', self.env.user.id))
        return {
            'name': f'Manufacturing Orders ({state or "All"})',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }

    def action_view_mos(self):
        return self._action_view_mrp_by_state()

    def action_view_mo_draft(self):
        return self._action_view_mrp_by_state('draft')

    def action_view_mo_confirmed(self):
        return self._action_view_mrp_by_state('confirmed')

    def action_view_mo_progress(self):
        return self._action_view_mrp_by_state('progress')

    def action_view_mo_done(self):
        return self._action_view_mrp_by_state('done')

    def action_view_mo_to_close(self):
        mrp_production_model = self.env['mrp.production']
        domain = [('state', '=', 'progress')]
        if self.filter_my_manufacturing:
            domain.append(('assignee_id', '=', self.env.user.id))
        mos = mrp_production_model.search(domain)
        to_close_ids = mos.filtered(lambda m: all(wo.state == 'done' for wo in m.work_order_ids)).ids
        return self._action_view_mrp_by_state(state='To Close', domain_override=[('id', 'in', to_close_ids)])

    def action_view_low_stock(self):
        products = self.env['product.product'].search([('product_type', '=', 'stockable')])
        low_stock_ids = products.filtered(lambda p: p.free_to_use_qty <= 0).ids
        return {
            'name': 'Low Stock Products',
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'view_mode': 'list,form',
            'domain': [('id', 'in', low_stock_ids)],
            'target': 'current',
        }

    def action_view_delayed_orders(self):
        domain = [
            ('state', 'in', ('confirmed', 'partially_delivered')),
            ('expected_date', '<', fields.Date.today())
        ]
        if self.filter_my_sales:
            domain.append(('user_id', '=', self.env.user.id))
        return {
            'name': 'Delayed Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'domain': domain,
            'target': 'current',
        }
