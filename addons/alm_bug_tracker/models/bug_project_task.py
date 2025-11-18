from odoo import models, fields

class ProjectTaskBug(models.Model):
    _inherit = 'project.task'

    bug_id = fields.Many2one('alm.bug', string='Related Bug')
