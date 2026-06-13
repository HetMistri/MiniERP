from odoo import models, fields, api


class PurchaseOrderReceive(models.TransientModel):
    _name = 'purchase.order.receive'
    _description = 'Receive Purchase Order'

    order_id = fields.Many2one('purchase.order', string='Purchase Order', required=True)
    line_ids = fields.One2many('purchase.order.receive.line', 'wizard_id', string='Lines')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id:
            order = self.env['purchase.order'].browse(active_id)
            res['order_id'] = order.id
            lines = []
            for line in order.order_line_ids:
                qty_to_receive = line.quantity - line.received_qty
                if qty_to_receive > 0:
                    lines.append((0, 0, {
                        'purchase_line_id': line.id,
                        'product_id': line.product_id.id,
                        'qty_ordered': line.quantity,
                        'qty_received': qty_to_receive,
                    }))
            res['line_ids'] = lines
        return res

    def action_validate(self):
        self.ensure_one()
        order = self.order_id
        
        for line in self.line_ids:
            if line.qty_received <= 0:
                continue
            
            product = line.product_id
            
            # Create Stock Ledger Entry (positive quantity for inbound)
            self.env['stock.ledger']._update_stock(
                product.id,
                line.qty_received,
                order.name,
                'purchase_receipt',
                notes=f"Receipt for Purchase Order {order.name}"
            )
            
            # Update Purchase Order Line
            line.purchase_line_id.received_qty += line.qty_received

        # Update Purchase Order State
        all_received = True
        any_received = False
        for line in order.order_line_ids:
            if line.received_qty < line.quantity:
                all_received = False
            if line.received_qty > 0:
                any_received = True
                
        if all_received:
            order.state = 'fully_received'
        elif any_received:
            order.state = 'partially_received'
            
        return {'type': 'ir.actions.act_window_close'}


class PurchaseOrderReceiveLine(models.TransientModel):
    _name = 'purchase.order.receive.line'
    _description = 'Receive Purchase Order Line'

    wizard_id = fields.Many2one('purchase.order.receive', string='Wizard Reference', required=True, ondelete='cascade')
    purchase_line_id = fields.Many2one('purchase.order.line', string='Purchase Line', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True)
    qty_ordered = fields.Float(string='Ordered Qty', readonly=True)
    qty_received = fields.Float(string='Qty to Receive', required=True, default=0.0)
