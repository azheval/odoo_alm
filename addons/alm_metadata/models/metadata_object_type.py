from odoo import models, fields

class MetadataObjectType(models.Model):
    _name = 'alm.metadata.object.type'
    _description = 'ALM Metadata Object Type'
    _order = 'name'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, translate=True)
    technical_name = fields.Char(string='Technical Name', required=True)

    _sql_constraints = [
        ('technical_name_uniq', 'unique (technical_name)', 'The technical name must be unique!')
    ]
