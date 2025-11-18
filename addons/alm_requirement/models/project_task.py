from odoo import models, fields

class ProjectTask(models.Model):
    _inherit = 'project.task'

    requirement_id = fields.Many2one(
        comodel_name='alm.requirement',
        string='Requirement',
        ondelete='set null',
        help="The requirement this task is fulfilling.",
    )
