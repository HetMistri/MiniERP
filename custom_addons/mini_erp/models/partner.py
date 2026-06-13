# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    partner_type = fields.Selection([
        ('individual', 'Individual'),
        ('company', 'Company'),
    ], string='Partner Type', default='individual', required=True)
    is_customer = fields.Boolean(string='Is a Customer', default=False)
    is_vendor = fields.Boolean(string='Is a Vendor', default=False)
