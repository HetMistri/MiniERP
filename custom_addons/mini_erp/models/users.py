from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    position = fields.Char(string='Position')
