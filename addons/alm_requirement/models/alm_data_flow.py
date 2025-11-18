from odoo import models, fields

class AlmDataFlow(models.Model):
    _inherit = 'alm.data.flow'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_data_flow_rel',
        column1='data_flow_id',
        column2='requirement_id',
        string='Requirements',
    )