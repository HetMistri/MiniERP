# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api

# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError


class PurchaseOrder(models.Model):
    _name = 'purchase.order'
    _description = 'Purchase Order'
    _inherit = ['audit.mixin']
    _order = 'name desc, id desc'

    name = fields.Char(string='PO Number', required=True, copy=False, readonly=True, default=lambda self: '/')
    partner_id = fields.Many2one('res.partner', string='Vendor', domain="[('is_vendor', '=', True)]", required=True)
    partner_address = fields.Char(string='Vendor Address', compute='_compute_partner_address', store=True, readonly=False)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('partially_received', 'Partially Received'),
        ('fully_received', 'Fully Received'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, copy=False)
    order_line_ids = fields.One2many('purchase.order.line', 'order_id', string='Order Lines', copy=True)
    date_order = fields.Datetime(string='Order Date', required=True, default=fields.Datetime.now)
    total_amount = fields.Monetary(string='Total Amount', compute='_compute_total_amount', store=True, currency_field='currency_id')
    user_id = fields.Many2one('res.users', string='Buyer', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')
    origin = fields.Char(string='Source Document')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    # Integration Field
    origin_sale_order_id = fields.Many2one('sale.order', string='Source Sales Order', copy=False)

    @api.depends('partner_id', 'partner_id.street', 'partner_id.city', 'partner_id.state_id', 'partner_id.country_id')
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

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('purchase.order') or '/'
        return super().create(vals_list)

    def unlink(self):
        if not self.env.context.get('force_delete'):
            for order in self:
                if order.state != 'draft':
                    raise UserError("You can only delete purchase orders in draft state.")
        return super().unlink()

    def action_confirm(self):
        self.ensure_one()
        if not self.partner_id:
            raise UserError("A vendor must be specified.")
        if not self.order_line_ids:
            raise UserError("An order must have at least one line.")
        
        for line in self.order_line_ids:
            if line.quantity <= 0:
                raise UserError("Quantity must be greater than zero.")
            
        self.write({'state': 'confirmed'})

    def action_receive(self):
        self.ensure_one()
        if self.state not in ('confirmed', 'partially_received'):
            raise UserError("You can only receive items for confirmed or partially received purchase orders.")
        return {
            'name': 'Receive Purchase Order',
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order.receive',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    def action_cancel(self):
        for order in self:
            if order.state not in ('draft', 'confirmed'):
                raise UserError("Only draft or confirmed orders can be cancelled.")
            order.write({'state': 'cancelled'})

    def action_view_source_sale_order(self):
        self.ensure_one()
        if not self.origin_sale_order_id:
            raise UserError("This Purchase Order has no source Sales Order.")
        return {
            'name': 'Source Sales Order',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'form',
            'res_id': self.origin_sale_order_id.id,
            'target': 'current',
        }

    def action_view_audit_logs(self):
        """Open audit logs filtered to Purchase module."""
        self.ensure_one()
        return {
            'name': 'Audit Logs — Purchases',
            'type': 'ir.actions.act_window',
            'res_model': 'audit.log',
            'view_mode': 'list,form',
            'domain': [('model_name', '=', 'purchase.order')],
            'context': {'search_default_res_id': self.id},
        }


class PurchaseOrderLine(models.Model):
    _name = 'purchase.order.line'
    _description = 'Purchase Order Line'

    order_id = fields.Many2one('purchase.order', string='Order Reference', required=True, ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    description = fields.Text(string='Description')
    quantity = fields.Float(string='Quantity Ordered', required=True, default=1.0)
    received_qty = fields.Float(string='Quantity Received', readonly=True, default=0.0)
    price_unit = fields.Monetary(string='Unit Price', required=True, default=0.0, currency_field='currency_id')
    subtotal = fields.Monetary(string='Subtotal', compute='_compute_subtotal', store=True, currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', related='order_id.currency_id', readonly=True)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.price_unit = self.product_id.cost_price
            self.description = self.product_id.name

    @api.depends('quantity', 'price_unit')
    def _compute_subtotal(self):
        for line in self:
            line.subtotal = line.quantity * line.price_unit
