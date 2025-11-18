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
