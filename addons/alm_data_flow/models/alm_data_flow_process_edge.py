from odoo import models, fields, api

class AlmDataFlowProcessEdge(models.Model):
    _name = 'alm_data_flow.process.edge'
    _description = 'Process Edge for Data Flow Diagram'

    process_id = fields.Many2one('alm.process', string='Process', required=True, ondelete='cascade')

    source_node_id = fields.Many2one(
        'alm_data_flow.process.node', 
        string='Source Node', 
        required=True, 
        ondelete='cascade',
        domain="[('process_id', '=', process_id)]"  # ДОБАВЛЕН ДОМЕН
    )
    
    target_node_id = fields.Many2one(
        'alm_data_flow.process.node', 
        string='Target Node', 
        required=True, 
        ondelete='cascade',
        domain="[('process_id', '=', process_id)]"  # ДОБАВЛЕН ДОМЕН
    )
    
    edge_type = fields.Selection([
        ('sequence', 'Sequence Flow'),
        ('message', 'Message Flow'),
        ('data', 'Data Association')
    ], string='Edge Type', required=True, default='sequence')

    condition_expression = fields.Text(string='Condition Expression')
    is_default = fields.Boolean(string='Is Default Flow')

    stroke_color = fields.Char(string='Stroke Color', default='#000000')
    stroke_width = fields.Integer(string='Stroke Width', default=1)
    font_color = fields.Char(string='Font Color', default='#000000')
    font_size = fields.Integer(string='Font Size', default=11)
