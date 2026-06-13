# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api
from odoo.exceptions import UserError


class ProcurementManager(models.AbstractModel):
    _name = 'procurement.manager'
    _description = 'Procurement Manager'

    @api.model
    def evaluate(self, product_id, required_qty, origin, origin_id=None):
        if not product_id:
            return None

        product = self.env['product.product'].browse(product_id) if isinstance(product_id, int) else product_id

        # shortage = required_qty - free_to_use_qty
        shortage = required_qty - product.free_to_use_qty
        if shortage <= 0:
            return None

        if not product.procure_on_demand:
            return None

        if product.procurement_type == 'purchase':
            return self._create_purchase_order(product, shortage, origin)
        elif product.procurement_type == 'manufacture':
            return self._create_manufacturing_order(product, shortage, origin)

        return None

    @api.model
    def _create_purchase_order(self, product, qty, origin):
        # Prevent duplicate procurement: check for existing Draft PO for same product + origin
        existing_po = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('origin', '=', origin),
            ('order_line_ids.product_id', '=', product.id)
        ], limit=1)
        if existing_po:
            return existing_po

        if not product.vendor_id:
            raise UserError(f"Cannot create Purchase Order for {product.name}: no vendor configured.")

        # Find source sales order if applicable
        so_name = origin.split(' — ')[0] if ' — ' in origin else origin
        so = self.env['sale.order'].search([('name', '=', so_name)], limit=1)

        po_vals = {
            'partner_id': product.vendor_id.id,
            'state': 'draft',
            'origin': origin,
            'date_order': fields.Datetime.now(),
        }
        if so:
            po_vals['origin_sale_order_id'] = so.id

        po = self.env['purchase.order'].create(po_vals)

        self.env['purchase.order.line'].create({
            'order_id': po.id,
            'product_id': product.id,
            'quantity': qty,
            'price_unit': product.cost_price,
            'description': product.name,
            'sequence': 10,
        })
        return po

    @api.model
    def _create_manufacturing_order(self, product, qty, origin):
        # Prevent duplicate procurement: check for existing Draft MO for same product + origin
        existing_mo = self.env['mrp.production'].search([
            ('state', '=', 'draft'),
            ('origin', '=', origin),
            ('product_id', '=', product.id)
        ], limit=1)
        if existing_mo:
            return existing_mo

        if not product.bom_id:
            raise UserError(f"Cannot create Manufacturing Order for {product.name}: no Bill of Materials (BoM) configured.")

        mo_vals = {
            'product_id': product.id,
            'product_qty': qty,
            'bom_id': product.bom_id.id,
            'state': 'draft',
            'origin': origin,
        }
        mo = self.env['mrp.production'].create(mo_vals)

        # Explode BoM: copy components from BoM to mrp.production.component
        bom = product.bom_id
        for bom_line in bom.component_ids:
            # Component quantity needed = bom_line.quantity * (MO quantity / bom.product_qty)
            needed_qty = bom_line.quantity * (qty / bom.product_qty)

            self.env['mrp.production.component'].create({
                'production_id': mo.id,
                'product_id': bom_line.product_id.id,
                'quantity_needed': needed_qty,
                'uom_id': bom_line.uom_id.id,
            })

            # Handle cascading procurement: if MO components themselves are MTO, recursively trigger procurement for those too
            if bom_line.product_id.procure_on_demand:
                component_origin = f"MO {mo.name}"
                self.evaluate(bom_line.product_id, needed_qty, component_origin)

        return mo

    @api.model
    def _cron_evaluate_reordering_rules(self):
        """Daily cron method to evaluate reordering rules for MTS products."""
        products = self.env['product.product'].search([
            ('procure_on_demand', '=', True),
            ('min_stock_qty', '>', 0.0)
        ])
        for product in products:
            if product.on_hand_qty < product.min_stock_qty:
                needed_qty = product.min_stock_qty - product.free_to_use_qty
                if needed_qty > 0:
                    self.evaluate(
                        product.id,
                        needed_qty,
                        f"MTS Reordering — {product.name}"
                    )
