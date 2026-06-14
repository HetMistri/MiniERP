# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


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

            if product.exists():
                if product.procurement_type:
                    res['replenish_type'] = product.procurement_type
                elif product.bom_id:
                    res['replenish_type'] = 'manufacture'
                elif product.vendor_id:
                    res['replenish_type'] = 'purchase'

                _logger.info(
                    "REPLENISH DEBUG -> Product=%s, ID=%s, procurement_type=%s, "
                    "has_vendor=%s, has_bom=%s, auto_route=%s",
                    product.name, product.id, product.procurement_type,
                    bool(product.vendor_id), bool(product.bom_id),
                    res.get('replenish_type'),
                )

        return res

    def action_replenish(self):
        self.ensure_one()

        if self.quantity <= 0:
            raise UserError(
                "Quantity must be greater than zero."
            )

        if not self.replenish_type:
            raise UserError(
                f"Cannot replenish product '{self.product_id.display_name}': "
                f"no procurement type is configured. "
                f"Go to the product form and set 'Procurement Type' "
                f"to 'Purchase' or 'Manufacture' under the Procurement Settings tab."
            )

        if self.replenish_type == 'purchase' and not self.product_id.vendor_id:
            raise UserError(
                f"Cannot replenish product '{self.product_id.display_name}' "
                f"via Purchase: no vendor is configured. "
                f"Go to the product form's Procurement Settings tab "
                f"and configure a Vendor, or switch the Procurement Type "
                f"to 'Manufacture' if this product has a Bill of Materials."
            )

        if self.replenish_type == 'manufacture' and not self.product_id.bom_id:
            raise UserError(
                f"Cannot replenish product '{self.product_id.display_name}' "
                f"via Manufacture: no Bill of Materials (BoM) is configured. "
                f"Go to the product form's Procurement Settings tab "
                f"and assign a BoM, or switch the Procurement Type "
                f"to 'Purchase' if a vendor is available."
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
