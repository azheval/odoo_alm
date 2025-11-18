from odoo import models, fields

class ConfigurableUnitVersionMetadata(models.Model):
    _inherit = 'alm.configurable.unit.version'

    metadata_object_ids = fields.One2many(
        'alm.metadata.object', 
        'version_id', 
        string='Metadata Objects'
    )
