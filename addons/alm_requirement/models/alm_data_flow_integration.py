from odoo import models, fields, api

class AlmDataFlowIntegration(models.Model):
    _inherit = 'alm.data.flow.integration'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_integration_rel',
        column1='integration_id',
        column2='requirement_id',
        string='Requirements',
    )

    @api.onchange('data_flow_id')
    def _onchange_data_flow_id_requirements(self):
        if self.data_flow_id and self.data_flow_id.requirement_ids:
            self.requirement_ids = [(6, 0, self.data_flow_id.requirement_ids.ids)]
        else:
            self.requirement_ids = [(5, 0, 0)]
