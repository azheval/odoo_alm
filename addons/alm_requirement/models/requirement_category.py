from odoo import models, fields

class RequirementCategory(models.Model):
    _name = 'alm.requirement.category'
    _description = 'Requirement Category'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    description = fields.Text(
        string='Description',
        translate=True,
    )
