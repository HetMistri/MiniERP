from odoo import models, fields, api


class ProductUom(models.Model):
    _name = 'product.uom'
    _description = 'Unit of Measure'
    _order = 'name'

    name = fields.Char(required=True, string='Unit Name')
    code = fields.Char(required=True, string='Code')
    active = fields.Boolean(default=True)


class ProductCategory(models.Model):
    _name = 'product.category'
    _description = 'Product Category'
    _rec_name = 'complete_name'
    _order = 'parent_path'

    name = fields.Char(required=True)
    parent_id = fields.Many2one('product.category', string='Parent Category', ondelete='restrict', index=True)
    child_ids = fields.One2many('product.category', 'parent_id', string='Subcategories')
    parent_path = fields.Char(index=True, recursive=True)
    description = fields.Text()
    active = fields.Boolean(default=True)
    complete_name = fields.Char(compute='_compute_complete_name', store=True, recursive=True)

    @api.depends('name', 'parent_id.complete_name')
    def _compute_complete_name(self):
        for record in self:
            if record.parent_id:
                record.complete_name = f'{record.parent_id.complete_name} / {record.name}'
            else:
                record.complete_name = record.name


class ProductProduct(models.Model):
    _name = 'product.product'
    _description = 'Product'
    _rec_name = 'name'
    _inherit = ['audit.mixin']
    _order = 'name'

    name = fields.Char(required=True)
    reference = fields.Char(string='Internal Reference', copy=False, readonly=True, index=True)
    category_id = fields.Many2one('product.category', string='Category', ondelete='restrict')
    sale_price = fields.Monetary(string='Sales Price', currency_field='currency_id')
    cost_price = fields.Monetary(string='Cost Price', currency_field='currency_id')
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', required=True)
    product_type = fields.Selection([
        ('stockable', 'Stockable'),
        ('service', 'Service'),
        ('consumable', 'Consumable'),
    ], string='Product Type', default='stockable', required=True)
    on_hand_qty = fields.Float(string='On Hand Quantity', compute='_compute_quantities', readonly=True)
    reserved_qty = fields.Float(string='Reserved Quantity', compute='_compute_quantities', readonly=True)
    free_to_use_qty = fields.Float(string='Free to Use Quantity', compute='_compute_quantities', readonly=True)
    active = fields.Boolean(default=True)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Procurement settings (Phase D)
    procure_on_demand = fields.Boolean(string='Procure on Demand', default=False)
    procurement_type = fields.Selection([
        ('manufacture', 'Manufacture'),
        ('purchase', 'Purchase'),
    ], string='Procurement Type')
    vendor_id = fields.Many2one('res.partner', string='Vendor', domain=[('is_vendor', '=', True)])
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials')
    min_stock_qty = fields.Float(string='Minimum Stock Quantity', default=0.0)
    lead_time_days = fields.Integer(string='Lead Time (Days)', default=1)

    @api.depends('on_hand_qty', 'reserved_qty')
    def _compute_quantities(self):
        # Safe checks to ensure database tables are created before running queries
        self.env.cr.execute("SELECT to_regclass('stock_ledger')")
        has_ledger = self.env.cr.fetchone()[0]
        
        self.env.cr.execute("SELECT to_regclass('mrp_production_component')")
        has_mrp = self.env.cr.fetchone()[0]

        on_hand_map = {}
        if has_ledger:
            ledger_data = self.env['stock.ledger'].sudo().read_group(
                [('product_id', 'in', self.ids)],
                ['product_id', 'quantity:sum'],
                ['product_id']
            )
            on_hand_map = {data['product_id'][0]: data['quantity'] for data in ledger_data if data['product_id']}

        reserved_mrp_map = {}
        if has_mrp:
            mrp_data = self.env['mrp.production.component'].sudo().read_group(
                [('product_id', 'in', self.ids), ('production_id.state', 'in', ('confirmed', 'progress'))],
                ['product_id', 'quantity_reserved:sum'],
                ['product_id']
            )
            reserved_mrp_map = {data['product_id'][0]: data['quantity_reserved'] for data in mrp_data if data['product_id']}

        reserved_so_map = {}
        if 'sale.order.line' in self.env:
            self.env.cr.execute("SELECT to_regclass('sale_order_line')")
            has_so = self.env.cr.fetchone()[0]
            if has_so:
                so_data = self.env['sale.order.line'].sudo().read_group(
                    [('product_id', 'in', self.ids), ('order_id.state', '=', 'confirmed')],
                    ['product_id', 'reserved_qty:sum'],
                    ['product_id']
                )
                reserved_so_map = {data['product_id'][0]: data['reserved_qty'] for data in so_data if data['product_id']}

        for record in self:
            record.on_hand_qty = on_hand_map.get(record.id, 0.0)
            record.reserved_qty = reserved_mrp_map.get(record.id, 0.0) + reserved_so_map.get(record.id, 0.0)
            record.free_to_use_qty = record.on_hand_qty - record.reserved_qty

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('reference'):
                vals['reference'] = self.env['ir.sequence'].next_by_code('product.product') or '/'
        return super().create(vals_list)


class ProductQuantityHistory(models.Model):
    _name = 'product.quantity.history'
    _description = 'Product Quantity History'
    _order = 'date desc'

    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='cascade', index=True)
    quantity = fields.Float(string='Quantity', required=True)
    date = fields.Datetime(default=fields.Datetime.now, required=True, index=True)
    reason = fields.Char(string='Reason')
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
