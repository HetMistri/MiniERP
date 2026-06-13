# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api


class MrpBom(models.Model):
    _name = 'mrp.bom'
    _description = 'Bill of Materials'
    _inherit = ['audit.mixin']
    _order = 'name'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: '/'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        ondelete='restrict'
    )
    product_qty = fields.Float(
        string='Quantity',
        default=1.0,
        required=True
    )
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The BoM reference must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.bom') or '/'
        return super().create(vals_list)
