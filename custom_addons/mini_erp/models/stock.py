from odoo import models, fields, api


class StockLedger(models.Model):
    _name = 'stock.ledger'
    _description = 'Stock Ledger'
    _order = 'date desc, id desc'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', index=True)
    reference = fields.Char(string='Reference', index=True)
    transaction_type = fields.Selection([
        ('sale_delivery', 'Sale Delivery'),
        ('purchase_receipt', 'Purchase Receipt'),
        ('manufacture_in', 'Manufacture In'),
        ('manufacture_out', 'Manufacture Out'),
        ('initial', 'Initial Stock'),
        ('adjustment', 'Adjustment'),
    ], string='Transaction Type', required=True)
    quantity = fields.Float(string='Quantity', required=True, help='Signed quantity: + for inbound, - for outbound')
    balance_after = fields.Float(string='Balance After', help='On-hand quantity after this transaction')
    date = fields.Datetime(string='Date', default=fields.Datetime.now, required=True, index=True)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user, required=True)

    @api.model
    def _update_stock(self, product_id, qty, reference, transaction_type):
        """Helper method to write a ledger entry and calculate balance_after"""
        product = self.env['product.product'].browse(product_id)
        if not product.exists():
            return None
        
        # Calculate balance after this transaction.
        # Sum of previous quantities plus the new one.
        # Since on_hand_qty is computed from the ledger, we can calculate the current on-hand first:
        current_on_hand = sum(self.search([('product_id', '=', product_id)]).mapped('quantity'))
        balance_after = current_on_hand + qty
        
        ledger_entry = self.create({
            'product_id': product_id,
            'quantity': qty,
            'reference': reference,
            'transaction_type': transaction_type,
            'balance_after': balance_after,
            'date': fields.Datetime.now(),
            'user_id': self.env.user.id,
        })
        return ledger_entry
