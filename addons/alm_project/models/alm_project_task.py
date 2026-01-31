from odoo import fields, models, api

class ProjectTask(models.Model):
    _inherit = 'project.task'

    configurable_unit_id = fields.Many2one(
        'alm.configurable.unit',
        string='Configurable Unit',
        help='The Configurable Unit related to this task.',
        store=True,
        index=True,
        domain="[('id', 'in', available_configurable_unit_ids)]"
    )
    configurable_unit_version_id = fields.Many2one(
        'alm.configurable.unit.version',
        string='Configurable Unit Version',
        help='The Configurable Unit Version related to this task.',
        store=True,
        index=True,
        domain="[('unit_id', '=', configurable_unit_id), ('unit_id', 'in', available_configurable_unit_ids)]"
    )

    available_configurable_unit_ids = fields.Many2many(
        'alm.configurable.unit',
        string='Available Configurable Units',
        compute='_compute_available_configurable_units'
    )

    planned_date_begin = fields.Datetime(
        string='Start Date',
        help='Date when the work on the task is planned to begin'
    )
    planned_date_end = fields.Datetime(
        string='End Date',
        help='Date when the work on the task is planned to end'
    )

    predecessor_ids = fields.Many2many(
        'project.task', 
        'project_task_dependency_rel',
        'task_id',
        'predecessor_id',
        string='Predecessors',
        help='Tasks that must be completed before this task can begin'
    )

    @api.depends('project_id.configurable_unit_ids')
    def _compute_available_configurable_units(self):
        for task in self:
            if task.project_id and task.project_id.configurable_unit_ids:
                task.available_configurable_unit_ids = task.project_id.configurable_unit_ids
            else:
                task.available_configurable_unit_ids = False

    @api.onchange('configurable_unit_id')
    def _onchange_configurable_unit_id(self):
        self.configurable_unit_version_id = False

    @api.onchange('project_id')
    def _onchange_project_id(self):
        self.configurable_unit_id = False
        self.configurable_unit_version_id = False
