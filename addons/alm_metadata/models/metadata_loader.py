from odoo import models, fields, api, _
import logging
import base64
import xml.etree.ElementTree as ET
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class MetadataLoader(models.TransientModel):
    _name = 'metadata.loader.wizard'
    _description = 'Metadata Loader Wizard'

    unit_id = fields.Many2one(
        'alm.configurable.unit', 
        string='Configurable Unit', 
        required=True
    )
    version_id = fields.Many2one(
        'alm.configurable.unit.version', 
        string='Version', 
        required=True,
        domain="[('unit_id', '=', unit_id)]"
    )
    data_file = fields.Binary(string='Data File', required=True)
    file_name = fields.Char(string='File Name')
    
    @api.onchange('unit_id')
    def _onchange_unit_id(self):
        if self.unit_id and self.version_id.unit_id != self.unit_id:
            self.version_id = False

    def action_load_metadata(self):
        if not self.data_file:
            raise UserError(_("Please select a file to upload."))
        
        try:
            file_content = base64.b64decode(self.data_file).decode('utf-8')
            
            metadata_objects = self._parse_xml_metadata(file_content)
            
            result = self._process_metadata_data(metadata_objects)
            
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Metadata Load Complete'),
                    'message': _('Successfully processed %s objects. Created: %s, Skipped: %s') % (
                        result['total'], result['created'], result['skipped']
                    ),
                    'sticky': False,
                }
            }
            
        except Exception as e:
            _logger.error("Error loading metadata: %s", str(e))
            raise UserError(_("Error loading metadata: %s") % str(e))

    def _parse_xml_metadata(self, xml_content):
        objects = []
        
        try:
            namespaces = {
                'md': 'http://v8.1c.ru/8.3/MDClasses',
                'v8': 'http://v8.1c.ru/8.1/data/core',
                'xr': 'http://v8.1c.ru/8.3/xcf/readable'
            }
            
            root = ET.fromstring(xml_content)
            
            configuration = root.find('.//md:Configuration', namespaces)
            if configuration is None:
                raise UserError(_("Invalid XML format: Configuration element not found"))
            
            child_objects = configuration.find('.//md:ChildObjects', namespaces)
            if child_objects is None:
                raise UserError(_("No ChildObjects found in XML"))
            
            for child in child_objects:
                tag_name = child.tag.split('}')[-1]
                object_name = child.text
                
                if object_name:
                    type_mapping = {
                        'Catalog': 'Catalog',
                        'Document': 'Document', 
                        'Report': 'Report',
                        'DataProcessor': 'DataProcessor',
                        'ExchangePlan': 'ExchangePlan',
                        'ChartOfCharacteristicTypes': 'ChartOfCharacteristicTypes',
                        'ChartOfAccounts': 'ChartOfAccounts',
                        'ChartOfCalculationTypes': 'ChartOfCalculationTypes',
                        'InformationRegister': 'InformationRegister',
                        'AccumulationRegister': 'AccumulationRegister',
                        'AccountingRegister': 'AccountingRegister',
                        'CalculationRegister': 'CalculationRegister',
                        'BusinessProcess': 'BusinessProcess',
                        'Task': 'Task',
                        'CommonModule': 'CommonModule',
                        'Role': 'Role',
                        'Subsystem': 'Subsystem',
                        'Constant': 'Constant',
                        'Enum': 'Enumeration',
                        'XDTOPackage': 'XDTO_Package'
                    }
                    
                    technical_type = type_mapping.get(tag_name)
                    if technical_type:
                        objects.append({
                            'technical_name': object_name,
                            'name': object_name,
                            'type_technical_name': technical_type,
                            'type_name': self._get_type_display_name(technical_type)
                        })
            
            return objects
            
        except ET.ParseError as e:
            raise UserError(_("XML parsing error: %s") % str(e))

    def _get_type_display_name(self, technical_type):
        type_names = {
            'Catalog': 'Справочник',
            'Document': 'Документ',
            'Report': 'Отчет', 
            'DataProcessor': 'Обработка',
            'ExchangePlan': 'План обмена',
            'ChartOfCharacteristicTypes': 'План видов характеристик',
            'ChartOfAccounts': 'План счетов',
            'ChartOfCalculationTypes': 'План видов расчета',
            'InformationRegister': 'Регистр сведений',
            'AccumulationRegister': 'Регистр накопления',
            'AccountingRegister': 'Регистр бухгалтерии',
            'CalculationRegister': 'Регистр расчета',
            'BusinessProcess': 'Бизнес-процесс',
            'Task': 'Задача',
            'CommonModule': 'Общий модуль',
            'Role': 'Роль',
            'Subsystem': 'Подсистема',
            'Constant': 'Константа',
            'Enumeration': 'Перечисление',
            'XDTO_Package': 'XDTO-пакет'
        }
        return type_names.get(technical_type, technical_type)

    def _process_metadata_data(self, metadata_objects):
        result = {
            'total': 0,
            'created': 0,
            'skipped': 0
        }
        
        for item in metadata_objects:
            result['total'] += 1
            
            type_obj = self._get_or_create_type(
                item['type_technical_name'],
                item['type_name']
            )
            if not type_obj:
                result['skipped'] += 1
                continue
                
            existing_obj = self.env['alm.metadata.object'].search([
                ('technical_name', '=', item['technical_name']),
                ('version_id', '=', self.version_id.id)
            ], limit=1)
            
            if existing_obj:
                result['skipped'] += 1
                continue
            
            self.env['alm.metadata.object'].create({
                'name': item['name'],
                'technical_name': item['technical_name'],
                'type_id': type_obj.id,
                'version_id': self.version_id.id,
            })
            result['created'] += 1
            
        return result

    def _get_or_create_type(self, technical_name, display_name):
        if not technical_name:
            return False
            
        type_obj = self.env['alm.metadata.object.type'].search([
            ('technical_name', '=', technical_name)
        ], limit=1)
        
        if type_obj:
            return type_obj
            
        return self.env['alm.metadata.object.type'].create({
            'name': display_name,
            'technical_name': technical_name
        })
