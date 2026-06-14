from odoo import models, fields, api

# pyrefly: ignore [missing-import]
from odoo.http import request
# pyrefly: ignore [missing-import]
from odoo.exceptions import UserError

class AuditLog(models.Model):
    _name = 'audit.log'
    _description = 'Audit Log'
    _order = 'timestamp desc, id desc'
    _rec_name = 'display_name'

    model_name = fields.Char(required=True, index=True, string='Model')
    record_id = fields.Integer(required=True, index=True, string='Record ID')
    res_id = fields.Reference(
        string='Record',
        selection='_select_record',
        compute='_compute_res_id',
        readonly=True,
    )
    field_name = fields.Char(string='Field')
    old_value = fields.Text(string='Old Value')
    new_value = fields.Text(string='New Value')
    action = fields.Selection([
        ('create', 'Created'),
        ('write', 'Updated'),
        ('unlink', 'Deleted'),
    ], required=True, string='Action')
    user_id = fields.Many2one('res.users', required=True, default=lambda self: self.env.user)
    timestamp = fields.Datetime(default=fields.Datetime.now, index=True)
    ip_address = fields.Char(string='IP Address')
    display_name = fields.Char(compute='_compute_display_name', string='Summary')

    def write(self, vals):
        if not self.env.context.get('install_mode') and not self.env.context.get('test_enable'):
            raise UserError("Audit log entries are immutable and cannot be modified.")
        return super().write(vals)

    def unlink(self):
        if not self.env.context.get('install_mode') and not self.env.context.get('test_enable'):
            raise UserError("Audit log entries are immutable and cannot be deleted.")
        return super().unlink()

    def _select_record(self):
        return [
            ('product.product', 'Product'),
            ('sale.order', 'Sale Order'),
            ('purchase.order', 'Purchase Order'),
            ('mrp.production', 'Manufacturing Order'),
            ('mrp.bom', 'Bill of Material'),
            ('mrp.work.order', 'Work Order'),
            ('mrp.work.center', 'Work Center'),
        ]

    @api.depends('model_name', 'record_id')
    def _compute_res_id(self):
        for rec in self:
            if rec.model_name and rec.record_id:
                rec.res_id = '%s,%d' % (rec.model_name, rec.record_id)
            else:
                rec.res_id = None

    @api.depends('action', 'model_name', 'record_id', 'field_name', 'timestamp')
    def _compute_display_name(self):
        for rec in self:
            action_label = dict(self._fields['action'].selection).get(rec.action, rec.action)
            parts = [action_label, rec.model_name or '', str(rec.record_id or '')]
            if rec.field_name:
                parts.append(rec.field_name)
            rec.display_name = ' / '.join(parts)

    @api.model
    def _get_ip(self):
        try:
            if request and request.httprequest:
                return request.httprequest.remote_addr or ''
        except Exception:
            pass
        return ''


class AuditMixin(models.AbstractModel):
    _name = 'audit.mixin'
    _description = 'Audit Mixin — Automatic create/write/unlink tracking'

    def _get_audit_excluded_fields(self):
        return {'id', 'create_uid', 'create_date', 'write_uid', 'write_date',
                '__last_update', 'display_name'}

    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for record, vals in zip(records, vals_list):
            tracked = {k: v for k, v in (vals or {}).items()
                       if k not in record._get_audit_excluded_fields()}
            if tracked:
                self.env['audit.log'].create({
                    'model_name': record._name,
                    'record_id': record.id,
                    'action': 'create',
                    'new_value': ', '.join(f'{k}={v}' for k, v in tracked.items()),
                    'user_id': self.env.user.id,
                    'ip_address': self.env['audit.log']._get_ip(),
                })
        return records

    def write(self, vals):
        excluded = self._get_audit_excluded_fields()
        tracked = {k: v for k, v in vals.items() if k not in excluded}
        if not tracked:
            return super().write(vals)
        old_values = {}
        for record in self:
            old_values[record.id] = {}
            for field_name in tracked:
                old = record._fields[field_name].convert_to_record(
                    record[field_name], record
                ) if record._fields.get(field_name) else record[field_name]
                old_values[record.id][field_name] = str(old) if old is not None else ''
        result = super().write(vals)
        for record in self:
            for field_name, new_value in tracked.items():
                self.env['audit.log'].create({
                    'model_name': record._name,
                    'record_id': record.id,
                    'field_name': field_name,
                    'action': 'write',
                    'old_value': old_values.get(record.id, {}).get(field_name, ''),
                    'new_value': str(new_value) if new_value is not None else '',
                    'user_id': self.env.user.id,
                    'ip_address': self.env['audit.log']._get_ip(),
                })
        return result

    def unlink(self):
        records_info = [(r.id, r._name, r.display_name or '') for r in self]
        result = super().unlink()
        for rec_id, model_name, display_name in records_info:
            self.env['audit.log'].create({
                'model_name': model_name,
                'record_id': rec_id,
                'action': 'unlink',
                'old_value': display_name,
                'user_id': self.env.user.id,
                'ip_address': self.env['audit.log']._get_ip(),
            })
        return result
