# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api

class FinancialInvoice(models.Model):
    _name = 'financial.invoice'
    _description = 'Financial Invoice'
    _inherit = ['audit.mixin']
    _order = 'invoice_date desc, id desc'

    name = fields.Char(string='Number', required=True, copy=False, readonly=True, default=lambda self: '/')
    partner_id = fields.Many2one('res.partner', string='Partner', required=True)
    sale_order_id = fields.Many2one('sale.order', string='Sales Order')
    purchase_order_id = fields.Many2one('purchase.order', string='Purchase Order')
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    invoice_date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('posted', 'Posted'),
        ('paid', 'Paid'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    type = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Supplier Bill')
    ], string='Type', required=True)
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                prefix = 'INV' if vals.get('type') == 'out_invoice' else 'BILL'
                seq = self.env['ir.sequence'].next_by_code('financial.invoice') or '0000'
                vals['name'] = f"{prefix}/{fields.Date.today().year}/{seq}"
        return super().create(vals_list)


class OperationalExpense(models.Model):
    _name = 'operational.expense'
    _description = 'Operational Expense'
    _inherit = ['audit.mixin']
    _order = 'date desc, id desc'

    name = fields.Char(string='Description', required=True)
    category = fields.Selection([
        ('raw_materials', 'Raw Materials'),
        ('purchases', 'Purchases'),
        ('payroll', 'Payroll'),
        ('operations', 'Operations'),
        ('logistics', 'Logistics'),
        ('misc', 'Miscellaneous')
    ], string='Category', default='operations', required=True)
    amount = fields.Monetary(string='Amount', required=True, currency_field='currency_id')
    date = fields.Date(string='Date', required=True, default=fields.Date.context_today)
    notes = fields.Text(string='Notes')
    currency_id = fields.Many2one('res.currency', string='Currency', default=lambda self: self.env.company.currency_id)
