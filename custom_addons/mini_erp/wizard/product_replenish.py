# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProductReplenishWizard(models.TransientModel):
    _name = 'product.replenish.wizard'
    _description = 'Product Replenishment Wizard'

    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
    )

    quantity = fields.Float(
        string='Quantity to Replenish',
        default=1.0,
        required=True,
    )

    replenish_type = fields.Selection(
        [
            ('purchase', 'Purchase'),
            ('manufacture', 'Manufacture'),
        ],
        string='Replenishment Route',
        required=True,
        default='purchase',
    )

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        product_id = self.env.context.get('default_product_id')

        if product_id:
            product = self.env['product.product'].browse(product_id)

            if product.exists() and product.procurement_type:
                res['replenish_type'] = product.procurement_type

        return res

    def action_replenish(self):
        self.ensure_one()

        if self.quantity <= 0:
            raise UserError(
                "Quantity must be greater than zero."
            )

        if not self.replenish_type:
            raise UserError(
                "Please select a replenishment route."
            )

        result = self.env['procurement.manager'].manual_replenish(
            self.product_id,
            self.quantity,
            procurement_type=self.replenish_type,
        )

        if not result:
            return {
                'type': 'ir.actions.act_window_close',
            }

        return {
            'name': result.display_name or result._description,
            'type': 'ir.actions.act_window',
            'res_model': result._name,
            'view_mode': 'form',
            'res_id': result.id,
            'target': 'current',
        }