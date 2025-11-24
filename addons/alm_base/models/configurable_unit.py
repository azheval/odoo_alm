from odoo import api, models, fields, _

class ConfigurableUnit(models.Model):
    _name = 'alm.configurable.unit'
    _description = 'ALM Configurable Unit'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(
        string=_('Name'),
        required=True,
        tracking=True,
    )

    technical_name = fields.Char(
        string=_('Technical Name'),
        copy=False,
        tracking=True,
    )

    unit_type = fields.Selection(
        string=_('Unit Type'),
        selection=[
            ('configuration', _('Configuration')),
            ('extension', _('Extension')),
            ('library', _('Library')),
        ],
        required=True,
        tracking=True,
    )

    user_ids = fields.Many2many(
        'res.users',
        string=_('Users'),
        tracking=True,
    )

    tag_ids = fields.Many2many(
        'alm.configurable.unit.tag',
        string=_('Tags'),
    )

    version_ids = fields.One2many(
        'alm.configurable.unit.version',
        'unit_id',
        string=_('Versions'),
    )

    active = fields.Boolean(
        default=True,
    )

    development_version_count = fields.Integer(string='Development Versions', compute='_compute_counts')
    published_version_count = fields.Integer(string='Published Versions', compute='_compute_counts')
    unsupported_version_count = fields.Integer(string='Unsupported Versions', compute='_compute_counts')

    new_bug_count = fields.Integer(string='New Bugs', compute='_compute_counts')
    confirmed_bug_count = fields.Integer(string='Confirmed Bugs', compute='_compute_counts')
    fixed_bug_count = fields.Integer(string='Fixed Bugs', compute='_compute_counts')

    @api.depends('version_ids', 'version_ids.state')
    def _compute_counts(self):
        for unit in self:
            unit.development_version_count = len(unit.version_ids.filtered(lambda v: v.state == 'development'))
            unit.published_version_count = len(unit.version_ids.filtered(lambda v: v.state == 'published'))
            unit.unsupported_version_count = len(unit.version_ids.filtered(lambda v: v.state == 'unsupported'))

            bugs = self.env['alm.bug'].search([('reported_in_version_ids', 'in', unit.version_ids.ids)])
            unit.new_bug_count = len(bugs.filtered(lambda b: b.state == 'new'))
            unit.confirmed_bug_count = len(bugs.filtered(lambda b: b.state == 'confirmed'))
            unit.fixed_bug_count = len(bugs.filtered(lambda b: b.state == 'fixed'))
