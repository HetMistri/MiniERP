# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    allow_negative_stock = fields.Boolean(
        string='Allow Negative Stock',
        default=False,
        help='If checked, stockable products can be delivered or consumed beyond their on-hand quantity without blocking validation.'
    )
