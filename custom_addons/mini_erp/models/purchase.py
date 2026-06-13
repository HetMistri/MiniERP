# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _description = 'Purchase Order'
    _inherit = ['audit.mixin']
    _order = 'name desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: '/'
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Vendor',
        required=True,
        ondelete='restrict'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    date_order = fields.Datetime(string='Order Date', default=fields.Datetime.now, required=True)
    total_amount = fields.Monetary(string='Total Amount', currency_field='currency_id', compute='_compute_total_amount', store=True)
    user_id = fields.Many2one('res.users', string='Purchase Representative', default=lambda self: self.env.user, required=True)
    notes = fields.Text(string='Notes')
    origin = fields.Char(string='Source Document')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company, required=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    order_line = fields.One2many('purchase.order.line', 'order_id', string='Order Lines')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The Purchase Order reference must be unique!'),
    ]

    @api.depends('order_line.subtotal')
    def _compute_total_amount(self):
        for order in self:
            order.total_amount = sum(line.subtotal for line in order.order_line)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order') or '/'
        return super().create(vals_list)


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _description = 'Purchase Order Line'
    _inherit = ['audit.mixin']
    _order = 'sequence, id'

    order_id = fields.Many2one('purchase.order', string='Purchase Reference', required=True, ondelete='cascade')
    sequence = fields.Integer(default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity', default=1.0, required=True)
    received_qty = fields.Float(string='Received Qty', default=0.0, required=True)
    price_unit = fields.Monetary(string='Unit Price', currency_field='currency_id', required=True)
    subtotal = fields.Monetary(string='Subtotal', currency_field='currency_id', compute='_compute_subtotal', store=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id', store=True, readonly=True)
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
