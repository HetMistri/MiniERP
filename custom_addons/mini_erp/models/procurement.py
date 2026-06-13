# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

import logging
from odoo import models, fields, api
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class ProcurementManager(models.AbstractModel):
    _name = 'procurement.manager'
    _description = 'Procurement Manager'

    @api.model
    def evaluate(self, product_id, required_qty, origin, origin_id=None, visited=None):
        if not product_id or required_qty <= 0:
            return None

        visited = set(visited) if visited else set()
        product = (
            self.env['product.product'].browse(product_id)
            if isinstance(product_id, int)
            else product_id
        )

        if not product.exists():
            raise UserError("Product not found.")

        _logger.info("Evaluating procurement for product %s (qty: %s, origin: %s)", product.name, required_qty, origin)

        if product.id in visited:
            raise UserError(f"Circular procurement detected: product '{product.name}' is already in the procurement path.")
        
        visited.add(product.id)

        free_qty = self._get_effective_free_qty(product, origin)
        shortage = required_qty - free_qty

        if shortage <= 0:
            _logger.info("No shortage for product %s (shortage: %s, free: %s, required: %s)", product.name, shortage, free_qty, required_qty)
            return None

        if not product.procure_on_demand:
            _logger.info("Product %s has shortage of %s but Procure on Demand is disabled.", product.name, shortage)
            return None

        if product.procurement_type == 'purchase':
            return self._create_purchase_order(product, shortage, origin)
        elif product.procurement_type == 'manufacture':
            return self._create_manufacturing_order(product, shortage, origin, visited=visited)

        raise UserError(
            f"Unsupported procurement type "
            f"'{product.procurement_type}' "
            f"for product '{product.name}'."
        )

    @api.model
    def _get_effective_free_qty(self, product, origin):
        free_qty = product.free_to_use_qty

        if not origin:
            return free_qty

        if origin.startswith('SO'):
            so_name = origin.split(' — ')[0]

            so_line = self.env['sale.order.line'].search([
                ('order_id.name', '=', so_name),
                ('product_id', '=', product.id),
            ], limit=1)

            if so_line:
                free_qty += so_line.reserved_qty

        elif origin.startswith('MO'):
            origin_ref = origin.split(' — ')[0]
            parts = origin_ref.split(' ')

            mo_name = (
                parts[1]
                if len(parts) >= 2 and parts[0] == 'MO'
                else parts[0]
            )

            mo_comp = self.env['mrp.production.component'].search([
                ('production_id.name', '=', mo_name),
                ('product_id', '=', product.id),
            ], limit=1)

            if mo_comp:
                free_qty += mo_comp.quantity_reserved

        return free_qty

    @api.model
    def _create_purchase_order(self, product, qty, origin):
        existing_po = self.env['purchase.order'].search([
            ('state', '=', 'draft'),
            ('origin', '=', origin),
            ('order_line_ids.product_id', '=', product.id),
        ], limit=1)

        if existing_po:
            _logger.info("Reusing existing Draft Purchase Order %s for product %s and origin %s", existing_po.name, product.name, origin)
            return existing_po

        if not product.vendor_id:
            raise UserError(
                f"Cannot create Purchase Order for "
                f"{product.name}: no vendor configured."
            )

        so_name = origin.split(' — ')[0] if ' — ' in origin else origin

        so = self.env['sale.order'].search([
            ('name', '=', so_name)
        ], limit=1)

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

        _logger.info("Created Purchase Order %s for vendor %s to procure %s units of product %s (origin: %s)", po.name, product.vendor_id.name, qty, product.name, origin)
        return po

    @api.model
    def _create_manufacturing_order(self, product, qty, origin, visited=None):
        existing_mo = self.env['mrp.production'].search([
            ('state', '=', 'draft'),
            ('origin', '=', origin),
            ('product_id', '=', product.id),
        ], limit=1)

        if existing_mo:
            _logger.info("Reusing existing Draft Manufacturing Order %s for product %s and origin %s", existing_mo.name, product.name, origin)
            return existing_mo

        if not product.bom_id:
            raise UserError(
                f"Cannot create Manufacturing Order for "
                f"{product.name}: no Bill of Materials (BoM) configured."
            )

        bom = product.bom_id

        if bom.product_qty <= 0:
            raise UserError(
                f"BoM '{bom.display_name}' has invalid quantity "
                f"({bom.product_qty})."
            )

        mo = self.env['mrp.production'].create({
            'product_id': product.id,
            'product_qty': qty,
            'bom_id': bom.id,
            'state': 'draft',
            'origin': origin,
        })
        _logger.info("Created Manufacturing Order %s to produce %s units of product %s (origin: %s)", mo.name, qty, product.name, origin)

        for bom_line in bom.component_ids:
            needed_qty = (
                bom_line.quantity *
                (qty / bom.product_qty)
            )

            self.env['mrp.production.component'].create({
                'production_id': mo.id,
                'product_id': bom_line.product_id.id,
                'quantity_needed': needed_qty,
                'uom_id': bom_line.uom_id.id,
            })

            if bom_line.product_id.procure_on_demand:
                component_origin = f"MO {mo.name}"
                self.evaluate(bom_line.product_id, needed_qty, component_origin, visited=visited)

        return mo

    @api.model
    def _cron_evaluate_reordering_rules(self):
        products = self.env['product.product'].search([
            ('procure_on_demand', '=', True),
            ('min_stock_qty', '>', 0.0),
        ])

        for product in products:
            if product.on_hand_qty < product.min_stock_qty:
                needed_qty = (
                    product.min_stock_qty -
                    product.free_to_use_qty
                )

                if needed_qty > 0:
                    self.evaluate(
                        product.id,
                        needed_qty,
                        f"MTS Reordering — {product.name}"
                    )

    @api.model
    def manual_replenish(self, product, qty, procurement_type=None):
        proc_type = procurement_type or product.procurement_type

        if proc_type == 'purchase':
            return self._create_purchase_order(
                product,
                qty,
                f"Manual Replenishment — {product.name}"
            )

        if proc_type == 'manufacture':
            return self._create_manufacturing_order(
                product,
                qty,
                f"Manual Replenishment — {product.name}"
            )

        raise UserError(
            f"Please select a valid replenishment route "
            f"for product '{product.display_name}'."
        )