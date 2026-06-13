# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    position = fields.Char(string='Position')
