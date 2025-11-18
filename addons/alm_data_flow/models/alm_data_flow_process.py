from odoo import models, fields, api, _
from lxml import etree
import logging

_logger = logging.getLogger(__name__)

class AlmProcess(models.Model):
    _name = 'alm.process'
    _description = 'ALM Process'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description')

    application_id = fields.Many2one(
        'alm.configurable.unit',
        string='Application',
        required=True,
        help="The application this process belongs to.",
        tracking=True,
    )

    tag_ids = fields.Many2many(
        comodel_name='alm.configurable.unit.tag',
        relation='alm_process_tag_rel',
        column1='process_id',
        column2='tag_id',
        string='Tags',
    )

    node_ids = fields.One2many(
        'alm_data_flow.process.node',
        'process_id',
        string='Nodes',
    )
    edge_ids = fields.One2many(
        'alm_data_flow.process.edge',
        'process_id',
        string='Edges',
    )

    diagram_data = fields.Text(string='Diagram Data', help="XML or other format for visual layout of the process diagram.")

    input_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_process_input_metadata_rel',
        string='Input Metadata Objects',
        compute='_compute_aggregated_metadata_objects',
        store=True,
        help="Aggregated metadata objects consumed by this process.",
    )
    output_metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        relation='alm_process_output_metadata_rel',
        string='Output Metadata Objects',
        compute='_compute_aggregated_metadata_objects',
        store=True,
        help="Aggregated metadata objects produced by this process.",
    )

    @api.depends('node_ids.function_id.input_metadata_object_ids', 'node_ids.function_id.output_metadata_object_ids')
    def _compute_aggregated_metadata_objects(self):
        for record in self:
            input_objects = self.env['alm.metadata.object']
            output_objects = self.env['alm.metadata.object']

            function_nodes = record.node_ids.filtered(lambda n: n.function_id)
            for node in function_nodes:
                input_objects |= node.function_id.input_metadata_object_ids
                output_objects |= node.function_id.output_metadata_object_ids
            record.input_metadata_object_ids = input_objects
            record.output_metadata_object_ids = output_objects


    @api.model
    def action_generate_diagram_xml(self, process_id):
        process = self.browse(process_id)
        process.ensure_one()
        _logger.info(f"Generating diagram for process: {process.name} using new graph model with styles")

        try:
            positions = {}
            
            for node in process.node_ids:
                if node.position_x is not None and node.position_y is not None and (node.position_x != 0 or node.position_y != 0):
                    positions[node.id] = {'x': node.position_x, 'y': node.position_y}
                    _logger.info(f"Node {node.name} has saved position: ({node.position_x}, {node.position_y})")
                else:
                    _logger.info(f"Node {node.name} has no valid position: ({node.position_x}, {node.position_y})")

            if len(positions) != len(process.node_ids):
                layout_successful = False
                try:
                    import networkx as nx
                    
                    G = nx.DiGraph()
                    node_ids = [n.id for n in process.node_ids]
                    G.add_nodes_from(node_ids)
                    
                    edge_tuples = [(e.source_node_id.id, e.target_node_id.id) for e in process.edge_ids]
                    G.add_edges_from(edge_tuples)

                    if G.nodes:
                        pos = nx.spring_layout(G, seed=42, iterations=100)

                        x_coords = [p[0] for p in pos.values()]
                        y_coords = [p[1] for p in pos.values()]
                        min_x, max_x = min(x_coords, default=0), max(x_coords, default=1)
                        min_y, max_y = min(y_coords, default=0), max(y_coords, default=1)

                        SCALE_X = 800
                        SCALE_Y = 600
                        
                        for node_id, (x, y) in pos.items():
                            norm_x = (x - min_x) / (max_x - min_x) if max_x > min_x else 0.5
                            norm_y = (y - min_y) / (max_y - min_y) if max_y > min_y else 0.5
                            positions[node_id] = {
                                'x': int(norm_x * SCALE_X),
                                'y': int(norm_y * SCALE_Y),
                            }
                        layout_successful = True
                        _logger.info("Successfully calculated networkx layout.")

                except ImportError:
                    _logger.warning("networkx library not found. Skipping auto-layout.")
                except Exception as layout_exc:
                    _logger.error(f"Error during auto-layout with networkx: {layout_exc}", exc_info=True)

                if not layout_successful:
                    _logger.info("Falling back to simple mathematical layout.")
                    nodes_without_positions = [n for n in process.node_ids if n.id not in positions]
                    _logger.info(f"Nodes without positions: {len(nodes_without_positions)}")
                    
                    if nodes_without_positions:
                        existing_x = [pos['x'] for pos in positions.values()] if positions else [0]
                        existing_y = [pos['y'] for pos in positions.values()] if positions else [0]
                        
                        start_x = max(existing_x) + 200 if existing_x and max(existing_x) > 0 else 50
                        start_y = max(existing_y) + 150 if existing_y and max(existing_y) > 0 else 50
                        
                        current_x = start_x
                        current_y = start_y
                        
                        for i, node in enumerate(nodes_without_positions):
                            positions[node.id] = {'x': current_x, 'y': current_y}
                            _logger.info(f"Assigned position to {node.name}: ({current_x}, {current_y})")
                            current_y += 150
                            
                            if current_y > 800:
                                current_x += 200
                                current_y = start_y
            else:
                _logger.info("All nodes have valid positions, skipping auto-layout")

            clean_nodes = self.env['alm_data_flow.process.node'].search([('process_id', '=', process.id)])
            fresh_edges = self.env['alm_data_flow.process.edge'].search([('process_id', '=', process.id)])

            root = etree.Element("mxGraphModel")
            root_cell = etree.SubElement(root, "root")
            etree.SubElement(root_cell, "mxCell", id="0")
            etree.SubElement(root_cell, "mxCell", id="1", parent="0")

            node_cell_map = {}
            cell_id_counter = 2
            
            def _get_node_style(node):
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
            
            def _get_edge_style(edge):
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

            for node in clean_nodes:
                node_cell_id = str(cell_id_counter)
                node_cell_map[node.id] = node_cell_id
                cell_id_counter += 1

                style = _get_node_style(node)
                
                width = node.width if node.width else 120
                height = node.height if node.height else 60
                
                node_cell = etree.SubElement(
                    root_cell, "mxCell",
                    id=node_cell_id,
                    value=node.name or '',
                    style=style,
                    parent="1",
                    vertex="1",
                    odoo_id=str(node.id)
                )
                
                if node.position_x is not None and node.position_y is not None and (node.position_x != 0 or node.position_y != 0):
                    pos_x = node.position_x
                    pos_y = node.position_y
                    _logger.info(f"Using saved position for {node.name}: ({pos_x}, {pos_y})")
                else:
                    pos_x = positions.get(node.id, {}).get('x', 0)
                    pos_y = positions.get(node.id, {}).get('y', 0)
                    _logger.info(f"Using calculated position for {node.name}: ({pos_x}, {pos_y})")
                
                geom_attrib = {
                    'x': str(pos_x),
                    'y': str(pos_y),
                    'width': str(width),
                    'height': str(height),
                    'as': "geometry"
                }
                etree.SubElement(node_cell, "mxGeometry", attrib=geom_attrib)

            for edge in fresh_edges:
                if edge.source_node_id.id in node_cell_map and edge.target_node_id.id in node_cell_map:
                    source_cell_id = node_cell_map[edge.source_node_id.id]
                    target_cell_id = node_cell_map[edge.target_node_id.id]
                    
                    edge_cell_id = str(cell_id_counter)
                    cell_id_counter += 1

                    edge_style = _get_edge_style(edge)
                    
                    edge_attrib = {
                        'id': edge_cell_id,
                        'style': edge_style,
                        'parent': "1",
                        'source': source_cell_id,
                        'target': target_cell_id,
                        'edge': "1"
                    }
                    if edge.condition_expression:
                        edge_attrib['value'] = edge.condition_expression

                    edge_cell = etree.SubElement(root_cell, "mxCell", attrib=edge_attrib)
                    
                    etree.SubElement(edge_cell, "mxGeometry", {'relative': "1", 'as': "geometry"})

            xml_string = etree.tostring(root, pretty_print=True, encoding='unicode')
            _logger.debug(f"Generated XML from graph model with styles: {xml_string}")
            return xml_string
        except Exception as e:
            _logger.error(f"Error generating diagram XML from graph model with styles: {e}", exc_info=True)
            raise

    @api.model
    def action_update_from_diagram_xml(self, process_id, xml_data):
        _logger.info(f"=== FULL DIAGRAM SYNC STARTED ===")
        _logger.info(f"Process ID: {process_id}")
        
        if not xml_data:
            _logger.warning("Received empty XML data. Aborting update.")
            return {'success': False, 'error': 'Empty XML data'}

        try:
            process = self.env['alm.process'].browse(process_id)
            if not process.exists():
                _logger.error(f"Process with ID {process_id} not found")
                return {'success': False, 'error': 'Process not found'}
                
            process.ensure_one()
            _logger.info(f"Processing diagram for: {process.name}")

            root = self._extract_diagram_root(xml_data)
            if not root:
                return {'success': False, 'error': 'Could not extract diagram data'}

            nodes_result = self._synchronize_nodes(process, root)
            
            edges_result = self._sync_edges(process, root)

            warnings = self._validate_business_rules(process, root)

            _logger.info(f"=== FULL DIAGRAM SYNC COMPLETED ===")
            result = {
                'nodes_created': nodes_result['nodes_created'],
                'nodes_updated': nodes_result['nodes_updated'], 
                'nodes_deleted': nodes_result['nodes_deleted'],
                'edges_created': edges_result['edges_created'],
                'edges_updated': edges_result['edges_updated'],
                'edges_deleted': edges_result['edges_deleted'],
                'warnings': warnings
            }
            _logger.info(f"Results: {result}")
            
            message = f"Nodes: +{result['nodes_created']} ↑{result['nodes_updated']} ↓{result['nodes_deleted']} | "
            message += f"Edges: +{result['edges_created']} ↑{result['edges_updated']} ↓{result['edges_deleted']}"
            
            if warnings:
                message += f" | Warnings: {len(warnings)}"
            
            return {
                'success': True,
                'results': result,
                'message': message
            }

        except Exception as e:
            _logger.error(f"=== FULL DIAGRAM SYNC FAILED ===")
            _logger.error(f"Unexpected error: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        
        

    def _extract_diagram_root(self, xml_data):
        try:
            if xml_data.startswith('<mxfile'):
                _logger.info("Detected mxfile format - extracting diagram data")
                root = etree.fromstring(xml_data.encode('utf-8'))
                diagram_elem = root.find('diagram')
                if diagram_elem is not None and diagram_elem.text is not None:
                    import base64
                    import zlib
                    import urllib.parse
                    
                    diagram_data_b64 = diagram_elem.text
                    diagram_data_compressed = base64.b64decode(diagram_data_b64)
                    
                    try:
                        diagram_data = zlib.decompress(diagram_data_compressed, -15)
                    except zlib.error:
                        diagram_data = diagram_data_compressed
                    
                    diagram_data_str = diagram_data.decode('utf-8')
                    
                    if diagram_data_str.startswith('%3C'):
                        diagram_data_str = urllib.parse.unquote(diagram_data_str)
                    
                    return etree.fromstring(diagram_data_str.encode('utf-8'))
            else:
                return etree.fromstring(xml_data.encode('utf-8'))
                
        except Exception as e:
            _logger.error(f"Error extracting diagram root: {e}")
            return None

    def _update_existing_nodes_positions(self, process, root):
        updated_nodes = 0
        
        cells_with_odoo_id = root.xpath("//mxCell[@vertex='1' and @odoo_id]")
        _logger.info(f"Found {len(cells_with_odoo_id)} cells with odoo_id")
        
        for cell in cells_with_odoo_id:
            odoo_id = cell.get('odoo_id')
            geom = cell.find('mxGeometry')
            
            if odoo_id and geom is not None:
                try:
                    node_id = int(odoo_id)
                    pos_x = int(float(geom.get('x', 0)))
                    pos_y = int(float(geom.get('y', 0)))
                    
                    _logger.info(f"Updating node {node_id} to position ({pos_x}, {pos_y})")

                    node_to_update = self.env['alm_data_flow.process.node'].browse(node_id)
                    
                    if node_to_update.exists() and node_to_update.process_id.id == process.id:
                        node_to_update.write({
                            'position_x': pos_x,
                            'position_y': pos_y,
                        })
                        updated_nodes += 1
                        _logger.info(f"Successfully updated node {node_id}")

                except (ValueError, TypeError) as e:
                    _logger.error(f"Error parsing node {odoo_id}: {e}")
                except Exception as e:
                    _logger.error(f"Unexpected error with node {odoo_id}: {e}")
        
        return updated_nodes

    def _create_new_nodes(self, process, root):
        new_nodes = 0
        
        cells_without_odoo_id = root.xpath("//mxCell[@vertex='1' and not(@odoo_id)]")
        _logger.info(f"Found {len(cells_without_odoo_id)} new cells without odoo_id")
        
        for cell in cells_without_odoo_id:
            try:
                value = cell.get('value', '')
                style = cell.get('style', '')
                geom = cell.find('mxGeometry')
                
                _logger.info(f"Processing new cell: value='{value}', style='{style}'")
                
                if not value or value.strip() == '':  
                    _logger.info(f"Skipping empty cell")
                    continue
                    
                pos_x = int(float(geom.get('x', 0))) if geom is not None else 0
                pos_y = int(float(geom.get('y', 0))) if geom is not None else 0
                
                _logger.info(f"Cell geometry: x={pos_x}, y={pos_y}")
                
                node_type = self._determine_node_type(style, value)
                _logger.info(f"Determined node type: {node_type}")
                
                existing_node = self.env['alm_data_flow.process.node'].search([
                    ('process_id', '=', process.id),
                    ('name', '=', value)
                ])
                
                if existing_node:
                    _logger.info(f"Node with name '{value}' already exists, skipping")
                    continue
                
                new_node = self.env['alm_data_flow.process.node'].create({
                    'process_id': process.id,
                    'name': value,
                    'node_type': node_type,
                    'position_x': pos_x,
                    'position_y': pos_y
                })
                
                new_nodes += 1
                _logger.info(f"SUCCESS: Created new node: '{value}' (type: {node_type}) at ({pos_x}, {pos_y}) with ID {new_node.id}")
                
            except Exception as e:
                _logger.error(f"Error creating new node: {e}", exc_info=True)
        
        _logger.info(f"Total new nodes created: {new_nodes}")
        return new_nodes

    def _determine_node_type(self, style, value):
        if not style:
            return 'function'
            
        style_lower = style.lower()
        value_lower = value.lower() if value else ''
        
        _logger.info(f"Determining type for style: '{style_lower}', value: '{value_lower}'")
        
        if 'ellipse' in style_lower:
            if 'start' in value_lower:
                return 'start'
            elif 'end' in value_lower:
                return 'end'
            return 'event'
        elif 'rhombus' in style_lower or 'diamond' in style_lower:
            return 'gateway'
        elif 'triangle' in style_lower:
            return 'event'
        elif 'circle' in style_lower:
            return 'event'
        elif 'rectangle' in style_lower:
            return 'function'
        
        if 'start' in value_lower:
            return 'start'
        elif 'end' in value_lower:
            return 'end'
        elif 'gateway' in value_lower or 'condition' in value_lower:
            return 'gateway'
        
        return 'function'

    def _sync_edges(self, process, root):
        result = {
            'edges_created': 0,
            'edges_updated': 0,
            'edges_deleted': 0
        }
        
        existing_edges = self.env['alm_data_flow.process.edge'].search([
            ('process_id', '=', process.id)
        ])
        
        process_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id)
        ])
        name_to_id = {node.name: node.id for node in process_nodes}
        
        diagram_edges = []
        edge_cells = root.xpath("//mxCell[@edge='1']")
        
        for edge_cell in edge_cells:
            edge_data = self._parse_edge_data(edge_cell, root, name_to_id)
            if edge_data and edge_data.get('source_node_id') and edge_data.get('target_node_id'):
                diagram_edges.append(edge_data)
        
        _logger.info(f"Diagram has {len(diagram_edges)} edges, DB has {len(existing_edges)} edges")
        
        processed_edge_keys = set()
        
        for edge_data in diagram_edges:
            edge_key = f"{edge_data['source_node_id']}_{edge_data['target_node_id']}"
            processed_edge_keys.add(edge_key)
            
            existing_edge = existing_edges.filtered(
                lambda e: e.source_node_id.id == edge_data['source_node_id'] and 
                        e.target_node_id.id == edge_data['target_node_id']
            )
            
            if existing_edge:
                updates = {}
                if edge_data.get('condition_expression') != existing_edge.condition_expression:
                    updates['condition_expression'] = edge_data.get('condition_expression', '')
                
                if edge_data.get('stroke_color') != existing_edge.stroke_color:
                    updates['stroke_color'] = edge_data.get('stroke_color', '#000000')
                
                if edge_data.get('stroke_width') != existing_edge.stroke_width:
                    updates['stroke_width'] = edge_data.get('stroke_width', 1)
                
                if edge_data.get('font_color') != existing_edge.font_color:
                    updates['font_color'] = edge_data.get('font_color', '#000000')
                
                if edge_data.get('font_size') != existing_edge.font_size:
                    updates['font_size'] = edge_data.get('font_size', 11)
                
                if updates:
                    existing_edge.write(updates)
                    result['edges_updated'] += 1
                    _logger.info(f"Updated edge: {edge_data['source_name']} -> {edge_data['target_name']}")
            else:
                self.env['alm_data_flow.process.edge'].create({
                    'process_id': process.id,
                    'source_node_id': edge_data['source_node_id'],
                    'target_node_id': edge_data['target_node_id'],
                    'edge_type': 'sequence',
                    'condition_expression': edge_data.get('condition_expression', ''),
                    'stroke_color': edge_data.get('stroke_color', '#000000'),
                    'stroke_width': edge_data.get('stroke_width', 1),
                    'font_color': edge_data.get('font_color', '#000000'),
                    'font_size': edge_data.get('font_size', 11)
                })
                result['edges_created'] += 1
                _logger.info(f"Created edge: {edge_data['source_name']} -> {edge_data['target_name']}")
        
        for edge in existing_edges:
            edge_key = f"{edge.source_node_id.id}_{edge.target_node_id.id}"
            if edge_key not in processed_edge_keys:
                _logger.info(f"Deleting edge: {edge.source_node_id.name} -> {edge.target_node_id.name}")
                edge.unlink()
                result['edges_deleted'] += 1
        
        return result

    def _parse_edge_data(self, edge_cell, root, name_to_id):
        try:
            source_id = edge_cell.get('source')
            target_id = edge_cell.get('target')
            condition = self._clean_html_tags(edge_cell.get('value', ''))
            style = edge_cell.get('style', '')
            
            style_dict = self._parse_style(style)
            stroke_color = style_dict.get('strokeColor', '#000000')
            stroke_width = int(style_dict.get('strokeWidth', 1))
            font_color = style_dict.get('fontColor', '#000000')
            font_size = int(style_dict.get('fontSize', 11))
            
            source_cell = root.xpath(f"//mxCell[@id='{source_id}']")
            target_cell = root.xpath(f"//mxCell[@id='{target_id}']")
            
            if source_cell and target_cell:
                source_name = self._clean_html_tags(source_cell[0].get('value', ''))
                target_name = self._clean_html_tags(target_cell[0].get('value', ''))
                
                source_node_id = name_to_id.get(source_name)
                target_node_id = name_to_id.get(target_name)
                
                if source_node_id and target_node_id:
                    return {
                        'source_node_id': source_node_id,
                        'target_node_id': target_node_id,
                        'source_name': source_name,
                        'target_name': target_name,
                        'condition_expression': condition,
                        'stroke_color': stroke_color,
                        'stroke_width': stroke_width,
                        'font_color': font_color,
                        'font_size': font_size
                    }
        
        except Exception as e:
            _logger.error(f"Error parsing edge data: {e}")
        
        return None
    
    def _synchronize_nodes(self, process, root):
        result = {
            'nodes_created': 0,
            'nodes_updated': 0, 
            'nodes_deleted': 0
        }
        
        existing_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id)
        ])
        existing_node_dict = {node.id: node for node in existing_nodes}
        existing_node_ids = set(existing_nodes.ids)
        
        diagram_nodes = []
        all_cells = root.xpath("//mxCell[@vertex='1']")
        
        for cell in all_cells:
            node_data = self._parse_cell_data(cell)
            if node_data and node_data.get('name'):
                diagram_nodes.append(node_data)
        
        _logger.info(f"Diagram has {len(diagram_nodes)} nodes, DB has {len(existing_nodes)} nodes")
        
        processed_node_ids = set()
        
        for node_data in diagram_nodes:
            node_result = self._sync_single_node(process, node_data, existing_node_dict)
            if node_result == 'created':
                result['nodes_created'] += 1
            elif node_result == 'updated':
                result['nodes_updated'] += 1
                
            if node_data.get('odoo_id'):
                processed_node_ids.add(node_data['odoo_id'])
        
        nodes_to_delete = existing_node_ids - processed_node_ids
        if nodes_to_delete:
            nodes_to_unlink = existing_nodes.filtered(lambda n: n.id in nodes_to_delete)
            _logger.info(f"Deleting {len(nodes_to_unlink)} nodes: {[n.name for n in nodes_to_unlink]}")
            nodes_to_unlink.unlink()
            result['nodes_deleted'] = len(nodes_to_unlink)
        
        return result

    def _sync_single_node(self, process, node_data, existing_node_dict):
        try:
            odoo_id = node_data.get('odoo_id')
            
            if odoo_id and odoo_id in existing_node_dict:
                existing_node = existing_node_dict[odoo_id]
                updates = {}
                
                if node_data['name'] != existing_node.name:
                    updates['name'] = node_data['name']
                
                if node_data.get('node_type') and node_data['node_type'] != existing_node.node_type:
                    updates['node_type'] = node_data['node_type']
                
                if node_data.get('fill_color') != existing_node.fill_color:
                    updates['fill_color'] = node_data.get('fill_color', '#ffffff')
                
                if node_data.get('stroke_color') != existing_node.stroke_color:
                    updates['stroke_color'] = node_data.get('stroke_color', '#000000')
                
                if node_data.get('font_color') != existing_node.font_color:
                    updates['font_color'] = node_data.get('font_color', '#000000')
                
                if node_data.get('font_size') != existing_node.font_size:
                    updates['font_size'] = node_data.get('font_size', 12)
                
                if node_data.get('width') != existing_node.width:
                    updates['width'] = node_data.get('width', 120)
                
                if node_data.get('height') != existing_node.height:
                    updates['height'] = node_data.get('height', 60)
                
                updates.update({
                    'position_x': node_data['position_x'],
                    'position_y': node_data['position_y'],
                    'stroke_width': node_data.get('stroke_width', 1)
                })
                
                if updates:
                    existing_node.write(updates)
                    return 'updated'
                else:
                    return 'no_changes'
            
            else:
                existing_with_same_name = self.env['alm_data_flow.process.node'].search([
                    ('process_id', '=', process.id),
                    ('name', '=', node_data['name'])
                ])
                
                if existing_with_same_name:
                    updates = {
                        'node_type': node_data.get('node_type', 'function'),
                        'position_x': node_data['position_x'],
                        'position_y': node_data['position_y'],
                        'width': node_data.get('width', 120),
                        'height': node_data.get('height', 60),
                        'fill_color': node_data.get('fill_color', '#ffffff'),
                        'stroke_color': node_data.get('stroke_color', '#000000'),
                        'stroke_width': node_data.get('stroke_width', 1),
                        'font_color': node_data.get('font_color', '#000000'),
                        'font_size': node_data.get('font_size', 12)
                    }
                    existing_with_same_name.write(updates)
                    return 'updated'
                else:
                    new_node = self.env['alm_data_flow.process.node'].create({
                        'process_id': process.id,
                        'name': node_data['name'],
                        'node_type': node_data.get('node_type', 'function'),
                        'position_x': node_data['position_x'],
                        'position_y': node_data['position_y'],
                        'width': node_data.get('width', 120),
                        'height': node_data.get('height', 60),
                        'fill_color': node_data.get('fill_color', '#ffffff'),
                        'stroke_color': node_data.get('stroke_color', '#000000'),
                        'stroke_width': node_data.get('stroke_width', 1),
                        'font_color': node_data.get('font_color', '#000000'),
                        'font_size': node_data.get('font_size', 12)
                    })
                    _logger.info(f"Created new node: {node_data['name']} (ID: {new_node.id})")
                    return 'created'
                    
        except Exception as e:
            _logger.error(f"Error syncing node {node_data.get('name')}: {e}")
            return 'error'
        
    def _parse_cell_data(self, cell):
        try:
            drawio_id = cell.get('id')
            value = cell.get('value', '')
            style = cell.get('style', '')
            odoo_id = cell.get('odoo_id')
            
            clean_value = self._clean_html_tags(value)
            
            if not clean_value or clean_value.strip() == '':
                return None
                
            node_type = self._determine_node_type(style, clean_value)
            
            geom = cell.find('mxGeometry')
            pos_x = int(float(geom.get('x', 0))) if geom is not None else 0
            pos_y = int(float(geom.get('y', 0))) if geom is not None else 0
            width = int(float(geom.get('width', 120))) if geom is not None else 120
            height = int(float(geom.get('height', 60))) if geom is not None else 60
            
            style_dict = self._parse_style(style)
            fill_color, stroke_color, font_color = self._extract_colors_from_style(style_dict)
            
            font_size = int(style_dict.get('fontSize', 12))
            
            stroke_width = int(style_dict.get('strokeWidth', 1))
            
            return {
                'drawio_id': drawio_id,
                'odoo_id': int(odoo_id) if odoo_id and odoo_id.isdigit() else None,
                'name': clean_value,
                'node_type': node_type,
                'position_x': pos_x,
                'position_y': pos_y,
                'width': width,
                'height': height,
                'fill_color': fill_color,
                'stroke_color': stroke_color,
                'stroke_width': stroke_width,
                'font_color': font_color,
                'font_size': font_size,
                'style': style,
                'original_value': value
            }
        except Exception as e:
            _logger.error(f"Error parsing cell data: {e}")
            return None
        
    def _clean_html_tags(self, text):
        if not text:
            return ""
        
        original_text = text
        
        import re
        clean_text = re.sub('<[^<]+?>', '', text)
        clean_text = clean_text.replace('&nbsp;', ' ').replace('&amp;', '&')
        clean_text = ' '.join(clean_text.split())
        
        if clean_text != original_text:
            _logger.info(f"Cleaned HTML: '{original_text}' -> '{clean_text}'")
        
        return clean_text.strip()
    
    def _determine_node_type(self, style, value):
        if not style:
            return 'function'
            
        style_lower = style.lower()
        clean_value = self._clean_html_tags(value).lower() if value else ''
        
        if 'ellipse' in style_lower:
            if 'start' in clean_value:
                return 'start'
            elif 'end' in clean_value:
                return 'end'
            return 'event'
        elif 'rhombus' in style_lower or 'diamond' in style_lower:
            return 'gateway'
        elif 'triangle' in style_lower:
            if 'up' in style_lower or 'north' in style_lower:
                return 'event'
            return 'gateway'
        elif 'hexagon' in style_lower:
            return 'loop'
        elif 'rectangle' in style_lower:
            return 'function'
        
        if any(word in clean_value for word in ['start', 'начало', 'старт']):
            return 'start'
        elif any(word in clean_value for word in ['end', 'конец', 'финиш']):
            return 'end'
        elif any(word in clean_value for word in ['gateway', 'condition', 'условие', 'шлюз']):
            return 'gateway'
        elif any(word in clean_value for word in ['loop', 'cycle', 'цикл', 'петля']):
            return 'loop'
        
        return 'function'
    
    def _validate_business_rules(self, process, root):
        warnings = []
        
        start_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id),
            ('node_type', '=', 'start')
        ])
        
        if not start_nodes:
            warnings.append("⚠️ Not Start Nodes")
        elif len(start_nodes) > 1:
            warnings.append("⚠️ Many Start Nodes")
        
        end_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id),
            ('node_type', '=', 'end')
        ])
        
        if not end_nodes:
            warnings.append("⚠️ Not End Nodes")
        
        all_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id)
        ])
        
        edges = self.env['alm_data_flow.process.edge'].search([
            ('process_id', '=', process.id)
        ])
        
        connected_nodes = set()
        for edge in edges:
            connected_nodes.add(edge.source_node_id.id)
            connected_nodes.add(edge.target_node_id.id)
        
        isolated_nodes = [node for node in all_nodes if node.id not in connected_nodes]
        if isolated_nodes:
            warnings.append(f"⚠️ Find isolated Nodes: {[n.name for n in isolated_nodes]}")
        
        gateway_nodes = self.env['alm_data_flow.process.node'].search([
            ('process_id', '=', process.id),
            ('node_type', '=', 'gateway')
        ])
        
        for gateway in gateway_nodes:
            outgoing_edges = edges.filtered(lambda e: e.source_node_id.id == gateway.id)
            if len(outgoing_edges) > 1:
                edges_without_conditions = outgoing_edges.filtered(lambda e: not e.condition_expression)
                if len(edges_without_conditions) > 1:
                    warnings.append(f"⚠️ Gateway '{gateway.name}' has several unconditional connections")
        
        for edge in edges:
            if edge.source_node_id == edge.target_node_id:
                warnings.append(f"⚠️ Cycle found: node '{edge.source_node_id.name}' refers to itself")

        nodes_without_outgoing = []
        for node in all_nodes:
            if node.node_type != 'end':
                outgoing_edges = edges.filtered(lambda e: e.source_node_id.id == node.id)
                if not outgoing_edges:
                    nodes_without_outgoing.append(node.name)

        if nodes_without_outgoing:
            warnings.append(f"⚠️ Nodes without outgoing links: {nodes_without_outgoing}")

        nodes_without_incoming = []
        for node in all_nodes:
            if node.node_type != 'start':
                incoming_edges = edges.filtered(lambda e: e.target_node_id.id == node.id)
                if not incoming_edges:
                    nodes_without_incoming.append(node.name)

        if nodes_without_incoming:
            warnings.append(f"⚠️ Nodes without incoming links: {nodes_without_incoming}")
        
        for warning in warnings:
            _logger.warning(warning)
        
        return warnings
    
    def _parse_style(self, style_string):
        style_dict = {}
        if not style_string:
            return style_dict
        
        for part in style_string.split(';'):
            if '=' in part:
                key, value = part.split('=', 1)
                style_dict[key] = value
        
        return style_dict

    def _extract_colors_from_style(self, style_dict):
        fill_color = '#ffffff'
        stroke_color = '#000000'
        font_color = '#000000'
        
        # Цвет заливки
        if 'fillColor' in style_dict:
            fill_color = style_dict['fillColor']
        elif 'swimlaneFillColor' in style_dict:
            fill_color = style_dict['swimlaneFillColor']
        
        # Цвет обводки
        if 'strokeColor' in style_dict:
            stroke_color = style_dict['strokeColor']
        
        # Цвет текста
        if 'fontColor' in style_dict:
            font_color = style_dict['fontColor']
        
        return fill_color, stroke_color, font_color

    def _get_default_colors_by_type(self, node_type):
        color_schemes = {
            'start': {'fill': '#c5e1a5', 'stroke': '#388e3c', 'font': '#000000'},  # зеленый
            'end': {'fill': '#ef9a9a', 'stroke': '#c62828', 'font': '#000000'},    # красный
            'gateway': {'fill': '#fff59d', 'stroke': '#f9a825', 'font': '#000000'}, # желтый
            'function': {'fill': '#bbdefb', 'stroke': '#1976d2', 'font': '#000000'}, # синий
            'event': {'fill': '#e1bee7', 'stroke': '#7b1fa2', 'font': '#000000'},   # фиолетовый
            'loop': {'fill': '#ffcc80', 'stroke': '#ef6c00', 'font': '#000000'}     # оранжевый
        }
        return color_schemes.get(node_type, color_schemes['function'])