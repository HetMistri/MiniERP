# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError, ValidationError


class TestMiniErpProcurement(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # UoM
        cls.uom = cls.env['product.uom'].create({
            'name': 'UnitsTest',
            'code': 'UT',
        })
        # Category
        cls.category = cls.env['product.category'].create({
            'name': 'TestCategory',
        })
        # Partners
        cls.customer = cls.env['res.partner'].create({
            'name': 'Test Customer',
            'is_customer': True,
        })
        cls.vendor = cls.env['res.partner'].create({
            'name': 'Test Vendor',
            'is_vendor': True,
        })

    def test_flow_1_mts_full_cycle(self):
        """Test Flow 1 - MTS Full Cycle"""
        product = self.env['product.product'].create({
            'name': 'MTS Product',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'sale_price': 100.0,
            'cost_price': 50.0,
        })

        # Add initial stock of 100
        self.env['stock.ledger']._update_stock(
            product.id, 100.0, 'Initial Stock', 'initial', 'Add initial stock'
        )

        product.invalidate_recordset()
        self.assertEqual(product.on_hand_qty, 100.0)
        self.assertEqual(product.free_to_use_qty, 100.0)

        # Create Sales Order
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 10.0,
                'price_unit': 100.0,
            })]
        })

        # Confirm SO
        so.action_confirm()
        product.invalidate_recordset()
        self.assertEqual(product.on_hand_qty, 100.0)
        self.assertEqual(product.reserved_qty, 10.0)
        self.assertEqual(product.free_to_use_qty, 90.0)

        # Deliver SO
        deliver_wizard = self.env['sale.order.deliver'].with_context(active_id=so.id).create({
            'order_id': so.id,
        })
        deliver_wizard.action_validate()

        product.invalidate_recordset()
        self.assertEqual(product.on_hand_qty, 90.0)
        self.assertEqual(product.reserved_qty, 0.0)
        self.assertEqual(product.free_to_use_qty, 90.0)
        self.assertEqual(so.state, 'fully_delivered')

    def test_flow_2_mto_purchase(self):
        """Test Flow 2 - MTO Purchase"""
        product = self.env['product.product'].create({
            'name': 'MTO Purchase Product',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'sale_price': 200.0,
            'cost_price': 120.0,
            'procure_on_demand': True,
            'procurement_type': 'purchase',
            'vendor_id': self.vendor.id,
        })

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 15.0,
                'price_unit': 200.0,
            })]
        })

        so.action_confirm()

        # Check PO creation
        po = self.env['purchase.order'].search([
            ('origin_sale_order_id', '=', so.id)
        ])
        self.assertTrue(po)
        self.assertEqual(po.state, 'draft')
        self.assertEqual(po.partner_id.id, self.vendor.id)
        self.assertEqual(len(po.order_line_ids), 1)
        self.assertEqual(po.order_line_ids.product_id.id, product.id)
        self.assertEqual(po.order_line_ids.quantity, 15.0)

    def test_flow_3_mto_manufacture(self):
        """Test Flow 3 - MTO Manufacture"""
        component = self.env['product.product'].create({
            'name': 'BOM Component',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'cost_price': 10.0,
        })
        self.env['stock.ledger']._update_stock(
            component.id, 100.0, 'Initial Stock', 'initial', 'Add components'
        )

        finished_product = self.env['product.product'].create({
            'name': 'Finished Product',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'sale_price': 150.0,
            'procure_on_demand': True,
            'procurement_type': 'manufacture',
        })

        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_qty': 1.0,
            'component_ids': [(0, 0, {
                'product_id': component.id,
                'quantity': 2.0,
            })]
        })
        finished_product.bom_id = bom.id

        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line_ids': [(0, 0, {
                'product_id': finished_product.id,
                'quantity': 10.0,
                'price_unit': 150.0,
            })]
        })

        so.action_confirm()

        # Check MO creation
        mo = self.env['mrp.production'].search([
            ('origin', '=', f"{so.name} — {finished_product.name}")
        ])
        self.assertTrue(mo)
        self.assertEqual(mo.state, 'draft')
        self.assertEqual(mo.product_id.id, finished_product.id)
        self.assertEqual(mo.product_qty, 10.0)

    def test_flow_4_manufacturing_completion(self):
        """Test Flow 4 - Manufacturing Completion"""
        component = self.env['product.product'].create({
            'name': 'BOM Component 2',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'cost_price': 20.0,
        })
        self.env['stock.ledger']._update_stock(
            component.id, 50.0, 'Initial Stock', 'initial', 'Add components'
        )

        finished_product = self.env['product.product'].create({
            'name': 'Finished Product 2',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'sale_price': 300.0,
            'procure_on_demand': True,
            'procurement_type': 'manufacture',
        })

        bom = self.env['mrp.bom'].create({
            'product_id': finished_product.id,
            'product_qty': 1.0,
            'component_ids': [(0, 0, {
                'product_id': component.id,
                'quantity': 3.0,
            })]
        })
        finished_product.bom_id = bom.id

        mo = self.env['mrp.production'].create({
            'product_id': finished_product.id,
            'product_qty': 5.0,
            'bom_id': bom.id,
        })

        mo.action_confirm()
        self.assertEqual(mo.state, 'confirmed')
        self.assertEqual(len(mo.component_ids), 1)
        self.assertEqual(mo.component_ids.quantity_reserved, 15.0)

        mo.action_start()
        self.assertEqual(mo.state, 'progress')

        # Since no work orders were exploded (no operations in BOM), we can finish directly
        mo.action_finish()
        self.assertEqual(mo.state, 'done')

        component.invalidate_recordset()
        finished_product.invalidate_recordset()
        self.assertEqual(component.on_hand_qty, 35.0)
        self.assertEqual(finished_product.on_hand_qty, 5.0)

    def test_flow_5_purchase_receipt(self):
        """Test Flow 5 - Purchase Receipt"""
        product = self.env['product.product'].create({
            'name': 'Product For Receipt',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'cost_price': 10.0,
        })

        po = self.env['purchase.order'].create({
            'partner_id': self.vendor.id,
            'order_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 25.0,
                'price_unit': 10.0,
            })]
        })

        po.action_confirm()
        self.assertEqual(po.state, 'confirmed')

        # Receive PO
        receive_wizard = self.env['purchase.order.receive'].with_context(active_id=po.id).create({
            'order_id': po.id,
        })
        receive_wizard.action_validate()

        product.invalidate_recordset()
        self.assertEqual(product.on_hand_qty, 25.0)
        self.assertEqual(po.state, 'fully_received')

    def test_flow_6_access_rights(self):
        """Test Flow 6 - Access Rights and Warnings/Blocks"""
        # Negative stock block verify
        self.env.company.allow_negative_stock = False

        product = self.env['product.product'].create({
            'name': 'Blocked Product',
            'product_type': 'stockable',
            'uom_id': self.uom.id,
            'category_id': self.category.id,
            'cost_price': 10.0,
        })

        # Try to deliver product with 0 stock
        so = self.env['sale.order'].create({
            'partner_id': self.customer.id,
            'order_line_ids': [(0, 0, {
                'product_id': product.id,
                'quantity': 5.0,
                'price_unit': 15.0,
            })]
        })

        # SO confirmation should block because no stock and no procurement
        with self.assertRaises(UserError):
            so.action_confirm()

        # Inactive BoM verify
        bom = self.env['mrp.bom'].create({
            'product_id': product.id,
            'product_qty': 1.0,
            'active': False,
        })
        
        mo = self.env['mrp.production'].create({
            'product_id': product.id,
            'product_qty': 5.0,
            'bom_id': bom.id,
        })
        # Try to confirm MO with inactive BoM
        with self.assertRaises(ValidationError):
            mo.action_confirm()
