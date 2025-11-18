from odoo import models, fields

class MetadataObject(models.Model):
    _inherit = 'alm.metadata.object'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_metadata_object_rel',
        column1='metadata_object_id',
        column2='requirement_id',
        string='Requirements',
        help="The requirements related to this metadata object.",
    )
