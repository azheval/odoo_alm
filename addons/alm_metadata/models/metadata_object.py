from odoo import models, fields, api, _

class MetadataObject(models.Model):
    _name = 'alm.metadata.object'
    _description = 'ALM Metadata Object'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Display Name', required=True, index=True, help="Name to be displayed in Odoo interface.")
    
    technical_name = fields.Char(string='Technical Name', index=True, help="The technical name of the object in the source application.")
    technical_guid = fields.Char(string='Technical GUID', index=True, help="The GUID of the object in the source application.")

    description = fields.Text(string='Description')
    comment = fields.Text(string='Comment')

    attribute_ids = fields.One2many(
        'alm.metadata.object.attribute',
        'object_id',
        string='Attributes'
    )
    
    type_id = fields.Many2one(
        'alm.metadata.object.type', 
        string='Type', 
        required=True,
        ondelete='restrict'
    )

    version_id = fields.Many2one(
        'alm.configurable.unit.version', 
        string='Version', 
        ondelete='cascade', 
        required=True,
        index=True
    )
    
    unit_id = fields.Many2one(
        'alm.configurable.unit', 
        string='Configurable Unit',
        related='version_id.unit_id', 
        store=True,
        index=True
    )

    _sql_constraints = [
        ('technical_guid_version_uniq', 'unique (technical_guid, version_id)', 'The GUID must be unique within a version!')
    ]
