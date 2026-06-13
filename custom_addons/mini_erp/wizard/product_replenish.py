# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductReplenishWizard(models.TransientModel):
    _name = 'product.replenish.wizard'
    _description = 'Product Replenishment Wizard'

    product_id = fields.Many2one('product.product', string='Product', required=True)
    quantity = fields.Float(string='Quantity to Order', default=1.0, required=True)
    replenish_type = fields.Selection([
        ('purchase', 'Purchase'),
        ('manufacture', 'Manufacture'),
    ], string='Replenishment Route', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if 'product_id' in res or self._context.get('default_product_id'):
            prod_id = res.get('product_id') or self._context.get('default_product_id')
            product = self.env['product.product'].browse(prod_id)
            if product.exists():
                res['replenish_type'] = product.procurement_type or 'purchase'
        return res

    def action_replenish(self):
        self.ensure_one()
        if self.quantity <= 0:
            raise UserError("Quantity must be greater than zero.")
        res = self.env['procurement.manager'].manual_replenish(
            self.product_id,
            self.quantity,
            procurement_type=self.replenish_type
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
