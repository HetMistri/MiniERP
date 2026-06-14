from odoo import models, fields, api
from odoo.exceptions import UserError


class DemoDataWizard(models.TransientModel):
    _name = 'demo.data.wizard'
    _description = 'Generate Demo Data'

    vendor_count = fields.Integer(string='Vendors', default=25)
    customer_count = fields.Integer(string='Customers', default=75)
    raw_material_count = fields.Integer(string='Raw Materials', default=15)
    component_count = fields.Integer(string='Components', default=25)
    finished_good_count = fields.Integer(string='Finished Goods', default=20)
    bom_count = fields.Integer(string='Bills of Materials', default=20)
    purchase_order_count = fields.Integer(string='Purchase Orders', default=100)
    mo_count = fields.Integer(string='Manufacturing Orders', default=80)
    sales_order_count = fields.Integer(string='Sales Orders', default=150)

    confirm_ratio = fields.Float(
        string='Confirm Ratio (%)',
        default=60.0,
        help='Percentage of orders to confirm/deliver/receive through workflows',
    )

    state = fields.Selection([
        ('form', 'Form'),
        ('result', 'Result'),
    ], default='form')

    result = fields.Text(string='Generation Result', readonly=True)

    def action_generate(self):
        if self.sales_order_count <= 0:
            raise UserError("At least 1 Sales Order is required.")

        generator = self.env['demo.data.generator']
        try:
            stats = generator.generate_all(
                vendor_count=self.vendor_count,
                customer_count=self.customer_count,
                raw_material_count=self.raw_material_count,
                component_count=self.component_count,
                finished_good_count=self.finished_good_count,
                bom_count=self.bom_count,
                purchase_order_count=self.purchase_order_count,
                mo_count=self.mo_count,
                sales_order_count=self.sales_order_count,
                confirm_ratio=self.confirm_ratio / 100.0,
            )
        except Exception as e:
            raise UserError(f"Demo data generation failed:\n{str(e)}") from e

        lines = [
            "=== Demo Data Generated ===",
            "",
            f"  Vendors:             {stats['vendors']}",
            f"  Customers:           {stats['customers']}",
            f"  Raw Materials:       {stats['raw_materials']}",
            f"  Components:          {stats['components']}",
            f"  Finished Goods:      {stats['finished_goods']}",
            f"  Bills of Materials:  {stats['boms']}",
            f"  Purchase Orders:     {stats['purchase_orders']}",
            f"  Manufacturing Orders: {stats['manufacturing_orders']}",
            f"  Sales Orders:        {stats['sales_orders']}",
            "",
            f"  Total records: ~{sum(stats.values())}",
        ]
        self.write({'state': 'result', 'result': '\n'.join(lines)})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'demo.data.wizard',
            'view_mode': 'form',
            'res_id': self.id,
            'target': 'new',
        }
