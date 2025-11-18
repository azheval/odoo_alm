from odoo import models, fields, api

class AlmDataFlowDataFlowEdge(models.Model):
    _name = 'alm_data_flow.data_flow.edge'
    _description = 'Data Flow Edge'
    _order = 'id'

    data_flow_id = fields.Many2one('alm.data.flow', string='Data Flow', required=True, ondelete='cascade')

    source_node_id = fields.Many2one(
        'alm_data_flow.data_flow.node',
        string='Source Node',
        required=True,
        ondelete='cascade',
        domain="[('data_flow_id', '=', data_flow_id)]"
    )

    target_node_id = fields.Many2one(
        'alm_data_flow.data_flow.node',
        string='Target Node',
        required=True,
        ondelete='cascade',
        domain="[('data_flow_id', '=', data_flow_id)]"
    )
    
    edge_type = fields.Selection([
        ('sequence', 'Sequence Flow'),
        ('message', 'Message Flow'),
        ('data', 'Data Association')
    ], string='Edge Type', required=True, default='sequence')

    condition_expression = fields.Text(string='Condition Expression')

    stroke_color = fields.Char(string='Stroke Color', default='#000000')
    stroke_width = fields.Integer(string='Stroke Width', default=1)
    font_color = fields.Char(string='Font Color', default='#000000')
    font_size = fields.Integer(string='Font Size', default=11)
