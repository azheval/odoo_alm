from odoo import models, fields, api

class Requirement(models.Model):
    _name = 'alm.requirement'
    _description = 'Requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'code desc'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    code = fields.Char(
        string='Code',
        required=True,
        readonly=True,
        default='/',
        copy=False,
    )
    description = fields.Html(
        string='Description',
        translate=True,
    )
    state = fields.Selection(
        selection=[
            ('draft', 'Draft'),
            ('clarification', 'Clarification'),
            ('confirmed', 'Confirmed'),
            ('in_progress', 'In Progress'),
            ('done', 'Done'),
            ('rejected', 'Rejected'),
        ],
        string='State',
        default='draft',
        tracking=True,
    )
    priority = fields.Selection(
        selection=[
            ('1', 'Low'),
            ('2', 'Medium'),
            ('3', 'High'),
            ('4', 'Critical'),
        ],
        string='Priority',
        default='2',
    )
    source = fields.Text(
        string='Source',
        help="Where did this requirement come from? (e.g., customer meeting, support ticket, etc.)"
    )
    
    # Dates
    date_finished = fields.Date(string='Finished Date', readonly=True)

    # Responsible Parties
    author_id = fields.Many2one(
        'res.users', 
        string='Author', 
        default=lambda self: self.env.user,
        readonly=True,
    )
    responsible_id = fields.Many2one(
        'res.users', 
        string='Responsible', 
        tracking=True,
    )

    # Hierarchy
    parent_id = fields.Many2one(
        'alm.requirement', 
        string='Parent Requirement', 
        ondelete='cascade',
        index=True,
    )
    child_ids = fields.One2many(
        'alm.requirement', 
        'parent_id', 
        string='Sub-requirements',
    )

    # Categorization
    category_id = fields.Many2one(
        comodel_name='alm.requirement.category',
        string='Category',
    )
    tag_ids = fields.Many2many(
        comodel_name='alm.configurable.unit.tag',
        relation='alm_requirement_tag_rel',
        column1='requirement_id',
        column2='tag_id',
        string='Tags',
    )
    project_id = fields.Many2one(
        comodel_name='project.project',
        string='Project',
        ondelete='cascade',
    )

    # Linked Objects
    task_ids = fields.One2many(
        comodel_name='project.task',
        inverse_name='requirement_id',
        string='Tasks',
    )
    metadata_object_ids = fields.Many2many(
        comodel_name='alm.metadata.object',
        relation='alm_requirement_metadata_object_rel',
        column1='requirement_id',
        column2='metadata_object_id',
        string='Metadata Objects',
    )
    process_ids = fields.Many2many(
        comodel_name='alm.process',
        relation='alm_requirement_process_rel',
        column1='requirement_id',
        column2='process_id',
        string='Processes',
    )
    function_ids = fields.Many2many(
        comodel_name='alm.process.function',
        relation='alm_requirement_process_function_rel',
        column1='requirement_id',
        column2='function_id',
        string='Functions',
    )
    integration_ids = fields.Many2many(
        comodel_name='alm.data.flow.integration',
        relation='alm_requirement_integration_rel',
        column1='requirement_id',
        column2='integration_id',
        string='Integrations',
    )
    bug_ids = fields.Many2many(
        comodel_name='alm.bug',
        relation='alm_requirement_bug_rel',
        column1='requirement_id',
        column2='bug_id',
        string='Bugs',
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', '/') == '/':
                vals['code'] = self.env['ir.sequence'].next_by_code('alm.requirement') or '/'
        return super().create(vals_list)

    def write(self, vals):
        if 'state' in vals and vals['state'] == 'done':
            vals['date_finished'] = fields.Date.today()
        return super().write(vals)

