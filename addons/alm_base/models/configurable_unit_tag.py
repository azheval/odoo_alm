from odoo import models, fields

class ConfigurableUnitTag(models.Model):
    _name = 'alm.configurable.unit.tag'
    _description = 'ALM Configurable Unit Tag'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True
    )
    
    color = fields.Integer(
        string='Color Index',
        default=0
    )

    _sql_constraints = [
        ('name_uniq', 'unique (name)', 'Tag name already exists!'),
    ]
