from odoo import api, fields, models, _
import base64
import zlib
import urllib.parse
import logging
import re
from lxml import etree

_logger = logging.getLogger(__name__)

class TestCase(models.Model):
    _name = 'alm.test.case'
    _description = 'Test Case'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Name', required=True, tracking=True)
    description = fields.Html(string='Description')

    test_case_number = fields.Char(
        string='Test Case Number',
        required=True,
        readonly=True,
        copy=False,
        default=lambda self: 'New'
    )

    suite_ids = fields.Many2many('alm.test.suite', string='Test Suites', tracking=True)

    state = fields.Selection([
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('archive', 'Archived'),
    ], string='State', default='draft', required=True, tracking=True)

    test_type = fields.Selection([
        ('end-to-end', 'End-to-End'),
        ('library', 'Library'),
    ], string='Test Type', default='end-to-end', required=True)

    priority = fields.Selection([
        ('0', 'Low'),
        ('1', 'Normal'),
        ('2', 'High'),
        ('3', 'Critical'),
    ], string='Priority', default='1')

    test_framework = fields.Selection([
        ('gherkin_vanessa', 'Gherkin (Vanessa)'),
        ('playwright', 'Playwright (Python)'),
        ('manual', 'Manual')
    ], string='Test Framework', default='gherkin_vanessa', required=True, tracking=True)

    responsible_user_id = fields.Many2one('res.users', string='Responsible', default=lambda self: self.env.user, tracking=True)

    tag_ids = fields.Many2many('alm.configurable.unit.tag', string='Tags')

    preconditions = fields.Html(string='Preconditions')
    postconditions = fields.Html(string='Postconditions')

    # Gherkin-specific fields
    gherkin_script = fields.Text(string='Gherkin Script')
    gherkin_script_upload = fields.Binary(string='Upload Gherkin File', help="Upload a .feature file to populate the Gherkin script content.")
    gherkin_script_filename = fields.Char(string='Source File Name', readonly=True)

    # Playwright-specific fields
    playwright_script = fields.Text(string='Playwright Script')
    playwright_script_upload = fields.Binary(string='Upload Playwright File', help="Upload a .py file to populate the Playwright script content.")
    playwright_script_filename = fields.Char(string='Playwright Script Filename', readonly=True)

    repository_path = fields.Char(string='Path in Repository', help="Manually enter the full path to the test file in the repository.")
    scenario_ids = fields.One2many('alm.test.case.scenario', 'test_case_id', string='Scenarios')


    # Relationships
    requirement_ids = fields.Many2many('alm.requirement', string='Requirements')
    bug_ids = fields.Many2many('alm.bug', string='Bugs')
    function_ids = fields.Many2many('alm.process.function', string='Functions')
    process_ids = fields.Many2many('alm.process', string='Processes')
    flow_ids = fields.Many2many('alm.data.flow', string='Flows')

    # Hierarchy
    includes_ids = fields.Many2many(
        comodel_name='alm.test.case',
        relation='alm_test_case_inclusion_rel',
        column1='parent_id',
        column2='child_id',
        string='Includes',
        domain="[('test_type', '=', 'library'), ('id', '!=', id)]"
    )
    included_in_ids = fields.Many2many(
        comodel_name='alm.test.case',
        relation='alm_test_case_inclusion_rel',
        column1='child_id',
        column2='parent_id',
        string='Included In',
        readonly=True
    )

    # Execution
    last_execution_result = fields.Selection([
        ('not_run', 'Not Run'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ], string='Last Execution Result', default='not_run', readonly=True, copy=False)
    last_execution_date = fields.Datetime(string='Last Execution Date', readonly=True, copy=False)

    # Computed field for metadata
    metadata_object_ids = fields.Many2many(
        'alm.metadata.object',
        string='Related Metadata',
        compute='_compute_related_metadata',
        store=False
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('test_case_number', 'New') == 'New':
                vals['test_case_number'] = self.env['ir.sequence'].next_by_code('alm.test.case.sequence') or 'New'
        records = super(TestCase, self).create(vals_list)
        for record in records:
            if record.gherkin_script and record.test_framework == 'gherkin_vanessa':
                record._analyze_and_build_hierarchy()
        return records

    def write(self, vals):
        res = super(TestCase, self).write(vals)
        if 'gherkin_script' in vals:
            for record in self:
                if record.test_framework == 'gherkin_vanessa':
                    record._analyze_and_build_hierarchy()
        return res

    @api.onchange('gherkin_script_upload')
    def _onchange_gherkin_script_upload(self):
        if not self.gherkin_script_upload or self.test_framework != 'gherkin_vanessa':
            return

        script_content = base64.b64decode(self.gherkin_script_upload).decode('utf-8')
        self.gherkin_script = script_content
        self.gherkin_script_upload = False

        # Gherkin-specific parsing
        if re.search(r'@ExportScenarios', script_content, re.IGNORECASE):
            self.test_type = 'library'
        functional_match = re.search(r'(?:Функционал|Feature):\s*(.*)', script_content, re.IGNORECASE)
        if functional_match:
            self.name = functional_match.group(1).strip()
        author_match = re.search(r'@author=(.*)', script_content, re.IGNORECASE)
        if author_match:
            author_str = author_match.group(1).strip()
            user = self.env['res.users'].search(['|', ('name', '=ilike', author_str), ('email', '=ilike', author_str)], limit=1)
            if user:
                self.responsible_user_id = user.id
        scenario_lines = [line.strip() for line in script_content.splitlines() if re.match(r'(?:Сценарий|Scenario):\s*', line, re.IGNORECASE)]
        scenarios_to_create = []
        for line in scenario_lines:
            parts = re.split(r'\s"(.*?)"', line)
            name = re.sub(r'(?:Сценарий|Scenario):\s*', '', parts[0], flags=re.IGNORECASE).strip()
            parameters = [p for p in parts[1:] if p.strip()]
            scenarios_to_create.append((0, 0, {'name': name, 'parameters': ' '.join(parameters)}))
        self.scenario_ids = [(5, 0, 0)] + scenarios_to_create

    def action_download_gherkin_script(self):
        self.ensure_one()
        if not self.gherkin_script:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Nothing to Download'),
                    'message': _('There is no Gherkin script content to download.'),
                    'type': 'warning',
                }
            }

        return {
            'type': 'ir.actions.act_url',
            'url': f'/alm_test/download_script/{self.id}/gherkin',
            'target': 'self',
        }

    def action_download_playwright_script(self):
        self.ensure_one()
        if not self.playwright_script:
            return {'type': 'ir.actions.act_window_close'}
        return {
            'type': 'ir.actions.act_url',
            'url': f'/alm_test/download_script/{self.id}/playwright',
            'target': 'self',
        }

    @api.onchange('playwright_script_upload')
    def _onchange_playwright_script_upload(self):
        if not self.playwright_script_upload or self.test_framework != 'playwright':
            return

        script_content = base64.b64decode(self.playwright_script_upload).decode('utf-8')
        self.playwright_script = script_content
        self.playwright_script_upload = False

    @api.depends(
        'function_ids.input_metadata_object_ids', 'function_ids.output_metadata_object_ids',
        'process_ids.input_metadata_object_ids', 'process_ids.output_metadata_object_ids',
        'flow_ids.input_metadata_object_ids', 'flow_ids.output_metadata_object_ids'
    )
    def _compute_related_metadata(self):
        for case in self:
            metadata_ids = set()
            # Collect from functions
            for func in case.function_ids:
                metadata_ids.update(func.input_metadata_object_ids.ids)
                metadata_ids.update(func.output_metadata_object_ids.ids)
            # Collect from processes
            for process in case.process_ids:
                metadata_ids.update(process.input_metadata_object_ids.ids)
                metadata_ids.update(process.output_metadata_object_ids.ids)
            # Collect from flows
            for flow in case.flow_ids:
                metadata_ids.update(flow.input_metadata_object_ids.ids)
                metadata_ids.update(flow.output_metadata_object_ids.ids)

            case.metadata_object_ids = [(6, 0, list(metadata_ids))]

    def action_activate(self):
        for record in self:
            record.state = 'active'

    def action_archive(self):
        for record in self:
            record.state = 'archive'

    def action_reset_to_draft(self):
        for record in self:
            record.state = 'draft'

    diagram_data = fields.Text(string="Hierarchy Diagram")

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
                    except (base64.binascii.Error, zlib.error, UnicodeDecodeError, etree.XMLSyntaxError):
                        # Fallback for plain XML inside diagram tag
                        try:
                            return etree.fromstring(diagram_content.encode('utf-8'))
                        except etree.XMLSyntaxError:
                             _logger.warning("Could not parse diagram content, even as plain XML.", exc_info=True)
                             return None
                return None
            else:
                return etree.fromstring(xml_data.encode('utf-8'))
        except (etree.XMLSyntaxError, Exception) as e:
            _logger.warning(f"Error parsing diagram XML: {e}", exc_info=True)
            return None

    def action_generate_hierarchy_diagram_xml(self, current_diagram_xml=None):
        self.ensure_one()
        _logger.info(f"Generating detailed hierarchy diagram for test case: {self.name}")

        # Constants
        ROW_HEIGHT = 26
        TABLE_WIDTH = 240
        ENTITY_X_GAP = 150
        ENTITY_Y_GAP = 50
        START_X, START_Y = 50, 50

        # 1. Gather all cases and prepare color mapping
        all_cases_to_draw = self._get_all_related_cases()
        path_colors = self._get_path_colors(all_cases_to_draw)

        # 2. Parse existing positions
        existing_positions = self._parse_existing_positions(current_diagram_xml)

        # 3. Build XML structure
        root = etree.Element("mxGraphModel")
        root_cell = etree.SubElement(root, "root")
        etree.SubElement(root_cell, "mxCell", id="0")
        etree.SubElement(root_cell, "mxCell", id="1", parent="0")

        # 4. Create Nodes (tables and rows)
        cell_id_counter = 2
        case_cell_map = {}
        scenario_cell_map = {}

        current_x, current_y = START_X, START_Y
        for case in all_cases_to_draw:
            pos = existing_positions.get(case.id, {'x': str(current_x), 'y': str(current_y)})
            case_cell_id = str(cell_id_counter); cell_id_counter += 1
            case_cell_map[case.id] = case_cell_id

            if case.test_framework == 'gherkin_vanessa':
                case_height = ROW_HEIGHT * (len(case.scenario_ids) + 1)
            else:
                case_height = ROW_HEIGHT * 3

            style = self._get_case_style(case)
            node_value = f"({case.test_case_number or 'N/A'}) - {case.name}"

            case_cell = etree.SubElement(root_cell, "mxCell", id=case_cell_id, value=node_value, style=style, parent="1", vertex="1", odoo_id=str(case.id))
            etree.SubElement(case_cell, "mxGeometry", x=pos['x'], y=pos['y'], width=str(TABLE_WIDTH), height=str(case_height), **{'as': "geometry"})

            if case.test_framework == 'gherkin_vanessa':
                attr_y_offset = ROW_HEIGHT
                for scenario in case.scenario_ids:
                    scenario_cell_id = str(cell_id_counter); cell_id_counter += 1
                    scenario_cell_map[scenario.id] = scenario_cell_id
                    attr_style = "shape=partialRectangle;collapsible=0;dropTarget=0;pointerEvents=0;fillColor=none;top=0;left=0;bottom=0;right=0;align=left;spacingLeft=6;"
                    attr_cell = etree.SubElement(root_cell, "mxCell", id=scenario_cell_id, value=scenario.name, style=attr_style, parent=case_cell_id, vertex="1", odoo_id=str(scenario.id))
                    etree.SubElement(attr_cell, "mxGeometry", y=str(attr_y_offset), width=str(TABLE_WIDTH), height=str(ROW_HEIGHT), **{'as': "geometry"})
                    attr_y_offset += ROW_HEIGHT

            if case.id not in existing_positions:
                current_y += case_height + ENTITY_Y_GAP
                if current_y > 800:
                    current_y = START_Y
                    current_x += TABLE_WIDTH + ENTITY_X_GAP

        # 5. Create Edges
        drawn_gherkin_edges = set()
        for calling_case in all_cases_to_draw:
            # Automated edges for Gherkin
            if calling_case.test_framework == 'gherkin_vanessa' and calling_case.gherkin_script:
                step_pattern = re.compile(r'^\s*(?:И|Дано|Когда|Тогда|And|Given|When|Then)\s+(.*)', re.IGNORECASE)
                for line in calling_case.gherkin_script.splitlines():
                    match = step_pattern.match(line.strip())
                    if not match: continue
                    full_step_text = match.group(1).strip()
                    parts = re.split(r'["«»](.*?)["«»]', full_step_text)
                    potential_scenario_name = parts[0].strip()
                    if not potential_scenario_name: continue

                    called_scenarios = self.env['alm.test.case.scenario'].search([
                        ('name', '=', potential_scenario_name),
                        ('test_case_id', 'in', all_cases_to_draw.ids),
                        ('test_case_id.test_type', '=', 'library'),
                        ('test_case_id', '!=', calling_case.id)
                    ])
                    for called_scenario in called_scenarios:
                        source_cell_id = scenario_cell_map.get(called_scenario.id)
                        target_cell_id = case_cell_map.get(calling_case.id)
                        if source_cell_id and target_cell_id:
                            path_key = f"{calling_case.id}-{called_scenario.test_case_id.id}"
                            color = path_colors.get(path_key, '#666666')
                            edge_style = f"edgeStyle=entityRelationEdgeStyle;endArrow=classic;html=1;strokeColor={color};"
                            edge_attrib = {'id': str(cell_id_counter), 'style': edge_style, 'parent': "1", 'source': source_cell_id, 'target': target_cell_id, 'edge': "1"}
                            edge_cell = etree.SubElement(root_cell, "mxCell", **edge_attrib)
                            etree.SubElement(edge_cell, "mxGeometry", relative="1", **{'as': "geometry"})
                            cell_id_counter += 1
                            drawn_gherkin_edges.add(path_key)

            # Manual edges for all frameworks
            for included_case in calling_case.includes_ids:
                if included_case in all_cases_to_draw:
                    source_cell_id = case_cell_map.get(included_case.id)
                    target_cell_id = case_cell_map.get(calling_case.id)
                    if source_cell_id and target_cell_id:
                        path_key = f"{calling_case.id}-{included_case.id}"
                        # Avoid drawing a duplicate dashed edge if a solid Gherkin edge was already created
                        if path_key in drawn_gherkin_edges:
                            continue

                        color = '#ADADAD' # Grey for manual links
                        edge_style = f"edgeStyle=entityRelationEdgeStyle;endArrow=classic;html=1;strokeColor={color};"
                        edge_attrib = {'id': str(cell_id_counter), 'style': edge_style, 'parent': "1", 'source': source_cell_id, 'target': target_cell_id, 'edge': "1"}
                        edge_cell = etree.SubElement(root_cell, "mxCell", **edge_attrib)
                        etree.SubElement(edge_cell, "mxGeometry", relative="1", **{'as': "geometry"})
                        cell_id_counter += 1


        return etree.tostring(root, pretty_print=True, encoding='unicode')

    def action_update_from_diagram_xml(self, xml_data):
        self.ensure_one()
        if not xml_data:
            return {'warning': 'No XML data received.'}

        xml_root = self._extract_diagram_root(xml_data)
        if xml_root is None:
            return {'warning': 'Could not parse diagram XML.'}

        self.write({'diagram_data': xml_data})

        diagram_includes = set()

        # Create maps for odoo_id to cell_id and cell_id to odoo_id
        cell_to_odoo_id = {cell.get('id'): cell.get('odoo_id') for cell in xml_root.xpath("//mxCell[@vertex='1' and @odoo_id]")}

        # Create map from scenario odoo_id to its parent test_case odoo_id
        scenario_to_case_map = {}
        for scenario_cell in xml_root.xpath("//mxCell[@vertex='1' and @odoo_id and contains(@style, 'shape=partialRectangle')]"):
            scenario_odoo_id = scenario_cell.get('odoo_id')
            parent_cell_id = scenario_cell.get('parent')
            if scenario_odoo_id and parent_cell_id in cell_to_odoo_id:
                case_odoo_id = cell_to_odoo_id[parent_cell_id]
                scenario_to_case_map[int(scenario_odoo_id)] = int(case_odoo_id)

        for edge in xml_root.xpath("//mxCell[@edge='1']"):
            source_cell_id = edge.get('source')
            target_cell_id = edge.get('target')

            calling_case_id = cell_to_odoo_id.get(source_cell_id)
            called_scenario_id = cell_to_odoo_id.get(target_cell_id)

            if calling_case_id and called_scenario_id and int(calling_case_id) == self.id:
                called_case_id = scenario_to_case_map.get(int(called_scenario_id))
                if called_case_id:
                    diagram_includes.add(called_case_id)

        current_includes = set(self.includes_ids.ids)
        to_add = diagram_includes - current_includes
        to_remove = current_includes - diagram_includes

        commands = []
        if to_add:
            commands.extend([(4, rec_id) for rec_id in to_add])
        if to_remove:
            commands.extend([(3, rec_id) for rec_id in to_remove])

        if commands:
            self.write({'includes_ids': commands})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _("Update Complete"),
                'message': f"Hierarchy updated. Added: {len(to_add)}, Removed: {len(to_remove)}.",
                'type': 'success',
            }
        }

    def _get_all_related_cases(self):
        """Traverse includes_ids and included_in_ids to get all related cases."""
        all_cases = self.env['alm.test.case']
        q = [self]
        visited = set()
        while q:
            current = q.pop(0)
            if current.id in visited:
                continue
            visited.add(current.id)
            all_cases |= current
            q.extend(current.includes_ids)
            q.extend(current.included_in_ids)
        return all_cases

    def _get_path_colors(self, all_cases):
        """Assign a consistent color to each unique call path."""
        import random

        path_keys = set()
        for case in all_cases:
            for included in case.includes_ids:
                path_keys.add(f"{case.id}-{included.id}")

        predefined_colors = [
            '#e6194B', '#3cb44b', '#ffe119', '#4363d8', '#f58231',
            '#911eb4', '#42d4f4', '#f032e6', '#bfef45', '#fabed4',
            '#469990', '#dcbeff', '#9A6324', '#fffac8', '#800000',
            '#aaffc3', '#808000', '#ffd8b1', '#000075', '#a9a9a9'
        ]
        random.shuffle(predefined_colors)

        path_colors = {}
        for key in sorted(list(path_keys)):
            if predefined_colors:
                path_colors[key] = predefined_colors.pop(0)
            else:
                path_colors[key] = '#' + ''.join(random.choice('0123456789ABCDEF') for j in range(6))
        return path_colors

    def _parse_existing_positions(self, xml_data):
        """Parse XML to get existing node positions."""
        positions = {}
        if not xml_data:
            return positions
        xml_root = self._extract_diagram_root(xml_data)
        if xml_root is not None:
            # Find all vertexes that are direct children of layer '1' and have an odoo_id
            for cell in xml_root.xpath("//mxCell[@vertex='1' and @odoo_id and @parent='1']"):
                odoo_id = cell.get('odoo_id')
                geom = cell.find('mxGeometry')
                if odoo_id and geom is not None:
                    positions[int(odoo_id)] = {'x': geom.get('x'), 'y': geom.get('y')}
        return positions

    def _get_case_style(self, case):
        """Get the style for a test case cell."""
        # Base styles
        if case.test_framework == 'gherkin_vanessa':
            style = "shape=table;startSize=26;container=1;collapsible=1;childLayout=tableLayout;fixedRows=1;rowLines=0;fontStyle=1;align=center;resizeLast=1;whiteSpace=wrap;"
        else:
            style = "shape=rectangle;whiteSpace=wrap;align=center;fontStyle=1;verticalAlign=middle;"

        # Base colors for test_type
        type_colors = {
            'library': '#FFF9C4',  # Light Yellow
            'end-to-end': '#E3F2FD', # Light Blue
        }
        # Framework specific colors
        framework_colors = {
            'gherkin_vanessa': '#D5E8D4', # Greenish
            'playwright': '#DAE8FC', # Bluish
            'manual': '#FFCCCC', # Pinkish for manual
        }

        # Prioritize framework color if available, otherwise use type color
        color = framework_colors.get(case.test_framework, type_colors.get(case.test_type, '#FFFFFF'))

        style += f"fillColor={color};"

        if case.id == self.id:  # Highlight current record
            style += "strokeColor=#000000;strokeWidth=3;" # Make highlight thicker

        return style

    def _analyze_and_build_hierarchy(self):
        """
        Analyzes the Gherkin script to find included scenarios from other
        library test cases and updates the 'includes_ids' field.
        THIS METHOD IS ONLY FOR GHERKIN TESTS.
        """
        self.ensure_one()
        if self.test_framework != 'gherkin_vanessa' or not self.gherkin_script:
            return

        step_pattern = re.compile(
            r'^\s*(?:И|Дано|Когда|Тогда|And|Given|When|Then)\s+(.*)',
            re.IGNORECASE
        )

        included_cases_to_add = self.env['alm.test.case']

        for line in self.gherkin_script.splitlines():
            match = step_pattern.match(line.strip())
            if not match:
                continue

            full_step_text = match.group(1).strip()

            parts = re.split(r'["«»](.*?)["«»]', full_step_text)
            potential_scenario_name = parts[0].strip()

            if not potential_scenario_name:
                continue

            scenarios = self.env['alm.test.case.scenario'].search([
                ('name', '=', potential_scenario_name),
                ('test_case_id.test_type', '=', 'library'),
                ('test_case_id', '!=', self.id if self.id else False)
            ])

            for scenario in scenarios:
                included_cases_to_add |= scenario.test_case_id

        if included_cases_to_add:
            new_ids = [(4, case.id) for case in included_cases_to_add if case not in self.includes_ids]
            if new_ids:
                self.write({'includes_ids': new_ids})


    def action_analyze_hierarchy(self):
        """
        Button action to trigger the hierarchy analysis for selected test cases.
        """
        for case in self:
            case._analyze_and_build_hierarchy()
        return True
