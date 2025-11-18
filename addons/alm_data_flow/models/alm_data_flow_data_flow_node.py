from odoo import models, fields, api

class AlmDataFlowDataFlowNode(models.Model):
    _name = 'alm_data_flow.data_flow.node'
    _description = 'Data Flow Node'
    _order = 'id'

    data_flow_id = fields.Many2one('alm.data.flow', string='Data Flow', required=True, ondelete='cascade')
    
    node_type = fields.Selection([
        ('process', 'Process'),
        ('start', 'Start'),
        ('end', 'End'),
        ('gateway', 'Gateway'),
        ('event', 'Event'),
        ('loop', 'Loop')
    ], string='Node Type', required=True, default='process')

    process_id = fields.Many2one(
        'alm.process',
        string='Process',
        domain="[('application_id', 'in', parent.application_ids)]"
    )
    
    application_id = fields.Many2one(
        'alm.configurable.unit',
        string='Application',
        related='process_id.application_id',
        store=True,
        readonly=True
    )
    
    name = fields.Char(
        string='Name', 
        required=True,
        help="The name of the node in the diagram."
    )
    
    key = fields.Char(
        string='Key', 
        compute='_compute_key', 
        store=True,
        help="Unique key for the node, composed of the application and process name."
    )

    position_x = fields.Integer(string='Position X', help="Horizontal position in the diagram.")
    position_y = fields.Integer(string='Position Y', help="Vertical position in the diagram.")

    width = fields.Integer(string='Width', default=160)
    height = fields.Integer(string='Height', default=80)
    fill_color = fields.Char(string='Fill Color', default='#ffffff')
    stroke_color = fields.Char(string='Stroke Color', default='#000000')
    stroke_width = fields.Integer(string='Stroke Width', default=1)
    font_color = fields.Char(string='Font Color', default='#000000')
    font_size = fields.Integer(string='Font Size', default=12)

    @api.constrains('node_type', 'process_id')
    def _check_process_id(self):
        for record in self:
            if record.node_type == 'process' and not record.process_id:
                raise models.ValidationError("A process must be selected for nodes of type 'Process'.")

    @api.depends('process_id.name', 'application_id.technical_name', 'name', 'node_type')
    def _compute_key(self):
        for node in self:
            if node.node_type == 'process' and node.application_id and node.process_id:
                app_name = node.application_id.technical_name or 'no_app'
                proc_name = node.process_id.name or 'no_proc'
                node.key = f'{app_name}.{proc_name}'
            else:
                node.key = node.name

    @api.onchange('process_id')
    def _onchange_process_id(self):
        if self.node_type == 'process' and self.process_id:
            self.name = self.process_id.name
