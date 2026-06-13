from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleOrderDeliver(models.TransientModel):
    _name = 'sale.order.deliver'
    _description = 'Deliver Sales Order'

    order_id = fields.Many2one('sale.order', string='Sales Order', required=True)
    line_ids = fields.One2many('sale.order.deliver.line', 'wizard_id', string='Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['sale.order'].browse(active_id)
            res['order_id'] = order.id
            lines = []
            for line in order.order_line_ids:
                qty_to_deliver = line.quantity - line.delivered_qty
                if qty_to_deliver > 0:
                    lines.append((0, 0, {
                        'sale_line_id': line.id,
                        'product_id': line.product_id.id,
                        'qty_ordered': line.quantity,
                        'qty_delivered': qty_to_deliver,
                    }))
            res['line_ids'] = lines
        return res

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        
        for line in self.line_ids:
            if line.qty_delivered <= 0:
                continue
            
            product = line.product_id
            # Perform availability validation for stockable items
            if product.product_type == 'stockable':
                if product.on_hand_qty < line.qty_delivered:
                    raise UserError(
                        f"Insufficient stock for '{product.name}'. "
                        f"On Hand: {product.on_hand_qty}, Delivery: {line.qty_delivered}"
                    )

            # Create Stock Ledger Entry (negative quantity for outbound)
            self.env['stock.ledger']._update_stock(
                product.id,
                -line.qty_delivered,
                order.name,
                'sale_delivery',
                notes=f"Delivery for Sales Order {order.name}"
            )
            
            # Update Sales Order Line
            sale_line = line.sale_line_id
            sale_line.delivered_qty += line.qty_delivered
            
            # Release reservations proportionally
            qty_to_release = min(sale_line.reserved_qty, line.qty_delivered)
            if qty_to_release > 0:
                sale_line.reserved_qty -= qty_to_release

        # Update Sales Order State
        all_delivered = True
        any_delivered = False
        for line in order.order_line_ids:
            if line.delivered_qty < line.quantity:
                all_delivered = False
            if line.delivered_qty > 0:
                any_delivered = True
                
        if all_delivered:
            order.state = 'fully_delivered'
        elif any_delivered:
            order.state = 'partially_delivered'
            
        return {'type': 'ir.actions.act_window_close'}


class SaleOrderDeliverLine(models.TransientModel):
    _name = 'sale.order.deliver.line'
    _description = 'Deliver Sales Order Line'

    wizard_id = fields.Many2one('sale.order.deliver', string='Wizard Reference', required=True, ondelete='cascade')
    sale_line_id = fields.Many2one('sale.order.line', string='Sales Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty_ordered = fields.Float(string='Ordered Qty', readonly=True)
    qty_delivered = fields.Float(string='Qty to Deliver', required=True, default=0.0)
