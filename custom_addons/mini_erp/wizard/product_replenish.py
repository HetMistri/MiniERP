# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductReplenishWizard(models.TransientModel):
    _name = 'product.replenish.wizard'
    _description = 'Product Replenishment Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity to Order', default=1.0, required=True)

    def action_replenish(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError("Quantity must be greater than zero.")
        res = self.env['procurement.manager'].manual_replenish(
            self.product_id,
            self.quantity
        )
        if res:
            return {
                'name': f"Procured {res._description}",
                'type': 'ir.actions.act_window',
                'res_model': res._name,
                'view_mode': 'form',
                'res_id': res.id,
                'target': 'current',
            }
        return {'type': 'ir.actions.act_window_close'}
