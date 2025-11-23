from odoo import models, fields, api, _

class BugReportWizard(models.TransientModel):
    _name = 'bug.report.wizard'
    _description = 'Bug Report Wizard'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')
    version_ids = fields.Many2many(
        'alm.configurable.unit.version',
        string='Versions',
        help="Leave empty to include all versions."
    )

    def generate_report(self):
        # Clear previous report data for the current user
        self.env['bug.report.line'].sudo().search([('create_uid', '=', self.env.user.id)]).unlink()

        versions = self.version_ids
        if not versions:
            versions = self.env['alm.configurable.unit.version'].search([])

        report_lines = []
        for version in versions:
            # Domain for registered bugs in this version
            registered_domain = [('reported_in_version_ids', 'in', version.id)]
            if self.date_from:
                registered_domain.append(('detection_date', '>=', self.date_from))
            if self.date_to:
                registered_domain.append(('detection_date', '<=', self.date_to))
            
            registered_bugs = self.env['alm.bug'].search(registered_domain)
            for bug in registered_bugs:
                report_lines.append({
                    'bug_id': bug.id,
                    'version_id': version.id,
                    'report_type': 'registered',
                    'create_uid': self.env.user.id,
                })

            # Domain for fixed bugs in this version
            fixed_domain = [('fixed_in_version_ids', 'in', version.id), ('state', '=', 'fixed')]
            if self.date_from:
                fixed_domain.append(('fix_date', '>=', self.date_from))
            if self.date_to:
                fixed_domain.append(('fix_date', '<=', self.date_to))
            
            fixed_bugs = self.env['alm.bug'].search(fixed_domain)
            for bug in fixed_bugs:
                report_lines.append({
                    'bug_id': bug.id,
                    'version_id': version.id,
                    'report_type': 'fixed',
                    'create_uid': self.env.user.id,
                })

        if report_lines:
            self.env['bug.report.line'].sudo().create(report_lines)

        return {
            'name': _('Bug Report'),
            'type': 'ir.actions.act_window',
            'res_model': 'bug.report.line',
            'view_mode': 'pivot,graph,list',
            'context': {
                'group_by': ['configurable_unit_id', 'version_id'],
                'pivot_column_groupby': ['report_type'],
                },
        }
