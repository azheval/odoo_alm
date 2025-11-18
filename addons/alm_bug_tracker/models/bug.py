from odoo import models, fields, api

class AlmBug(models.Model):
    _name = 'alm.bug'
    _description = 'ALM Bug'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True)
    description = fields.Html(string='Description')

    bug_number = fields.Char(
        string='Bug Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: 'New'
    )

    @api.model
    def _default_bug_number(self):
        return self.env['ir.sequence'].next_by_code('alm.bug.sequence') or 'New'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('bug_number', 'New') == 'New':
                vals['bug_number'] = self.env['ir.sequence'].next_by_code('alm.bug.sequence') or 'New'
        return super(AlmBug, self).create(vals_list)

    state = fields.Selection([
        ('new', 'New'),
        ('confirmed', 'Confirmed'),
        ('rejected', 'Rejected'),
        ('fixed', 'Fixed'),
    ], string='State', default='new', required=True, tracking=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1')

    detection_method = fields.Selection([
        ('manual', 'Manual'),
        ('external', 'External'),
        ('automated', 'Automated'),
    ], string='Detection Method', default='manual', required=True)

    detection_date = fields.Datetime(string='Detection Date', default=fields.Datetime.now, required=True)
    fix_date = fields.Datetime(string='Fix Date', tracking=True)

    user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    reported_in_version_ids = fields.Many2many(
        'alm.configurable.unit.version',
        'alm_bug_reported_version_rel',
        'bug_id', 'version_id',
        string='Reported In Versions'
    )

    fixed_in_version_ids = fields.Many2many(
        'alm.configurable.unit.version',
        'alm_bug_fixed_version_rel',
        'bug_id', 'version_id',
        string='Fixed In Versions'
    )

    metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        'alm_bug_metadata_object_rel',
        'bug_id', 'metadata_object_id',
        string='Metadata Objects'
    )

    task_ids = fields.One2many('project.task', 'bug_id', string='Fixing Tasks')

    test_name = fields.Text(string='Detected by Test')
