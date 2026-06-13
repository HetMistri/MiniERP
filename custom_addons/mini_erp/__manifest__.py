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
        'views/views.xml',
        'views/product_views.xml',
        'views/audit_log_views.xml',
        'views/templates.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
