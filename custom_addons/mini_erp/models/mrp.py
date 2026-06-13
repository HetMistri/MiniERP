# -*- coding: utf-8 -*-
# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from odoo import models, fields, api, _
# pyrefly: ignore [missing-import]
from odoo.exceptions import ValidationError

class MrpWorkCenter(models.Model):
    _name = 'mrp.work.center'
    _description = 'Work Center'
    _inherit = ['audit.mixin']
    _order = 'name'

    name = fields.Char(required=True, string='Name')
    code = fields.Char(required=True, string='Code')
    responsible_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user)
    working_hours = fields.Float(string='Working Hours per Day', default=8.0)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', related='company_id.currency_id', readonly=True)
    cost_per_hour = fields.Monetary(string='Cost per Hour', currency_field='currency_id')
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('code_uniq', 'unique(code)', 'Work Center code must be unique!'),
    ]

    @api.constrains('working_hours', 'cost_per_hour')
    def _check_workcenter_values(self):
        for wc in self:
            if wc.working_hours < 0 or wc.working_hours > 24:
                raise ValidationError(_("Working hours must be between 0 and 24 hours per day."))
            if wc.cost_per_hour < 0:
                raise ValidationError(_("Cost per hour cannot be negative."))

    def unlink(self):
        for wc in self:
            operations = self.env['mrp.bom.operation'].search([('work_center_id', '=', wc.id)])
            if operations:
                raise ValidationError(_("You cannot delete a Work Center that is referenced in Bill of Materials operations."))
        return super().unlink()


class MrpBom(models.Model):
    _name = 'mrp.bom'
    _description = 'Bill of Materials'
    _inherit = ['audit.mixin']
    _order = 'name'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: '/')
    product_id = fields.Many2one('product.product', string='Finished Product', required=True, ondelete='restrict', index=True)
    product_qty = fields.Float(string='Quantity', default=1.0, required=True)
    component_ids = fields.One2many('mrp.bom.component', 'bom_id', string='Components')
    operation_ids = fields.One2many('mrp.bom.operation', 'bom_id', string='Operations')
    active = fields.Boolean(default=True)
    notes = fields.Text(string='Notes')

    @api.constrains('product_qty')
    def _check_product_qty(self):
        for bom in self:
            if bom.product_qty <= 0:
                raise ValidationError(_("The product quantity on the Bill of Materials must be greater than zero."))

    def unlink(self):
        for bom in self:
            productions = self.env['mrp.production'].search([('bom_id', '=', bom.id)])
            if productions:
                raise ValidationError(_("You cannot delete a Bill of Materials that is used in Manufacturing Orders."))
        return super().unlink()

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.bom') or '/'
        return super().create(vals_list)

    def name_get(self):
        result = []
        for bom in self:
            result.append((bom.id, f"{bom.name} ({bom.product_id.name})"))
        return result

    def action_save(self):
        return True


class MrpBomComponent(models.Model):
    _name = 'mrp.bom.component'
    _description = 'BoM Component'
    _order = 'id'

    bom_id = fields.Many2one('mrp.bom', string='Parent BoM', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Component Product', required=True, ondelete='restrict')
    quantity = fields.Float(string='Quantity Needed', default=1.0, required=True)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)

    @api.constrains('quantity')
    def _check_quantity(self):
        for comp in self:
            if comp.quantity <= 0:
                raise ValidationError(_("The quantity of component %s must be greater than zero.") % comp.product_id.name)


