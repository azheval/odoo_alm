from odoo import models, fields, api

class AlmDataFlowProcessNode(models.Model):
    _name = 'alm_data_flow.process.node'
    _description = 'Process Node for Data Flow Diagram'

    process_id = fields.Many2one('alm.process', string='Process', required=True, ondelete='cascade')
    function_id = fields.Many2one(
        'alm.process.function', 
        string='Function',
        domain="[('process_id', '=', process_id)]"
    )
    
    name = fields.Char(string='Name', required=True)
    node_type = fields.Selection([
        ('function', 'Function'),
        ('start', 'Start'),
        ('end', 'End'),
        ('gateway', 'Gateway'),
        ('event', 'Event'),
        ('loop', 'Loop')
    ], string='Node Type', required=True, default='function')

    position_x = fields.Integer(string='Position X')
    position_y = fields.Integer(string='Position Y')

    width = fields.Integer(string='Width', default=120)
    height = fields.Integer(string='Height', default=60)
    fill_color = fields.Char(string='Fill Color', default='#ffffff')
    stroke_color = fields.Char(string='Stroke Color', default='#000000')
    stroke_width = fields.Integer(string='Stroke Width', default=1)
    font_color = fields.Char(string='Font Color', default='#000000')
    font_size = fields.Integer(string='Font Size', default=12)
    text_align = fields.Selection([
        ('left', 'Left'),
        ('center', 'Center'),
        ('right', 'Right')
    ], string='Text Alignment', default='center')

    metadata_in = fields.Json(string='Input Metadata')
    metadata_out = fields.Json(string='Output Metadata')
    
    condition = fields.Text(string='Condition')

    @api.onchange('function_id')
    def _onchange_function_id(self):
        if self.function_id:
            self.name = self.function_id.name
