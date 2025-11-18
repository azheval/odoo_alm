from odoo import models, fields, api, _
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class AlmDataFlow(models.Model):
    _name = 'alm.data.flow'
    _description = 'ALM Data Flow'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description')

    application_ids = fields.Many2many(
        'alm.configurable.unit',
        string='Applications',
        help="The applications involved in this data flow.",
        tracking=True,
        required=True,
    )

    tag_ids = fields.Many2many(
        comodel_name='alm.configurable.unit.tag',
        relation='alm_data_flow_tag_rel',
        column1='data_flow_id',
        column2='tag_id',
        string='Tags',
    )

    node_ids = fields.One2many(
        'alm_data_flow.data_flow.node',
        'data_flow_id',
        string='Nodes',
    )
    
    edge_ids = fields.One2many(
        'alm_data_flow.data_flow.edge',
        'data_flow_id',
        string='Edges',
    )

    diagram = fields.Text(string='Diagram', help="XML or other format for visual layout of the data flow diagram.")

    input_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_data_flow_input_metadata_rel',
        string='Input Metadata Objects',
        compute='_compute_aggregated_metadata_objects',
        store=True,
        help="Aggregated metadata objects consumed by this data flow.",
    )
    
    output_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_data_flow_output_metadata_rel',
        string='Output Metadata Objects',
        compute='_compute_aggregated_metadata_objects',
        store=True,
        help="Aggregated metadata objects produced by this data flow.",
    )

    all_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        string='All Metadata Objects',
        compute='_compute_all_metadata_objects',
        store=True,
        help="All metadata objects (input and output) involved in this data flow.",
    )

    status = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('deprecated', 'Deprecated'),
    ], string='Status', default='draft', tracking=True)

    @api.depends('node_ids.process_id.input_metadata_object_ids', 'node_ids.process_id.output_metadata_object_ids')
    def _compute_aggregated_metadata_objects(self):
        for record in self:
            input_objects = self.env['alm.metadata.object']
            output_objects = self.env['alm.metadata.object']
            
            process_nodes = record.node_ids.filtered(lambda n: n.process_id)
            for node in process_nodes:
                input_objects |= node.process_id.input_metadata_object_ids
                output_objects |= node.process_id.output_metadata_object_ids
            
            record.input_metadata_object_ids = input_objects
            record.output_metadata_object_ids = output_objects

    @api.depends('input_metadata_object_ids', 'output_metadata_object_ids')
    def _compute_all_metadata_objects(self):
        for record in self:
            record.all_metadata_object_ids = record.input_metadata_object_ids | record.output_metadata_object_ids

    def _get_node_style(self, node):
        """Generate style string for node with colors and styling"""
        style_parts = ["whiteSpace=wrap", "html=1"]
        
        if node.node_type == 'gateway':
            style_parts.extend(["shape=rhombus", "perimeter=rhombusPerimeter"])
            default_fill = '#fff59d'
            default_stroke = '#f9a825'
        elif node.node_type == 'start':
            style_parts.extend(["shape=ellipse", "perimeter=ellipsePerimeter"])
            default_fill = '#c5e1a5'
            default_stroke = '#388e3c'
        elif node.node_type == 'end':
            style_parts.extend(["shape=ellipse", "perimeter=ellipsePerimeter"])
            default_fill = '#ef9a9a'
            default_stroke = '#c62828'
        elif node.node_type == 'event':
            style_parts.extend(["shape=circle", "perimeter=ellipsePerimeter"])
            default_fill = '#e1bee7'
            default_stroke = '#7b1fa2'
        elif node.node_type == 'loop':
            style_parts.extend(["shape=hexagon", "perimeter=hexagonPerimeter"])
            default_fill = '#ffcc80'
            default_stroke = '#ef6c00'
        else:
            style_parts.extend(["shape=rectangle", "perimeter=rectanglePerimeter", "rounded=0"])
            default_fill = '#bbdefb'
            default_stroke = '#1976d2'
        
        fill_color = node.fill_color if node.fill_color and node.fill_color != '#ffffff' else default_fill
        stroke_color = node.stroke_color if node.stroke_color and node.stroke_color != '#000000' else default_stroke
        font_color = node.font_color if node.font_color else '#000000'
        font_size = node.font_size if node.font_size else 12
        stroke_width = node.stroke_width if node.stroke_width else 1
        
        style_parts.extend([
            f"fillColor={fill_color}",
            f"strokeColor={stroke_color}",
            f"fontColor={font_color}",
            f"fontSize={font_size}",
            f"strokeWidth={stroke_width}"
        ])
        
        return ";".join(style_parts)

    def _get_edge_style(self, edge):
        style_parts = ["endArrow=classic", "html=1", "rounded=0"]
        
        stroke_color = edge.stroke_color if edge.stroke_color and edge.stroke_color != '#000000' else '#2e7d32'
        font_color = edge.font_color if edge.font_color else '#000000'
        font_size = edge.font_size if edge.font_size else 11
        stroke_width = edge.stroke_width if edge.stroke_width else 1
        
        style_parts.extend([
            f"strokeColor={stroke_color}",
            f"fontColor={font_color}",
            f"fontSize={font_size}",
            f"strokeWidth={stroke_width}"
        ])
        
        if edge.edge_type == 'message':
            style_parts.append("dashed=1")
        elif edge.edge_type == 'data':
            style_parts.extend(["dashed=1", "dashPattern=3 3"])
        
        return ";".join(style_parts)

    @api.model
    def action_generate_diagram_xml(self, data_flow_id):
        data_flow = self.browse(data_flow_id)
        data_flow.ensure_one()
        _logger.info(f"Generating diagram for data flow: {data_flow.name}")

        try:
            positions = {}
            for node in data_flow.node_ids:
                if node.position_x is not None and node.position_y is not None and (node.position_x != 0 or node.position_y != 0):
                    positions[node.id] = {'x': node.position_x, 'y': node.position_y}

            if len(positions) != len(data_flow.node_ids):
                layout_successful = False
                try:
                    import networkx as nx
                    G = nx.DiGraph()
                    node_ids = [n.id for n in data_flow.node_ids]
                    G.add_nodes_from(node_ids)
                    edge_tuples = [(e.source_node_id.id, e.target_node_id.id) for e in data_flow.edge_ids]
                    G.add_edges_from(edge_tuples)

                    if G.nodes:
                        pos = nx.spring_layout(G, seed=42, iterations=100)
                        x_coords = [p[0] for p in pos.values()]
                        y_coords = [p[1] for p in pos.values()]
                        min_x, max_x = min(x_coords, default=0), max(x_coords, default=1)
                        min_y, max_y = min(y_coords, default=0), max(y_coords, default=1)
                        SCALE_X, SCALE_Y = 800, 600
                        for node_id, (x, y) in pos.items():
                            norm_x = (x - min_x) / (max_x - min_x) if max_x > min_x else 0.5
                            norm_y = (y - min_y) / (max_y - min_y) if max_y > min_y else 0.5
                            positions[node_id] = {'x': int(norm_x * SCALE_X), 'y': int(norm_y * SCALE_Y)}
                        layout_successful = True
                except ImportError:
                    _logger.warning("networkx library not found. Skipping auto-layout.")
                except Exception as e:
                    _logger.error(f"Error during auto-layout: {e}", exc_info=True)

                if not layout_successful:
                    _logger.info("Falling back to simple mathematical layout.")
                    nodes_without_positions = [n for n in data_flow.node_ids if n.id not in positions]
                    if nodes_without_positions:
                        existing_x = [pos['x'] for pos in positions.values()] if positions else [0]
                        existing_y = [pos['y'] for pos in positions.values()] if positions else [0]
                        start_x = max(existing_x) + 200 if existing_x and max(existing_x) > 0 else 50
                        start_y = max(existing_y) + 150 if existing_y and max(existing_y) > 0 else 50
                        current_x = start_x
                        current_y = start_y
                        for i, node in enumerate(nodes_without_positions):
                            positions[node.id] = {'x': current_x, 'y': current_y}
                            current_y += 150
                            if current_y > 800:
                                current_x += 200
                                current_y = start_y

            root = etree.Element("mxGraphModel")
            root_cell = etree.SubElement(root, "root")
            etree.SubElement(root_cell, "mxCell", id="0")
            etree.SubElement(root_cell, "mxCell", id="1", parent="0")

            node_cell_map = {}
            cell_id_counter = 2
            for node in data_flow.node_ids:
                node_cell_id = str(cell_id_counter)
                node_cell_map[node.id] = node_cell_id
                cell_id_counter += 1
                
                style = self._get_node_style(node)
                
                if node.node_type == 'process' and node.process_id:
                    label = f"{node.application_id.technical_name}.{node.process_id.name}" if node.application_id else node.process_id.name
                else:
                    label = node.name

                node_cell = etree.SubElement(root_cell, "mxCell", id=node_cell_id, value=label, style=style, parent="1", vertex="1", odoo_id=str(node.id))
                
                pos_x = node.position_x if node.position_x is not None and (node.position_x != 0 or node.position_y != 0) else positions.get(node.id, {}).get('x', 0)
                pos_y = node.position_y if node.position_y is not None and (node.position_x != 0 or node.position_y != 0) else positions.get(node.id, {}).get('y', 0)

                geom_attrib = {'x': str(pos_x), 'y': str(pos_y), 'width': str(node.width), 'height': str(node.height), 'as': "geometry"}
                etree.SubElement(node_cell, "mxGeometry", attrib=geom_attrib)

            for edge in data_flow.edge_ids:
                if edge.source_node_id.id in node_cell_map and edge.target_node_id.id in node_cell_map:
                    source_cell_id = node_cell_map[edge.source_node_id.id]
                    target_cell_id = node_cell_map[edge.target_node_id.id]
                    edge_cell_id = str(cell_id_counter)
                    cell_id_counter += 1
                    edge_style = self._get_edge_style(edge)
                    edge_attrib = {'id': edge_cell_id, 'style': edge_style, 'parent': "1", 'source': source_cell_id, 'target': target_cell_id, 'edge': "1"}
                    if edge.condition_expression:
                        edge_attrib['value'] = edge.condition_expression
                    edge_cell = etree.SubElement(root_cell, "mxCell", attrib=edge_attrib)
                    etree.SubElement(edge_cell, "mxGeometry", {'relative': "1", 'as': "geometry"})

            return etree.tostring(root, pretty_print=True, encoding='unicode')
        except Exception as e:
            _logger.error(f"Error generating diagram XML for data flow: {e}", exc_info=True)
            raise

    @api.model
    def action_update_from_diagram_xml(self, data_flow_id, xml_data):
        if not xml_data:
            return {'success': False, 'error': 'Empty XML data'}

        try:
            data_flow = self.env['alm.data.flow'].browse(data_flow_id)
            data_flow.ensure_one()
            
            root = self._extract_diagram_root(xml_data)
            if not root:
                return {'success': False, 'error': 'Could not extract diagram data'}

            nodes_result = self._synchronize_nodes(data_flow, root)
            edges_result = self._synchronize_edges(data_flow, root)

            message = f"Nodes: +{nodes_result['created']} ↑{nodes_result['updated']} ↓{nodes_result['deleted']} | Edges: +{edges_result['created']} ↑{edges_result['updated']} ↓{edges_result['deleted']}"
            
            return {'success': True, 'message': message}
        except Exception as e:
            _logger.error(f"Error updating data flow from diagram: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _extract_diagram_root(self, xml_data):
        try:
            if xml_data.startswith('<mxfile'):
                root = etree.fromstring(xml_data.encode('utf-8'))
                diagram_elem = root.find('diagram')
                if diagram_elem is not None and diagram_elem.text is not None:
                    import base64, zlib, urllib.parse
                    decoded = base64.b64decode(diagram_elem.text)
                    try:
                        decompressed = zlib.decompress(decoded, -15)
                    except zlib.error:
                        decompressed = decoded
                    unquoted = urllib.parse.unquote(decompressed.decode('utf-8'))
                    return etree.fromstring(unquoted.encode('utf-8'))
            else:
                return etree.fromstring(xml_data.encode('utf-8'))
        except Exception as e:
            _logger.error(f"Error extracting diagram root: {e}")
            return None

    def _determine_node_type(self, style, value):
        if not style: return 'process'
        style_lower = style.lower()
        value_lower = value.lower() if value else ''
        if 'ellipse' in style_lower:
            if 'start' in value_lower: return 'start'
            if 'end' in value_lower: return 'end'
            return 'event'
        if 'rhombus' in style_lower or 'diamond' in style_lower: return 'gateway'
        if 'hexagon' in style_lower: return 'loop'
        return 'process'

    def _synchronize_nodes(self, data_flow, root):
        result = {'created': 0, 'updated': 0, 'deleted': 0}
        existing_nodes = {node.id: node for node in data_flow.node_ids}
        diagram_node_ids = set()

        for cell in root.xpath("//mxCell[@vertex='1']"):
            odoo_id_str = cell.get('odoo_id')
            value = self._clean_html_tags(cell.get('value', ''))
            if not value: continue

            geom = cell.find('mxGeometry')
            style_dict = self._parse_style(cell.get('style', ''))
            node_type = self._determine_node_type(cell.get('style', ''), value)
            
            updates = {
                'name': value,
                'node_type': node_type,
                'position_x': int(float(geom.get('x', 0))),
                'position_y': int(float(geom.get('y', 0))),
                'width': int(float(geom.get('width', 160))),
                'height': int(float(geom.get('height', 80))),
                'fill_color': style_dict.get('fillColor', '#ffffff'),
                'stroke_color': style_dict.get('strokeColor', '#000000'),
                'stroke_width': int(style_dict.get('strokeWidth', 1)),
                'font_color': style_dict.get('fontColor', '#000000'),
                'font_size': int(style_dict.get('fontSize', 12)),
            }

            if odoo_id_str:
                odoo_id = int(odoo_id_str)
                diagram_node_ids.add(odoo_id)
                if odoo_id in existing_nodes:
                    node = existing_nodes[odoo_id]
                    if node.node_type == 'process':
                        updates.pop('name', None)
                    node.write(updates)
                    result['updated'] += 1
            else:
                if node_type != 'process':
                    updates['data_flow_id'] = data_flow.id
                    self.env['alm_data_flow.data_flow.node'].create(updates)
                    result['created'] += 1
        
        nodes_to_delete_ids = set(existing_nodes.keys()) - diagram_node_ids
        if nodes_to_delete_ids:
            nodes_to_delete = self.env['alm_data_flow.data_flow.node'].browse(nodes_to_delete_ids)
            nodes_to_delete.unlink()
            result['deleted'] = len(nodes_to_delete)
            
        return result

    def _synchronize_edges(self, data_flow, root):
        result = {'created': 0, 'updated': 0, 'deleted': 0}
        existing_edges = {(e.source_node_id.id, e.target_node_id.id): e for e in data_flow.edge_ids}
        diagram_edges = {}

        data_flow.invalidate_recordset(['node_ids'])
        node_map_by_key = {node.key: node for node in data_flow.node_ids}
        node_map_by_id = {node.id: node for node in data_flow.node_ids}
        
        cell_to_node = {}
        for cell in root.xpath("//mxCell[@vertex='1']"):
            odoo_id_str = cell.get('odoo_id')
            if odoo_id_str:
                cell_to_node[cell.get('id')] = node_map_by_id.get(int(odoo_id_str))
            else:
                key = self._clean_html_tags(cell.get('value', ''))
                cell_to_node[cell.get('id')] = node_map_by_key.get(key)

        for cell in root.xpath("//mxCell[@edge='1']"):
            source_node = cell_to_node.get(cell.get('source'))
            target_node = cell_to_node.get(cell.get('target'))
            
            if source_node and target_node:
                style_dict = self._parse_style(cell.get('style', ''))
                edge_type = 'sequence'
                if style_dict.get('dashed') == '1':
                    edge_type = 'data' if 'dashPattern' in style_dict else 'message'

                edge_data = {
                    'edge_type': edge_type,
                    'condition_expression': self._clean_html_tags(cell.get('value', '')),
                    'stroke_color': style_dict.get('strokeColor', '#000000'),
                    'stroke_width': int(style_dict.get('strokeWidth', 1)),
                    'font_color': style_dict.get('fontColor', '#000000'),
                    'font_size': int(style_dict.get('fontSize', 11)),
                }
                diagram_edges[(source_node.id, target_node.id)] = edge_data

        edges_to_delete = set(existing_edges.keys()) - set(diagram_edges.keys())
        if edges_to_delete:
            for source_id, target_id in edges_to_delete:
                existing_edges[(source_id, target_id)].unlink()
                result['deleted'] += 1

        for (source_id, target_id), data in diagram_edges.items():
            if (source_id, target_id) in existing_edges:
                existing_edges[(source_id, target_id)].write(data)
                result['updated'] += 1
            else:
                data.update({'data_flow_id': data_flow.id, 'source_node_id': source_id, 'target_node_id': target_id})
                self.env['alm_data_flow.data_flow.edge'].create(data)
                result['created'] += 1
        
        return result

    def _parse_style(self, style_string):
        return {p.split('=', 1)[0]: p.split('=', 1)[1] for p in style_string.split(';') if '=' in p}

    def _clean_html_tags(self, text):
        if not text: return ""
        import re
        return ' '.join(re.sub('<[^<]+?>', '', text).replace('&nbsp;', ' ').split()).strip()
