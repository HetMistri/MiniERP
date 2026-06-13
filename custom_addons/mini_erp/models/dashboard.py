# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api


class DashboardData(models.TransientModel):
    _name = 'dashboard.data'
    _description = 'Dashboard Data'

    total_sales_orders = fields.Integer(string='Total Sales Orders', compute='_compute_kpis')
    pending_deliveries = fields.Integer(string='Pending Deliveries', compute='_compute_kpis')
    total_mo = fields.Integer(string='Total MOs', compute='_compute_kpis')
    delayed_orders = fields.Integer(string='Delayed Orders', compute='_compute_kpis')
    total_po = fields.Integer(string='Total POs', compute='_compute_kpis')
    partial_receipts = fields.Integer(string='Partial Receipts', compute='_compute_kpis')
    low_stock_products = fields.Integer(string='Low Stock Products', compute='_compute_kpis')
    
    # Last 10 audit logs
    recent_audit_log_ids = fields.Many2many('audit.log', compute='_compute_recent_audit_logs')

    def _compute_kpis(self):
        sale_order_model = self.env['sale.order']
        purchase_order_model = self.env['purchase.order']
        mrp_production_model = self.env['mrp.production']
        product_product_model = self.env['product.product']

        for rec in self:
            rec.total_sales_orders = sale_order_model.search_count([])
            rec.pending_deliveries = sale_order_model.search_count([('state', 'in', ('confirmed', 'partially_delivered'))])
            
            if 'mrp.production' in self.env:
                rec.total_mo = mrp_production_model.search_count([])
            else:
                rec.total_mo = 0
                
            rec.delayed_orders = sale_order_model.search_count([
                ('state', 'in', ('confirmed', 'partially_delivered')),
                ('expected_date', '<', fields.Date.today())
            ])
            rec.total_po = purchase_order_model.search_count([])
            rec.partial_receipts = purchase_order_model.search_count([('state', '=', 'partially_received')])
            
            # Low stock products: stockable products with free_to_use_qty <= 0
            products = product_product_model.search([('product_type', '=', 'stockable')])
            rec.low_stock_products = len(products.filtered(lambda p: p.free_to_use_qty <= 0))

    def _compute_recent_audit_logs(self):
        for rec in self:
            rec.recent_audit_log_ids = self.env['audit.log'].search([], limit=10).ids

    @api.model
    def action_open_dashboard(self):
        # Create a transient record to trigger computes, and display it
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

    # Action methods for clicking cards
    def action_view_sales(self):
        return {
            'name': 'Sales Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'target': 'current',
        }

    def action_view_pending_deliveries(self):
        return {
            'name': 'Pending Deliveries',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'domain': [('state', 'in', ('confirmed', 'partially_delivered'))],
            'target': 'current',
        }

    def action_view_mos(self):
        return {
            'name': 'Manufacturing Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_delayed_orders(self):
        return {
            'name': 'Delayed Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form,kanban',
            'domain': [
                ('state', 'in', ('confirmed', 'partially_delivered')),
                ('expected_date', '<', fields.Date.today())
            ],
            'target': 'current',
        }

    def action_view_pos(self):
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'target': 'current',
        }

    def action_view_partial_receipts(self):
        return {
            'name': 'Partial Receipts',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('state', '=', 'partially_received')],
            'target': 'current',
        }

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
