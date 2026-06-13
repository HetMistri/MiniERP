{
    'name': "Mini ERP",
    'summary': "From Demand to Delivery — Complete Manufacturing ERP",
    'description': """
Mini ERP System that digitally manages the complete business flow:
- Product Management
- Sales Management
- Purchase Management
- Manufacturing
- Bill of Materials (BoM)
- Inventory & Stock Tracking
- Procurement Automation
    """,
    'author': "Shiv Furniture Works",
    'website': "",
    'license': 'LGPL-3',
    'category': 'Manufacturing',
    'version': '1.0.0',
    'depends': ['base'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'data/ir_cron_data.xml',
        'views/audit_log_views.xml',
        'views/product_views.xml',
        'views/views.xml',
        'views/stock_views.xml',
        'views/mrp_views.xml',
        'wizard/sale_order_deliver_views.xml',
        'wizard/purchase_order_receive_views.xml',
        'wizard/product_replenish_views.xml',
        'views/partner_views.xml',
        'views/sale_order_views.xml',
        'views/purchase_order_views.xml',
        'views/user_views.xml',
        'views/dashboard_views.xml',
        'views/reports.xml',
        'views/templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'mini_erp/static/src/css/dashboard.css',
        ],
    },
    'demo': [
        'demo/demo.xml',
        'demo/mrp_demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
