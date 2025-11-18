from odoo import http
from odoo.http import request
import json

class DiagramController(http.Controller):

    @http.route('/alm_diagram/get_url', type='http', auth='user', methods=['POST'], csrf=False)
    def get_drawio_editor_url(self, **kw):
        """
        Controller to fetch the Draw.io editor URL from system parameters.
        This provides a stable endpoint for the frontend widget.
        """
        url = request.env['ir.config_parameter'].sudo().get_param('alm_diagram.drawio_editor_url')
        return request.make_response(
            json.dumps({'url': url or ''}),
            headers={'Content-Type': 'application/json'}
        )