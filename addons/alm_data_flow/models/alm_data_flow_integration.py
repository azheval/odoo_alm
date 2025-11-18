from odoo import models, fields, api, _
from lxml import etree
import logging
import random
import base64
import zlib
import urllib.parse

_logger = logging.getLogger(__name__)

class AlmDataFlowIntegration(models.Model):
    _name = 'alm.data.flow.integration'
    _description = 'ALM Data Flow Integration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description', tracking=True)

    data_flow_id = fields.Many2one(
        'alm.data.flow',
        string='Data Flow',
        required=True,
        ondelete='restrict',
        help="The data flow this integration belongs to.",
        tracking=True,
    )

    all_metadata_object_ids = fields.Many2many(
        related='data_flow_id.all_metadata_object_ids',
        string='All Metadata Objects',
    )

    field_map_ids = fields.One2many(
        'alm.data.flow.field.map',
        'integration_id',
        string='Field Mappings',
        help="Individual field mappings for this integration."
    )

    diagram_data = fields.Text(string="Diagram Data")

    def _get_predefined_colors(self):
        return [
            '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231', 
            '#911eb4', '#46f0f0', '#f032e6', '#bcf60c', '#fabebe',
            '#008080', '#e6beff', '#9A6324', '#fffac8', '#800000',
            '#aaffc3', '#808000', '#ffd8b1', '#000075', '#808080'
        ]

    def _extract_diagram_root(self, xml_data):
        if not xml_data:
            return None
        try:
            if xml_data.strip().startswith('<mxfile'):
                root = etree.fromstring(xml_data.encode('utf-8'))
                diagram_elem = root.find('diagram')
                if diagram_elem is not None and diagram_elem.text is not None:
                    diagram_content = diagram_elem.text
                    try:
                        decoded = base64.b64decode(diagram_content)
                        decompressed = zlib.decompress(decoded, -15)
                        unquoted = urllib.parse.unquote(decompressed.decode('utf-8'))
                        return etree.fromstring(unquoted.encode('utf-8'))
                    except (base64.binascii.Error, zlib.error, UnicodeDecodeError) as e:
                        try:
                            return etree.fromstring(diagram_content.encode('utf-8'))
                        except etree.XMLSyntaxError:
                            pass
                _logger.warning("_extract_diagram_root: No parsable diagram content found in mxfile")
                return None
            else:
                return etree.fromstring(xml_data.encode('utf-8'))
        except etree.XMLSyntaxError as e:
            _logger.warning(f"_extract_diagram_root: XML Syntax Error: {e}")
            return None
        except Exception as e:
            _logger.error(f"_extract_diagram_root: Unexpected error: {e}")
            return None

    def action_generate_mapping_diagram_xml(self, current_diagram_xml=None):
        self.ensure_one()
        _logger.info(f"Generating mapping diagram for integration: {self.name}")
        
        if (current_diagram_xml is None or current_diagram_xml == '') and self.diagram_data:
            current_diagram_xml = self.diagram_data
            _logger.info("Using diagram_data from database")
        
        ENTITY_WIDTH = 200
        ROW_HEIGHT = 26
        ENTITY_X_GAP = 150
        
        existing_positions = {}
        existing_path_colors = {}
        if current_diagram_xml:
            try:
                xml_root = self._extract_diagram_root(current_diagram_xml)
                _logger.info(f"Full XML structure: {etree.tostring(xml_root, encoding='unicode')[:1000]}")
                if xml_root is None:
                    _logger.warning("Could not extract valid mxGraphModel from current_diagram_xml. Existing positions/colors will not be restored.")
                else:
                    entity_cells = xml_root.xpath("//mxCell[@vertex='1']")
                    _logger.info(f"Vertex cells found: {len(entity_cells)}")
                    
                    for cell in entity_cells:
                        entity_name = cell.get('value')
                        geom = cell.find('mxGeometry')
                        style = cell.get('style', '')
                        if entity_name and geom is not None and 'shape=table' in style:
                            existing_positions[entity_name] = {'x': geom.get('x'), 'y': geom.get('y')}
                    edge_cells = xml_root.xpath("//mxCell[@edge='1']")
                    
                    for edge in edge_cells:
                        path_key = edge.get('path_key')
                        style = edge.get('style', '')
                        
                        if path_key and 'strokeColor=' in style:
                            color = style.split('strokeColor=')[1].split(';')[0]
                            if color and path_key not in existing_path_colors:
                                existing_path_colors[path_key] = color
                                _logger.info(f"✓ Found color for path {path_key}: {color}")
                                
            except Exception as e:
                _logger.warning(f"Could not parse existing diagram XML: {e}")
        
        
        root = etree.Element("mxGraphModel")
        root_cell = etree.SubElement(root, "root")
        etree.SubElement(root_cell, "mxCell", id="0")
        etree.SubElement(root_cell, "mxCell", id="1", parent="0")

        cell_id_counter = 2
        attribute_cell_map = {}
        
        used_object_ids = set()
        technical_fields = set()
        for mapping in self.field_map_ids:
            if mapping.source_field_id: used_object_ids.add(mapping.source_field_id.object_id.id)
            if mapping.target_field_id: used_object_ids.add(mapping.target_field_id.object_id.id)
            if mapping.technical_field: technical_fields.add(mapping.technical_field)
        
        used_objects = self.env['alm.metadata.object'].browse(list(used_object_ids))
        sorted_technical_fields = sorted(list(technical_fields))
        
        available_colors = self._get_predefined_colors()
        random.shuffle(available_colors)
        path_colors = existing_path_colors.copy()
        
        path_keys = set()
        for m in self.field_map_ids:
            path_key = m.technical_field if m.technical_field else f"direct_{m.id}"
            path_keys.add(path_key)

        for key in sorted(list(path_keys)):
            if key not in path_colors:
                path_colors[key] = available_colors.pop(0) if available_colors else '#666666'

        current_x, current_y = 50, 50
        
        all_entities_to_draw = list(used_objects)
        if sorted_technical_fields:
            tech_obj = {'name': "Technical Fields", 'attributes': sorted_technical_fields, 'is_tech': True}
            all_entities_to_draw.append(tech_obj)

        for entity in all_entities_to_draw:
            is_tech_block = isinstance(entity, dict) and entity.get('is_tech')
            entity_name = entity['name'] if is_tech_block else entity.name
            
            pos = existing_positions.get(entity_name, {'x': str(current_x), 'y': str(current_y)})

            if is_tech_block:
                attributes = [{'name': name} for name in entity['attributes']]
                entity_height = ROW_HEIGHT * (len(attributes) + 1)
                style = "shape=table;startSize=26;container=1;collapsible=1;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;fillColor=#dae8fc;strokeColor=#6c8ebf;"
            else:
                all_attrs = entity.attribute_ids.filtered(lambda a: not a.parent_id)
                entity_height = ROW_HEIGHT * (len(all_attrs) + 1)
                for attr in all_attrs: entity_height += ROW_HEIGHT * len(attr.child_ids)
                style = "shape=table;startSize=26;container=1;collapsible=1;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;"

            entity_cell_id = str(cell_id_counter); cell_id_counter += 1
            entity_cell = etree.SubElement(root_cell, "mxCell", id=entity_cell_id, value=entity_name, style=style, parent="1", vertex="1")
            etree.SubElement(entity_cell, "mxGeometry", {'x': pos['x'], 'y': pos['y'], 'width': str(ENTITY_WIDTH), 'height': str(entity_height), 'as': "geometry"})

            attr_y_offset = ROW_HEIGHT
            if is_tech_block:
                for attr in attributes:
                    attr_cell_id = str(cell_id_counter); cell_id_counter += 1
                    attribute_cell_map[f"tech_{attr['name']}"] = attr_cell_id
                    attr_style = "shape=partialRectangle;collapsible=0;dropTarget=0;pointerEvents=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=6;"
                    attr_cell = etree.SubElement(root_cell, "mxCell", id=attr_cell_id, value=attr['name'], style=attr_style, parent=entity_cell_id, vertex="1")
                    etree.SubElement(attr_cell, "mxGeometry", {'y': str(attr_y_offset), 'width': str(ENTITY_WIDTH), 'height': str(ROW_HEIGHT), 'as': "geometry"})
                    attr_y_offset += ROW_HEIGHT
            else:
                for attr in entity.attribute_ids.filtered(lambda a: not a.parent_id).sorted('sequence'):
                    attr_cell_id = str(cell_id_counter); cell_id_counter += 1
                    attribute_cell_map[attr.id] = attr_cell_id
                    attr_style = "shape=partialRectangle;collapsible=0;dropTarget=0;pointerEvents=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=6;"
                    attr_cell = etree.SubElement(root_cell, "mxCell", id=attr_cell_id, value=attr.name, style=attr_style, parent=entity_cell_id, vertex="1")
                    etree.SubElement(attr_cell, "mxGeometry", {'y': str(attr_y_offset), 'width': str(ENTITY_WIDTH), 'height': str(ROW_HEIGHT), 'as': "geometry"})
                    attr_y_offset += ROW_HEIGHT
                    for child_attr in attr.child_ids.sorted('sequence'):
                        child_attr_cell_id = str(cell_id_counter); cell_id_counter += 1
                        attribute_cell_map[child_attr.id] = child_attr_cell_id
                        child_attr_style = "shape=partialRectangle;collapsible=0;dropTarget=0;pointerEvents=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=18;fontStyle=2;"
                        child_attr_cell = etree.SubElement(root_cell, "mxCell", id=child_attr_cell_id, value=child_attr.name, style=child_attr_style, parent=entity_cell_id, vertex="1")
                        etree.SubElement(child_attr_cell, "mxGeometry", {'y': str(attr_y_offset), 'width': str(ENTITY_WIDTH), 'height': str(ROW_HEIGHT), 'as': "geometry"})
                        attr_y_offset += ROW_HEIGHT
            
            if entity_name not in existing_positions:
                current_x += ENTITY_WIDTH + ENTITY_X_GAP

        for mapping in self.field_map_ids:
            source_cell_id, target_cell_id = None, None
            if mapping.source_field_id: source_cell_id = attribute_cell_map.get(mapping.source_field_id.id)
            elif mapping.technical_field: source_cell_id = attribute_cell_map.get(f"tech_{mapping.technical_field}")
            
            if mapping.target_field_id: target_cell_id = attribute_cell_map.get(mapping.target_field_id.id)
            elif mapping.technical_field and mapping.source_field_id: target_cell_id = attribute_cell_map.get(f"tech_{mapping.technical_field}")

            if source_cell_id and target_cell_id:
                path_key = mapping.technical_field if mapping.technical_field else f"direct_{mapping.id}"
                color = path_colors.get(path_key, '#666666')
                
                edge_cell_id = str(cell_id_counter); cell_id_counter += 1
                edge_style = f"edgeStyle=entityRelationEdgeStyle;endArrow=block;endFill=1;strokeWidth=1;rounded=0;strokeColor={color};"
                edge_attrib = {'id': edge_cell_id, 'style': edge_style, 'parent': "1", 'source': source_cell_id, 'target': target_cell_id, 'edge': "1", 'path_key': path_key}
                
                edge_cell = etree.SubElement(root_cell, "mxCell", attrib=edge_attrib)
                etree.SubElement(edge_cell, "mxGeometry", {'relative': "1", 'as': "geometry"})

        return etree.tostring(root, pretty_print=True, encoding='unicode')
