from odoo import http
from odoo.http import request
import base64

class TestScriptDownloader(http.Controller):

    @http.route('/alm_test/download_script/<int:case_id>/<string:script_type>', type='http', auth='user')
    def download_test_script(self, case_id, script_type, **kw):
        """
        This controller method handles the download of a test script.
        It fetches the test case by its ID, retrieves the script content
        and filename based on the script_type (gherkin or playwright),
        and returns it as a file download.
        """
        test_case = request.env['alm.test.case'].sudo().browse(case_id)
        if not test_case.exists():
            return request.not_found()

        script_content = None
        filename = None

        if script_type == 'gherkin' and test_case.gherkin_script:
            script_content = test_case.gherkin_script.encode('utf-8')
            filename = test_case.gherkin_script_filename or f'{test_case.name or "test"}.feature'
        elif script_type == 'playwright' and test_case.playwright_script:
            script_content = test_case.playwright_script.encode('utf-8')
            filename = test_case.playwright_script_filename or f'{test_case.name or "test"}.py'

        if not script_content:
            return request.make_response("There is no script content to download for the selected type.")

        headers = [
            ('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Disposition', f'attachment; filename="{filename}"'),
            ('Content-Length', len(script_content)),
        ]

        return request.make_response(script_content, headers)
