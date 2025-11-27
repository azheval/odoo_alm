from odoo import fields, models

class TestSuite(models.Model):
    _name = 'alm.test.suite'
    _description = 'Test Suite'

    name = fields.Char(string='Name', required=True)
    description = fields.Text(string='Description')
    test_case_ids = fields.Many2many(
        'alm.test.case',
        string='Test Cases'
    )
