from odoo import models, fields

class AlmProcess(models.Model):
    _inherit = 'alm.process'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_process_rel',
        column1='process_id',
        column2='requirement_id',
        string='Requirements',
        help="The requirements related to this process.",
    )
