# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import http, fields
from odoo.http import request


class MiniErpDashboardController(http.Controller):

    @http.route('/dashboard/data', type='json', auth='user', methods=['POST'])
    def get_dashboard_data(self):
        sale_order_model = request.env['sale.order']
        purchase_order_model = request.env['purchase.order']
        mrp_production_model = request.env['mrp.production']
        product_product_model = request.env['product.product']
        audit_log_model = request.env['audit.log']

        products = product_product_model.search([('product_type', '=', 'stockable')])
        low_stock_count = len(products.filtered(lambda p: p.free_to_use_qty <= 0))

        audit_logs = audit_log_model.search([], limit=10)
        audit_logs_list = [{
            'id': log.id,
            'model_name': log.model_name,
            'record_id': log.record_id,
            'field_name': log.field_name or '',
            'old_value': log.old_value or '',
            'new_value': log.new_value or '',
            'action': log.action,
            'user': log.user_id.name,
            'timestamp': fields.Datetime.to_string(log.timestamp),
            'display_name': log.display_name or ''
        } for log in audit_logs]

        data = {
            'total_sales_orders': sale_order_model.search_count([]),
            'pending_deliveries': sale_order_model.search_count([('state', 'in', ('confirmed', 'partially_delivered'))]),
            'total_mo': mrp_production_model.search_count([]) if 'mrp.production' in request.env else 0,
            'delayed_orders': sale_order_model.search_count([
                ('state', 'in', ('confirmed', 'partially_delivered')),
                ('expected_date', '<', fields.Date.today())
            ]),
            'total_po': purchase_order_model.search_count([]),
            'partial_receipts': purchase_order_model.search_count([('state', '=', 'partially_received')]),
            'low_stock_products': low_stock_count,
            'recent_audit_logs': audit_logs_list,
        }
        return data
