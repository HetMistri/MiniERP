from odoo import models, api, fields
from odoo.exceptions import UserError
from faker import Faker
import random
import logging

_logger = logging.getLogger(__name__)
fake = Faker()
Faker.seed(42)
random.seed(42)


class DemoDataGenerator(models.AbstractModel):
    _name = 'demo.data.generator'
    _description = 'Demo Data Generator'

    # ── Product Catalogs ──────────────────────────────────────────────
    RAW_MATERIALS = [
        "Wood Board", "Plywood Sheet", "MDF Board", "Foam Sheet",
        "Fabric Roll", "Leather Sheet", "Steel Rod", "Aluminium Pipe",
        "Copper Wire", "PVC Sheet", "Glass Panel", "Marble Slab",
        "Veneer Sheet", "Rubber Padding", "Spring Coil",
    ]
    COMPONENTS = [
        "Chair Base", "Chair Cushion", "Arm Rest", "Table Top",
        "Drawer", "Drawer Handle", "Hinge", "Leg Set",
        "Shelf Bracket", "Wheel Castor", "Gas Lift", "Seat Plate",
        "Backrest Frame", "Keyboard Tray", "Cable Management Tray",
        "Desk Leg", "Foot Ring", "Arm Pad", "Tilt Mechanism",
        "Screw Pack (100ct)", "Bolt Pack (50ct)", "Corner Bracket",
        "Wood Dowel", "Cam Lock", "Drawer Slide Rail",
        "Magnetic Catch", "Shelf Pin Set", "Frame Connector",
        "Panel Bracket", "Edge Banding Roll",
    ]
    FINISHED_GOODS = [
        ("Executive Chair", 15000, 8500),
        ("Office Chair", 10000, 5500),
        ("Dining Chair", 6000, 3200),
        ("Wooden Table", 25000, 14000),
        ("Dining Table 6-Seater", 35000, 20000),
        ("Study Desk", 12000, 6500),
        ("Bookshelf 3-Tier", 8000, 4200),
        ("Wardrobe 2-Door", 40000, 22000),
        ("Nightstand", 7000, 3800),
        ("Sofa 3-Seater", 55000, 30000),
        ("Coffee Table", 15000, 8000),
        ("TV Unit", 22000, 12000),
        ("Shoe Rack", 6000, 3200),
        ("Corner Shelf", 5000, 2600),
        ("Computer Desk", 14000, 7500),
        ("Conference Table", 45000, 28000),
        ("Bed Frame Queen", 30000, 16000),
        ("Wardrobe 3-Door", 55000, 30000),
        ("Dressing Table", 18000, 9500),
        ("Office Cabinet", 25000, 14000),
    ]

    PRODUCT_CATEGORIES = [
        "Raw Materials", "Components", "Finished Goods",
    ]

    @api.model
    def generate_all(self, vendor_count=25, customer_count=75,
                     raw_material_count=15, component_count=25,
                     finished_good_count=20, bom_count=20,
                     purchase_order_count=100, mo_count=80,
                     sales_order_count=150, confirm_ratio=0.6):
        """Main entry point — generates all demo data respecting dependencies."""
        step = 0
        total = 9

        step += 1
        _logger.info("[%d/%d] Generating categories...", step, total)
        uoms = self._ensure_uoms()
        categories = self._generate_categories()

        step += 1
        _logger.info("[%d/%d] Generating vendors (%d)...", step, total, vendor_count)
        vendors = self._generate_vendors(vendor_count)

        step += 1
        _logger.info("[%d/%d] Generating customers (%d)...", step, total, customer_count)
        customers = self._generate_customers(customer_count)

        step += 1
        _logger.info("[%d/%d] Generating products (%d raw + %d comp + %d finished)...",
                     step, total, raw_material_count, component_count, finished_good_count)
        raw_products, comp_products, finished_products = self._generate_products(
            categories, uoms, raw_material_count, component_count, finished_good_count
        )

        step += 1
        _logger.info("[%d/%d] Generating BoMs (%d)...", step, total, bom_count)
        boms = self._generate_boms(finished_products, comp_products, raw_products, bom_count)

        step += 1
        _logger.info("[%d/%d] Generating purchase orders (%d)...", step, total, purchase_order_count)
        purchase_orders = self._generate_purchase_orders(
            vendors, raw_products + comp_products, purchase_order_count
        )

        step += 1
        _logger.info("[%d/%d] Generating manufacturing orders (%d)...", step, total, mo_count)
        mos = self._generate_manufacturing_orders(finished_products, boms, mo_count)

        step += 1
        _logger.info("[%d/%d] Generating sales orders (%d)...", step, total, sales_order_count)
        sales_orders = self._generate_sales_orders(
            customers, finished_products, sales_order_count
        )

        step += 1
        _logger.info("[%d/%d] Running workflows (confirm %.0f%% of orders)...",
                     step, total, confirm_ratio * 100)
        self._run_workflows(sales_orders, purchase_orders, mos, confirm_ratio)

        _logger.info("Demo data generation complete!")
        return {
            'vendors': len(vendors),
            'customers': len(customers),
            'raw_materials': len(raw_products),
            'components': len(comp_products),
            'finished_goods': len(finished_products),
            'boms': len(boms),
            'purchase_orders': len(purchase_orders),
            'manufacturing_orders': len(mos),
            'sales_orders': len(sales_orders),
        }

    # ── UoMs ─────────────────────────────────────────────────────────
    def _ensure_uoms(self):
        existing = self.env['product.uom'].search([])
        if len(existing) >= 3:
            return existing
        uom_data = [
            ('Units', 'unit'),
            ('Pieces', 'pc'),
            ('Kilograms', 'kg'),
            ('Meters', 'm'),
            ('Sets', 'set'),
            ('Pairs', 'pr'),
        ]
        for name, code in uom_data:
            if not self.env['product.uom'].search([('code', '=', code)]):
                self.env['product.uom'].create({'name': name, 'code': code})
        return self.env['product.uom'].search([])

    # ── Categories ────────────────────────────────────────────────────
    def _generate_categories(self):
        existing = self.env['product.category'].search([])
        existing_names = {c.name for c in existing}
        created = []
        for name in self.PRODUCT_CATEGORIES:
            if name not in existing_names:
                cat = self.env['product.category'].create({'name': name})
                created.append(cat)
        return existing + self.env['product.category'].browse([c.id for c in created])

    # ── Partners ──────────────────────────────────────────────────────
    def _generate_vendors(self, count):
        created = []
        for _ in range(count):
            created.append(self.env['res.partner'].create({
                'name': fake.company(),
                'partner_type': 'company',
                'is_vendor': True,
                'street': fake.street_address(),
                'city': fake.city(),
                'phone': fake.phone_number(),
                'email': fake.email(),
            }))
        return created

    def _generate_customers(self, count):
        created = []
        for _ in range(count):
            created.append(self.env['res.partner'].create({
                'name': fake.company(),
                'partner_type': 'company',
                'is_customer': True,
                'street': fake.street_address(),
                'city': fake.city(),
                'phone': fake.phone_number(),
                'email': fake.email(),
            }))
        return created

    # ── Products ──────────────────────────────────────────────────────
    def _generate_products(self, categories, uoms, raw_count, comp_count, finished_count):
        uom_unit = uoms[0]
        raw_cat = categories.filtered(lambda c: c.name == 'Raw Materials')[:1]
        comp_cat = categories.filtered(lambda c: c.name == 'Components')[:1]
        finished_cat = categories.filtered(lambda c: c.name == 'Finished Goods')[:1]

        raw_products = []
        for name in self.RAW_MATERIALS[:raw_count]:
            raw_products.append(self.env['product.product'].create({
                'name': name,
                'product_type': 'stockable',
                'uom_id': uom_unit.id,
                'category_id': raw_cat.id,
                'sale_price': round(random.uniform(50, 500), 2),
                'cost_price': round(random.uniform(20, 300), 2),
            }))

        comp_products = []
        for name in self.COMPONENTS[:comp_count]:
            comp_products.append(self.env['product.product'].create({
                'name': name,
                'product_type': 'stockable',
                'uom_id': uom_unit.id,
                'category_id': comp_cat.id,
                'sale_price': round(random.uniform(100, 2000), 2),
                'cost_price': round(random.uniform(50, 1200), 2),
            }))

        finished_products = []
        for name, sale_price, cost_price in self.FINISHED_GOODS[:finished_count]:
            finished_products.append(self.env['product.product'].create({
                'name': name,
                'product_type': 'stockable',
                'uom_id': uom_unit.id,
                'category_id': finished_cat.id,
                'sale_price': sale_price,
                'cost_price': cost_price,
            }))

        return raw_products, comp_products, finished_products

    # ── BoMs ──────────────────────────────────────────────────────────
    def _generate_boms(self, finished_products, comp_products, raw_products, count):
        created = []
        all_components = comp_products + raw_products
        for product in finished_products[:count]:
            bom = self.env['mrp.bom'].create({
                'product_id': product.id,
                'product_qty': 1.0,
            })
            # Pick 3-6 random components
            components = random.sample(all_components, min(random.randint(3, 6), len(all_components)))
            for comp in components:
                self.env['mrp.bom.component'].create({
                    'bom_id': bom.id,
                    'product_id': comp.id,
                    'quantity': round(random.uniform(0.5, 4.0), 2),
                })
            created.append(bom)
        return created

    # ── Purchase Orders ───────────────────────────────────────────────
    def _generate_purchase_orders(self, vendors, products, count):
        created = []
        for _ in range(count):
            vendor = random.choice(vendors)
            po = self.env['purchase.order'].create({
                'partner_id': vendor.id,
                'date_order': fake.date_time_between(start_date='-3M', end_date='now'),
            })
            # Add 1-5 lines
            line_products = random.sample(products, min(random.randint(1, 5), len(products)))
            for prod in line_products:
                self.env['purchase.order.line'].create({
                    'order_id': po.id,
                    'product_id': prod.id,
                    'quantity': round(random.uniform(10, 200), 0),
                    'price_unit': prod.cost_price,
                    'description': prod.name,
                })
            created.append(po)
        return created

    # ── Manufacturing Orders ──────────────────────────────────────────
    def _generate_manufacturing_orders(self, finished_products, boms, count):
        created = []
        for _ in range(count):
            bom = random.choice(boms)
            mo = self.env['mrp.production'].create({
                'product_id': bom.product_id.id,
                'product_qty': round(random.uniform(1, 20), 0),
                'bom_id': bom.id,
                'date_planned_start': fake.date_time_between(start_date='-2M', end_date='+1M'),
            })
            created.append(mo)
        return created

    # ── Sales Orders ──────────────────────────────────────────────────
    def _generate_sales_orders(self, customers, finished_products, count):
        created = []
        for _ in range(count):
            customer = random.choice(customers)
            so = self.env['sale.order'].create({
                'partner_id': customer.id,
                'date_order': fake.date_time_between(start_date='-3M', end_date='now'),
            })
            # Add 1-4 lines
            line_products = random.sample(finished_products, min(random.randint(1, 4), len(finished_products)))
            for prod in line_products:
                self.env['sale.order.line'].create({
                    'order_id': so.id,
                    'product_id': prod.id,
                    'quantity': round(random.uniform(1, 15), 0),
                    'price_unit': prod.sale_price,
                    'description': prod.name,
                })
            created.append(so)
        return created

    # ── Workflows ─────────────────────────────────────────────────────
    def _run_workflows(self, sales_orders, purchase_orders, mos, confirm_ratio):
        # Confirm some POs + receive them (gives stock)
        for po in purchase_orders:
            if random.random() < confirm_ratio:
                try:
                    po.action_confirm()
                    po.action_receive()
                    # Auto-receive via the receive wizard
                    receive_wizard = self.env['purchase.order.receive'].create({
                        'order_id': po.id,
                    })
                    receive_wizard.default_get(['order_id', 'line_ids'])
                    receive_wizard.action_validate()
                except Exception as e:
                    _logger.warning("Could not process PO %s: %s", po.name, str(e))

        # Complete some MOs (consumes components, produces finished goods)
        for mo in mos:
            if random.random() < confirm_ratio:
                try:
                    mo.action_confirm()
                    mo.action_produce()
                except Exception as e:
                    _logger.warning("Could not process MO %s: %s", mo.name, str(e))

        # Confirm and deliver some SOs
        for so in sales_orders:
            if random.random() < confirm_ratio:
                try:
                    so.action_confirm()
                    so.action_deliver()
                    deliver_wizard = self.env['sale.order.deliver'].create({
                        'order_id': so.id,
                    })
                    deliver_wizard.default_get(['order_id', 'line_ids'])
                    deliver_wizard.action_validate()
                except Exception as e:
                    _logger.warning("Could not process SO %s: %s", so.name, str(e))