class MrpBomOperation(models.Model):
    _name = 'mrp.bom.operation'
    _description = 'BoM Operation'
    _order = 'sequence, id'

    bom_id = fields.Many2one('mrp.bom', string='Parent BoM', ondelete='cascade', required=True)
    work_center_id = fields.Many2one('mrp.work.center', string='Work Center', required=True, ondelete='restrict')
    name = fields.Char(string='Operation Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    duration_minutes = fields.Float(string='Duration (Minutes)', default=60.0)
    description = fields.Text(string='Description')


class MrpProduction(models.Model):
    _name = 'mrp.production'
    _description = 'Manufacturing Order'
    _inherit = ['audit.mixin']
    _order = 'date_planned_start desc, id desc'

    name = fields.Char(string='Reference', required=True, copy=False, readonly=True, index=True, default=lambda self: '/')
    product_id = fields.Many2one('product.product', string='Finished Product', required=True, ondelete='restrict', index=True)
    product_qty = fields.Float(string='Quantity to Produce', default=1.0, required=True)
    bom_id = fields.Many2one('mrp.bom', string='Bill of Materials', ondelete='restrict')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
        ('cancel', 'Cancelled'),
    ], string='Status', default='draft', required=True, index=True, copy=False)
    component_ids = fields.One2many('mrp.production.component', 'production_id', string='Components', copy=True)
    work_order_ids = fields.One2many('mrp.work.order', 'production_id', string='Work Orders', copy=True)
    date_planned_start = fields.Datetime(string='Planned Start Date', default=fields.Datetime.now, required=True)
    date_planned_finish = fields.Datetime(string='Planned Finish Date')
    date_start = fields.Datetime(string='Start Date', readonly=True)
    date_finished = fields.Datetime(string='Finished Date', readonly=True)
    assignee_id = fields.Many2one('res.users', string='Assignee', default=lambda self: self.env.user)
    origin = fields.Char(string='Source Document')
    notes = fields.Text(string='Notes')
    component_status = fields.Selection([
        ('available', 'Available'),
        ('not_available', 'Not Available'),
    ], string='Component Status', compute='_compute_component_status', store=False)

    @api.depends('component_ids', 'component_ids.product_id.free_to_use_qty', 'component_ids.quantity_needed', 'component_ids.quantity_reserved')
    def _compute_component_status(self):
        for order in self:
            status = 'available'
            for comp in order.component_ids:
                needed = comp.quantity_needed
                available = comp.quantity_reserved + comp.product_id.free_to_use_qty
                if needed > available:
                    status = 'not_available'
                    break
            order.component_status = status

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            bom = self.env['mrp.bom'].search([('product_id', '=', self.product_id.id), ('active', '=', True)], limit=1)
            if bom:
                self.bom_id = bom
            else:
                self.bom_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('name') or vals.get('name') == '/':
                vals['name'] = self.env['ir.sequence'].next_by_code('mrp.production') or '/'
        return super().create(vals_list)

    def action_confirm(self):
        for order in self:
            if order.state != 'draft':
                continue
            if not order.product_id:
                raise ValidationError(_("Please select a product to manufacture."))
            if not order.bom_id or not order.bom_id.active:
                raise ValidationError(_("Please select an active Bill of Materials (BoM) for product %s.") % order.product_id.name)
            if order.product_qty <= 0:
                raise ValidationError(_("Quantity to produce must be greater than zero."))

            # 1. Explode BoM components
            component_vals = []
            ratio = order.product_qty / order.bom_id.product_qty
            for bom_comp in order.bom_id.component_ids:
                needed = bom_comp.quantity * ratio
                component_vals.append((0, 0, {
                    'product_id': bom_comp.product_id.id,
                    'quantity_needed': needed,
                    'quantity_consumed': 0.0,
                    'quantity_reserved': 0.0,
                }))
            order.write({'component_ids': component_vals})

            # 2. Explode BoM operations to Work Orders
            wo_vals = []
            for op in order.bom_id.operation_ids:
                wo_vals.append((0, 0, {
                    'work_center_id': op.work_center_id.id,
                    'name': op.name,
                    'sequence': op.sequence,
                    'duration_minutes': op.duration_minutes,
                    'state': 'pending',
                }))
            order.write({'work_order_ids': wo_vals})

            # 3. Reserve components
            order._reserve_components()

            order.write({'state': 'confirmed'})
        return True

    def _reserve_components(self):
        for order in self:
            for comp in order.component_ids:
                free_qty = comp.product_id.free_to_use_qty
                needed = comp.quantity_needed
                reserved = min(needed, max(0.0, free_qty))
                comp.write({'quantity_reserved': reserved})
                self.env['product.product']._update_reserved_qty(comp.product_id.id, reserved)

    def action_start(self):
        for order in self:
            if order.state != 'confirmed':
                continue
            order.write({
                'state': 'progress',
                'date_start': fields.Datetime.now(),
            })
            for wo in order.work_order_ids:
                if wo.state == 'pending':
                    wo.write({'state': 'ready'})
        return True

    def action_finish(self):
        for order in self:
            if order.state != 'progress':
                continue
            if any(wo.state != 'done' for wo in order.work_order_ids):
                raise ValidationError(_("All work orders must be completed ('Done') before finishing the production order."))

            for comp in order.component_ids:
                if comp.quantity_consumed <= 0:
                    comp.write({'quantity_consumed': comp.quantity_needed})

            # Validate component stock availability if negative stock is not allowed
            if not self.env.company.allow_negative_stock:
                for comp in order.component_ids:
                    if comp.product_id.product_type == 'stockable':
                        if comp.product_id.on_hand_qty < comp.quantity_consumed:
                            raise ValidationError(_(
                                "Insufficient stock for component '%s'. "
                                "On Hand: %s, Consumed: %s"
                            ) % (comp.product_id.name, comp.product_id.on_hand_qty, comp.quantity_consumed))

            for comp in order.component_ids:
                self.env['stock.ledger']._update_stock(
                    comp.product_id.id,
                    -comp.quantity_consumed,
                    order.name,
                    'manufacture_out'
                )

            self.env['stock.ledger']._update_stock(
                order.product_id.id,
                order.product_qty,
                order.name,
                'manufacture_in'
            )

            for comp in order.component_ids:
                if comp.quantity_reserved > 0:
                    self.env['product.product']._update_reserved_qty(comp.product_id.id, -comp.quantity_reserved)
                comp.write({'quantity_reserved': 0.0})

            order.write({
                'state': 'done',
                'date_finished': fields.Datetime.now(),
            })
        return True

    def action_cancel(self):
        for order in self:
            if order.state not in ('draft', 'confirmed', 'progress', 'done'):
                raise ValidationError(_("You cannot cancel this manufacturing order in its current state."))
            
            # If MO is Done, reverse stock movements
            if order.state == 'done':
                ledger_entries = self.env['stock.ledger'].search([('reference', '=', order.name)])
                for entry in ledger_entries:
                    self.env['stock.ledger']._update_stock(
                        entry.product_id.id,
                        -entry.quantity,
                        order.name,
                        'adjustment',
                        notes=f"Reversal of {entry.transaction_type} due to MO cancellation"
                    )
            
            for comp in order.component_ids:
                if comp.quantity_reserved > 0:
                    self.env['product.product']._update_reserved_qty(comp.product_id.id, -comp.quantity_reserved)
                comp.write({'quantity_reserved': 0.0})
            order.write({'state': 'cancel'})
        return True

    def unlink(self):
        for order in self:
            if order.state not in ('draft', 'cancel'):
                raise ValidationError(_("You can only delete manufacturing orders in 'Draft' or 'Cancelled' status."))
        return super().unlink()

    def action_produce(self):
        for order in self:
            if order.state not in ('confirmed', 'progress'):
                continue
            # Auto-complete any work orders that aren't done yet
            for wo in order.work_order_ids:
                if wo.state != 'done':
                    if wo.state in ('pending', 'ready'):
                        wo.action_start()
                    wo.action_done()
            # If the state is confirmed, transition to progress first
            if order.state == 'confirmed':
                order.write({
                    'state': 'progress',
                    'date_start': fields.Datetime.now(),
                })
            # Finish the manufacturing order (this backflushes, logs stock ledger, and marks it Done)
            order.action_finish()
        return True


