from odoo import models, fields

class Bug(models.Model):
    _inherit = 'alm.bug'

    requirement_ids = fields.Many2many(
        comodel_name='alm.requirement',
        relation='alm_requirement_bug_rel',
        column1='bug_id',
        column2='requirement_id',
        string='Requirements',
        help="The requirements related to this bug.",
    )
