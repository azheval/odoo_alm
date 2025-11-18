from odoo import models, fields

class AlmDataFlowIntegration(models.Model):
    _inherit = 'alm.data.flow.integration'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_integration_map_rel',
        column1='integration_map_id',
        column2='requirement_id',
        string='Requirements',
        help="The requirements related to this integration map.",
    )
