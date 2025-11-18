from odoo import fields, models, api

class ProjectConfigurableUnit(models.Model):
    _name = 'project.configurable.unit'
    _description = 'Project Configurable Units'
    
    project_id = fields.Many2one(
        'project.project',
        string='Project',
        required=True
    )
    configurable_unit_id = fields.Many2one(
        'alm.configurable.unit',
        string='Configurable Unit',
        required=True
    )

class ProjectProject(models.Model):
    _inherit = 'project.project'
    
    configurable_unit_ids = fields.Many2many(
        'alm.configurable.unit',
        string='Configurable Units',
        relation='project_configurable_unit_rel',
        column1='project_id',
        column2='configurable_unit_id',
        help='Configurable Units available in this project'
    )