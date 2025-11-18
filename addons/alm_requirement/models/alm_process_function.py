from odoo import models, fields

class AlmProcessFunction(models.Model):
    _inherit = 'alm.process.function'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_process_function_rel',
        column1='function_id',
        column2='requirement_id',
        string='Requirements',
        help="The requirements related to this process function.",
    )
