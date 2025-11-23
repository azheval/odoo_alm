from odoo import models, fields, api, _

class AlmProcessFunction(models.Model):
    _name = 'alm.process.function'
    _description = 'ALM Process Function/Step'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description')

    process_id = fields.Many2one(
        'alm.process',
        string='Process',
        required=True,
        ondelete='cascade',
        help="The process this function/step belongs to.",
        tracking=True,
    )

    application_id = fields.Many2one(
        'alm.configurable.unit',
        string='Configurable Unit',
        related='process_id.application_id',
        store=True,
    )

    sequence = fields.Integer(string='Sequence', default=10, help="Order of execution within the process.")

    responsible_role_id = fields.Many2one(
        'alm.metadata.object',
        string='Responsible Role',
        domain="[('type_id.technical_name', '=', 'Role')]",
        help="The role responsible for executing this function/step.",
        tracking=True,
    )

    input_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_process_function_input_metadata_rel',
        column1='function_id',
        column2='metadata_object_id',
        string='Input Metadata Objects',
        help="Metadata objects consumed by this function/step.",
    )

    output_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_process_function_output_metadata_rel',
        column1='function_id',
        column2='metadata_object_id',
        string='Output Metadata Objects',
        help="Metadata objects produced by this function/step.",
    )

    transformation_logic = fields.Text(string='Transformation Logic', help="Detailed logic for data transformation within this function/step.")
