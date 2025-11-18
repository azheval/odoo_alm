from odoo import models, fields, api, _
from odoo.exceptions import ValidationError

class AlmDataFlowFieldMap(models.Model):
    _name = 'alm.data.flow.field.map'
    _description = 'ALM Data Flow Field Mapping'
    _order = 'sequence,name'

    name = fields.Char(string='Name', compute='_compute_name', store=True, readonly=False)
    sequence = fields.Integer(string='Sequence', default=10)

    integration_id = fields.Many2one(
        'alm.data.flow.integration',
        string='Data Flow Integration',
        required=True,
        ondelete='cascade',
        help="The data flow integration this field mapping belongs to."
    )

    source_field_id = fields.Many2one(
        'alm.metadata.object.attribute',
        string='Source Field',
        ondelete='restrict',
        help="The source field for this mapping.",
        domain="[('object_id', 'in', parent.all_metadata_object_ids)]"
    )

    target_field_id = fields.Many2one(
        'alm.metadata.object.attribute',
        string='Target Field',
        ondelete='restrict',
        help="The target field for this mapping.",
        domain="[('object_id', 'in', parent.all_metadata_object_ids)]"
    )

    technical_field = fields.Char(
        string="Technical Field",
        help="Define an intermediate technical field for complex transformations."
    )

    transformation_logic = fields.Text(
        string='Transformation Logic',
        help="Any specific logic for transforming the data (e.g., 'Convert date format', 'Map enum values')."
    )
    
    notes = fields.Text(string='Notes', help="Any additional notes or comments for this field mapping.")

    @api.depends('source_field_id', 'target_field_id', 'technical_field')
    def _compute_name(self):
        for rec in self:
            source = rec.source_field_id.display_name if rec.source_field_id else ''
            target = rec.target_field_id.display_name if rec.target_field_id else ''
            tech = rec.technical_field

            if source and target:
                rec.name = f"{source} -> {target}"
            elif source and tech:
                rec.name = f"{source} -> [{tech}]"
            elif tech and target:
                rec.name = f"[{tech}] -> {target}"
            elif tech:
                rec.name = f"[{tech}]"
            elif source:
                rec.name = source
            elif target:
                rec.name = target
            else:
                rec.name = "New Mapping"

    @api.constrains('source_field_id', 'target_field_id', 'technical_field')
    def _check_valid_mapping(self):
        for record in self:
            has_source = bool(record.source_field_id)
            has_target = bool(record.target_field_id)
            has_tech = bool(record.technical_field)
            if not any([has_source, has_target, has_tech]):
                raise ValidationError(_("A mapping line cannot be empty."))
            if has_tech and not any([has_source, has_target]):
                raise ValidationError(_("A technical field must be used either as a source or a target for another field."))

