# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _name = 'sale.order'
    _description = 'Sales Order'
    _inherit = ['audit.mixin']
    _order = 'name desc, id desc'

    name = fields.Char(string='SO Number', required=True, copy=False, readonly=True, default=lambda self: '/')
    partner_id = fields.Many2one('res.partner', string='Customer', domain="[('is_customer', '=', True)]", required=True)
    partner_address = fields.Char(string='Customer Address', compute='_compute_partner_address', store=True, readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_delivered', 'Partially Delivered'),
        ('fully_delivered', 'Fully Delivered'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, copy=False)
    order_line_ids = fields.One2many('sale.order.line', 'order_id', string='Order Lines', copy=True)
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    expected_date = fields.Date(string='Expected Delivery Date')
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', store=True, currency_field='currency_id')
    user_id = fields.Many2one('res.users', string='Salesperson', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Smart Buttons & Counts
    purchase_order_count = fields.Integer(string='Purchase Order Count', compute='_compute_purchase_order_count')
    delivery_count = fields.Integer(string='Delivery Count', compute='_compute_delivery_count')
    mrp_production_count = fields.Integer(string='Manufacturing Order Count', compute='_compute_mrp_production_count')

    @api.depends('partner_id')
    def _compute_partner_address(self):
        for order in self:
            p = order.partner_id
            if p:
                parts = [p.street, p.city, p.state_id.name if p.state_id else None, p.country_id.name if p.country_id else None]
                order.partner_address = ', '.join(filter(None, parts))
            else:
                order.partner_address = ''

    @api.depends('order_line_ids.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(order.order_line_ids.mapped('subtotal'))

    def _compute_purchase_order_count(self):
        for order in self:
            order.purchase_order_count = self.env['purchase.order'].search_count([
                ('origin_sale_order_id', '=', order.id)
            ])

    def _compute_delivery_count(self):
        for order in self:
            order.delivery_count = self.env['stock.ledger'].search_count([
                ('reference', '=', order.name),
                ('transaction_type', '=', 'sale_delivery')
            ])

    def _compute_mrp_production_count(self):
        for order in self:
            if 'mrp.production' in self.env:
                order.mrp_production_count = self.env['mrp.production'].search_count([
                    ('origin', '=', order.name)
                ])
            else:
                order.mrp_production_count = 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('sale.order') or '/'
        return super().create(vals_list)

    def unlink(self):
        for order in self:
            if order.state != 'draft':
                raise UserError("You can only delete sales orders in draft state.")
        return super().unlink()

    def action_confirm(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError("A customer must be specified.")
        if not self.order_line_ids:
            raise UserError("An order must have at least one line.")
        
        for line in self.order_line_ids:
            if line.quantity <= 0:
                raise UserError("Quantity must be greater than zero.")
            
            # Enforce stock check if not allow_negative_stock
            if line.product_id.product_type == 'stockable' and not self.env.company.allow_negative_stock:
                if line.product_id.free_to_use_qty < line.quantity and not line.product_id.procure_on_demand:
                    raise UserError(
                        f"Insufficient stock for product '{line.product_id.name}' and no procurement configured.\n"
                        f"Requested: {line.quantity}, Free: {line.product_id.free_to_use_qty}"
                    )

            # Reserve stock
            line.reserved_qty = line.quantity
            self.env['product.product']._update_reserved_qty(line.product_id.id, line.quantity)
            
        self.write({'state': 'confirmed'})
        # Trigger procurement evaluation
        self._trigger_procurement_evaluation()

    def action_deliver(self):
        self.ensure_one()
        if self.state not in ('confirmed', 'partially_delivered'):
            raise UserError("You can only deliver confirmed or partially delivered orders.")
        return {
            'name': 'Deliver Sales Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order.deliver',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_cancel(self):
        for order in self:
            if order.state not in ('draft', 'confirmed'):
                raise UserError("Only draft or confirmed orders can be cancelled.")
            for line in order.order_line_ids:
                if line.reserved_qty > 0:
                    self.env['product.product']._update_reserved_qty(line.product_id.id, -line.reserved_qty)
                    line.reserved_qty = 0.0
            order.write({'state': 'cancelled'})

    def _trigger_procurement_evaluation(self):
        """Trigger procurement engine for each confirmed sale order line."""
        for line in self.order_line_ids:
            if line.product_id.procure_on_demand:
                origin_name = f"{self.name} — {line.product_id.name}"
                self.env['procurement.manager'].evaluate(
                    line.product_id.id,
                    line.quantity,
                    origin_name
                )

    # View Actions
    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'name': 'Purchase Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('origin_sale_order_id', '=', self.id)],
            'context': {'default_origin_sale_order_id': self.id},
        }

    def action_view_deliveries(self):
        self.ensure_one()
        return {
            'name': 'Stock Moves (Deliveries)',
            'type': 'ir.actions.act_window',
            'res_model': 'stock.ledger',
            'view_mode': 'list,form',
            'domain': [('reference', '=', self.name), ('transaction_type', '=', 'sale_delivery')],
        }

    def action_view_mrp_productions(self):
        self.ensure_one()
        if 'mrp.production' not in self.env:
            raise UserError("Manufacturing module is not loaded.")
        return {
            'name': 'Manufacturing Orders',
            'type': 'ir.actions.act_window',
            'res_model': 'mrp.production',
            'view_mode': 'list,form',
            'domain': [('origin', '=', self.name)],
        }

    def action_view_audit_logs(self):
        """Open audit logs filtered to Sales module."""
        self.ensure_one()
        return {
            'name': 'Audit Logs — Sales',
            'type': 'ir.actions.act_window',
            'res_model': 'audit.log',
            'view_mode': 'list,form',
            'domain': [('model', '=', 'sale.order')],
            'context': {'search_default_res_id': self.id},
        }


class SaleOrderLine(models.Model):
    _name = 'sale.order.line'
    _description = 'Sales Order Line'

    order_id = fields.Many2one('sale.order', string='Order Reference', required=True, ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity Ordered', required=True, default=1.0)
    delivered_qty = fields.Float(string='Quantity Delivered', readonly=True, default=0.0)
    reserved_qty = fields.Float(string='Quantity Reserved', readonly=True, default=0.0)
    price_unit = fields.Monetary(string='Unit Price', required=True, default=0.0, currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    stock_availability = fields.Char(string='Stock Availability', compute='_compute_stock_availability')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.sale_price
            self.description = self.product_id.name

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit

    @api.depends('product_id', 'product_id.on_hand_qty', 'product_id.reserved_qty', 'product_id.free_to_use_qty')
    def _compute_stock_availability(self):
        for line in self:
            if line.product_id:
                line.stock_availability = (
                    f"On Hand: {line.product_id.on_hand_qty} | "
                    f"Reserved: {line.product_id.reserved_qty} | "
                    f"Free: {line.product_id.free_to_use_qty}"
                )
            else:
                line.stock_availability = "N/A"
