from odoo import fields, models

class TestCaseScenario(models.Model):
    _name = 'alm.test.case.scenario'
    _description = 'Test Case Scenario'
    _order = 'sequence, id'

    name = fields.Char(string='Name', required=True)
    parameters = fields.Char(string='Parameters')
    test_case_id = fields.Many2one('alm.test.case', string='Test Case', ondelete='cascade')
    sequence = fields.Integer(string='Sequence', default=10)
