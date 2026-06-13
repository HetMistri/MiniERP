from odoo import models, fields, api
from odoo.exceptions import UserError

class ProcurementManager(models.AbstractModel):
    _name = 'procurement.manager'
    _description = 'Procurement Manager'


    @api.model
    def evaluate(self, product_id, required_qty, origin, origin_id=None):
        if not product_id or required_qty <= 0:
            return None

        product = (
            self.env['product.product'].browse(product_id)
            if isinstance(product_id, int)
            else product_id
        )

        if not product.exists():
            raise UserError("Product not found.")

        free_qty = self._get_effective_free_qty(product, origin)
        shortage = required_qty - free_qty

        if shortage <= 0:
            return None

        if not product.procure_on_demand:
            return None

        if product.procurement_type == 'purchase':
            return self._create_purchase_order(
                product,
                shortage,
                origin
            )

        if product.procurement_type == 'manufacture':
            return self._create_manufacturing_order(
                product,
                shortage,
                origin
            )

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

        return po

    @api.model
    def _create_manufacturing_order(self, product, qty, origin):
        existing_mo = self.env['mrp.production'].search([
            ('state', '=', 'draft'),
            ('origin', '=', origin),
            ('product_id', '=', product.id),
        ], limit=1)

        if existing_mo:
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
                self.evaluate(
                    bom_line.product_id,
                    needed_qty,
                    f"MO {mo.name}"
                )

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