class MrpProductionComponent(models.Model):
    _name = 'mrp.production.component'
    _description = 'Manufacturing Order Component'
    _order = 'id'

    production_id = fields.Many2one('mrp.production', string='Parent MO', ondelete='cascade', required=True)
    product_id = fields.Many2one('product.product', string='Product', required=True, ondelete='restrict')
    quantity_needed = fields.Float(string='Quantity Needed', default=1.0, required=True)
    quantity_consumed = fields.Float(string='Quantity Consumed', default=0.0)
    quantity_reserved = fields.Float(string='Quantity Reserved', default=0.0)
    uom_id = fields.Many2one('product.uom', string='Unit of Measure', related='product_id.uom_id', readonly=True, store=True)


class MrpWorkOrder(models.Model):
    _name = 'mrp.work.order'
    _description = 'Work Order'
    _inherit = ['audit.mixin']
    _order = 'sequence, id'

    production_id = fields.Many2one('mrp.production', string='Parent MO', ondelete='cascade', required=True)
    work_center_id = fields.Many2one('mrp.work.center', string='Work Center', required=True, ondelete='restrict')
    name = fields.Char(string='Work Order Name', required=True)
    sequence = fields.Integer(string='Sequence', default=10)
    state = fields.Selection([
        ('pending', 'Pending'),
        ('ready', 'Ready'),
        ('progress', 'In Progress'),
        ('done', 'Done'),
    ], string='Status', default='pending', required=True, copy=False)
    duration_minutes = fields.Float(string='Duration (Minutes)', default=60.0)
    real_duration = fields.Float(string='Real Duration (Minutes)', compute='_compute_real_duration', store=True)
    date_start = fields.Datetime(string='Start Date')
    date_end = fields.Datetime(string='End Date')
    assignee_id = fields.Many2one('res.users', string='Assignee')

    @api.depends('date_start', 'date_end')
    def _compute_real_duration(self):
        for wo in self:
            if wo.date_start and wo.date_end:
                diff = wo.date_end - wo.date_start
                wo.real_duration = diff.total_seconds() / 60.0
            else:
                wo.real_duration = 0.0

    def action_start(self):
        for wo in self:
            if wo.state not in ('ready', 'pending'):
                continue
            wo.write({
                'state': 'progress',
                'date_start': fields.Datetime.now(),
            })
        return True

    def action_done(self):
        for wo in self:
            if wo.state != 'progress':
                wo.write({'date_start': fields.Datetime.now()})
            wo.write({
                'state': 'done',
                'date_end': fields.Datetime.now(),
            })
        return True
