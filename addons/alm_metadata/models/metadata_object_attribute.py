from odoo import models, fields, api

class MetadataObjectAttribute(models.Model):
    _name = 'alm.metadata.object.attribute'
    _description = 'ALM Metadata Object Attribute'
    _order = 'sequence,name'

    def _get_default_object_id(self):
        return self.env.context.get('default_object_id')

    name = fields.Char(
        string='Attribute Name', 
        required=True, 
        help="Name to be displayed in Odoo interface."
    )
    
    display_name = fields.Char(string='Display Name', compute='_compute_display_name', store=True, recursive=True)

    technical_name = fields.Char(
        string='Technical Name', 
        help="The technical name of the attribute in the source application."
    )

    object_id = fields.Many2one(
        'alm.metadata.object', 
        string='Metadata Object', 
        required=True, 
        ondelete='cascade',
        default=_get_default_object_id,
    )

    parent_id = fields.Many2one(
        'alm.metadata.object.attribute',
        string='Parent Attribute',
        ondelete='cascade',
        domain="[('object_id', '=', object_id)]"
    )

    child_ids = fields.One2many(
        'alm.metadata.object.attribute',
        'parent_id',
        string='Child Attributes'
    )

    sequence = fields.Integer(string='Sequence', default=10)

    type_id = fields.Many2one(
        'alm.metadata.object.type',
        string='Type',
        help="The data type of the attribute. Can be a primitive type or a reference to another metadata object type."
    )
    
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('technical_name_object_uniq', 'unique (technical_name, object_id, parent_id)', 'The technical name must be unique within a metadata object or parent attribute!')
    ]

    @api.depends('name', 'parent_id.display_name')
    def _compute_display_name(self):
        for rec in self:
            if rec.parent_id:
                rec.display_name = f"{rec.parent_id.display_name} / {rec.name}"
            elif rec.object_id:
                rec.display_name = f"{rec.object_id.name} / {rec.name}"
            else:
                rec.display_name = rec.name
