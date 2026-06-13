# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import models, fields, api


class MrpWorkCenter(models.Model):
    _name = 'mrp.work.center'
    _description = 'Work Center'
    _order = 'name'

    name = fields.Char(required=True)
    code = fields.Char(required=True)
    responsible_id = fields.Many2one('res.users', default=lambda self: self.env.user, required=True)
    working_hours = fields.Float(default=8.0)
    cost_per_hour = fields.Float(default=0.0)
    description = fields.Text()
    active = fields.Boolean(default=True)


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _inherit = ['audit.mixin']
    _order = 'name desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: '/'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        ondelete='restrict'
    )
    product_qty = fields.Float(
        string='Quantity',
        required=True,
        default=1.0
    )
    bom_id = fields.Many2one(
        'mrp.bom',
        string='Bill of Materials',
        ondelete='restrict'
    )
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('in_progress', 'In Progress'),
        ('done', 'Done'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', required=True)
    date_planned_start = fields.Datetime(string='Planned Start')
    date_planned_finish = fields.Datetime(string='Planned Finish')
    date_start = fields.Datetime(string='Start Date', readonly=True)
    date_finished = fields.Datetime(string='Finished Date', readonly=True)
    assignee_id = fields.Many2one(
        'res.users',
        string='Assignee',
        required=True,
        default=lambda self: self.env.user
    )
    origin = fields.Char(string='Source Document')
    notes = fields.Text(string='Notes')
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        required=True,
        default=lambda self: self.env.company
    )
    component_ids = fields.One2many(
        'mrp.production.component',
        'production_id',
        string='Components'
    )

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'The Manufacturing Order reference must be unique!'),
    ]

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.production') or '/'
        return super().create(vals_list)


class MrpProductionComponent(models.Model):
    _name = 'mrp.production.component'
    _description = 'Manufacturing Order Component'
    _inherit = ['audit.mixin']
    _order = 'id'

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        required=True,
        ondelete='cascade'
    )
    product_id = fields.Many2one(
        'product.product',
        string='Component Product',
        required=True,
        ondelete='restrict'
    )
    quantity_needed = fields.Float(
        string='Quantity Needed',
        required=True
    )
    quantity_consumed = fields.Float(
        string='Quantity Consumed',
        default=0.0,
        required=True
    )
    quantity_reserved = fields.Float(
        string='Quantity Reserved',
        default=0.0,
        required=True
    )
    uom_id = fields.Many2one(
        'product.uom',
        string='Unit of Measure',
        required=True,
        ondelete='restrict'
    )


class MrpWorkOrder(models.Model):
    _name = 'mrp.work.order'
    _description = 'Work Order'
    _order = 'sequence, id'

    production_id = fields.Many2one(
        'mrp.production',
        string='Manufacturing Order',
        required=True,
        ondelete='cascade'
    )
    work_center_id = fields.Many2one(
        'mrp.work.center',
        string='Work Center',
        required=True,
        ondelete='restrict'
    )
    sequence = fields.Integer(default=10)
    name = fields.Char(required=True)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('in_progress', 'In Progress'),
        ('done', 'Done')
    ], default='pending', required=True)
    duration_minutes = fields.Float(string='Duration (Minutes)', default=0.0)
    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')
    assignee_id = fields.Many2one(
        'res.users',
        string='Assignee',
        required=True,
        default=lambda self: self.env.user
    )
