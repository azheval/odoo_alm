def post_init_hook(cr, registry):
    from odoo.api import Environment
    env = Environment(cr, 1, {})
    env['alm_diagram.config'].update_drawio_parameter()
