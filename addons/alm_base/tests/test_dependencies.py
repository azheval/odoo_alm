# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestConfigurableUnitDependencies(TransactionCase):
    
    def setUp(self):
        super(TestConfigurableUnitDependencies, self).setUp()
        
        # Создаем тестовые конфигурационные единицы
        self.unit_trade = self.env['one_c_alm.configurable.unit'].create({
            'name': 'Trade',
            'unit_type': 'configuration',
        })
        
        self.unit_bsp = self.env['one_c_alm.configurable.unit'].create({
            'name': 'BSP', 
            'unit_type': 'library',
        })
        
        self.unit_warehouse = self.env['one_c_alm.configurable.unit'].create({
            'name': 'Warehouse',
            'unit_type': 'extension', 
        })

    def test_01_add_first_dependency(self):
        """Тест: добавление первой зависимости"""
        # Создаем версии
        trade_version = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '11.5.4.112',
            'unit_id': self.unit_trade.id,
        })
        
        bsp_version = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '1.1.1.1',
            'unit_id': self.unit_bsp.id,
        })
        
        # Добавляем зависимость - должно работать без ошибок
        trade_version.includes_ids = [(4, bsp_version.id)]
        
        # Проверяем что зависимость добавилась
        self.assertEqual(trade_version.includes_ids, bsp_version)
        self.assertEqual(bsp_version.included_in_ids, trade_version)

    def test_02_add_compatible_versions_same_unit(self):
        """Тест: добавление совместимых версий одной единицы"""
        trade_version = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '11.5.4.112',
            'unit_id': self.unit_trade.id,
        })
        
        bsp_version_1 = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '1.1.1.1',
            'unit_id': self.unit_bsp.id,
        })
        
        bsp_version_2 = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '1.1.1.2',  # Совместима с 1.1.1.1
            'unit_id': self.unit_bsp.id,
        })
        
        # Добавляем первую зависимость
        trade_version.includes_ids = [(4, bsp_version_1.id)]
        
        # Добавляем вторую совместимую зависимость - должно работать
        trade_version.includes_ids = [(4, bsp_version_2.id)]
        
        # Проверяем что обе зависимости добавились
        self.assertEqual(len(trade_version.includes_ids), 2)

    def test_03_add_incompatible_versions_same_unit(self):
        """Тест: добавление несовместимых версий одной единицы"""
        trade_version = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '11.5.4.112',
            'unit_id': self.unit_trade.id,
        })
        
        bsp_version_1 = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '1.1.1.1',
            'unit_id': self.unit_bsp.id,
        })
        
        bsp_version_2 = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '1.2.0.1',  # Несовместима с 1.1.1.1
            'unit_id': self.unit_bsp.id,
        })
        
        # Добавляем первую зависимость
        trade_version.includes_ids = [(4, bsp_version_1.id)]
        
        # Пытаемся добавить вторую несовместимую зависимость - должна быть ошибка
        with self.assertRaises(ValidationError):
            trade_version.includes_ids = [(4, bsp_version_2.id)]

    def test_04_version_parsing(self):
        """Тест: парсинг версий"""
        version_model = self.env['one_c_alm.configurable.unit.version']
        
        # Тестируем разные форматы версий
        test_cases = [
            ('1', [1, 0, 0, 0]),
            ('1.2', [1, 2, 0, 0]),
            ('1.2.3', [1, 2, 3, 0]),
            ('1.2.3.456', [1, 2, 3, 456]),
        ]
        
        for version_str, expected in test_cases:
            result = version_model._parse_version(version_str)
            self.assertEqual(result, expected, f"Failed for version: {version_str}")

    def test_05_version_compatibility(self):
        """Тест: проверка совместимости версий"""
        version_model = self.env['one_c_alm.configurable.unit.version']
        
        # Совместимые версии (первые 3 компонента одинаковы)
        compatible_cases = [
            ('1.1.1.1', '1.1.1.2'),
            ('1.2.3.100', '1.2.3.200'),
            ('1.0.0.1', '1.0.0.999'),
        ]
        
        for v1, v2 in compatible_cases:
            self.assertTrue(version_model._check_version_compatibility(v1, v2),
                          f"Should be compatible: {v1} vs {v2}")
        
        # Несовместимые версии (первые 3 компонента разные)
        incompatible_cases = [
            ('1.1.1.1', '1.1.2.1'),
            ('1.2.3.100', '1.2.4.100'),
            ('1.0.0.1', '2.0.0.1'),
        ]
        
        for v1, v2 in incompatible_cases:
            self.assertFalse(version_model._check_version_compatibility(v1, v2),
                           f"Should be incompatible: {v1} vs {v2}")

    def test_06_no_self_reference(self):
        """Тест: нельзя добавить зависимость на саму себя"""
        trade_version = self.env['one_c_alm.configurable.unit.version'].create({
            'name': '11.5.4.112',
            'unit_id': self.unit_trade.id,
        })
        
        # Пытаемся добавить зависимость на саму себя - должна быть ошибка
        with self.assertRaises(ValidationError):
            trade_version.includes_ids = [(4, trade_version.id)]
