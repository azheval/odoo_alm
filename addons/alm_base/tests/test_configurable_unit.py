# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError

class TestConfigurableUnit(TransactionCase):
    
    def setUp(self, *args, **kwargs):
        super(TestConfigurableUnit, self).setUp(*args, **kwargs)
        self.ConfigurableUnit = self.env['one_c_alm.configurable.unit']
        self.Tag = self.env['one_c_alm.configurable.unit.tag']
        self.user = self.env.ref('base.user_demo')
        self.tag = self.Tag.create({'name': 'Test Tag'})

    def test_create_configurable_unit(self):
        """Test creating a configurable unit with all fields."""
        unit_name = 'My Test Library'
        one_c_name = 'lib_MyTestLibrary'
        unit_type = 'library'
        
        unit = self.ConfigurableUnit.create({
            'name': unit_name,
            'one_c_name': one_c_name,
            'unit_type': unit_type,
            'user_ids': [(6, 0, [self.user.id])],
            'tag_ids': [(6, 0, [self.tag.id])],
        })
        
        self.assertEqual(unit.name, unit_name)
        self.assertEqual(unit.one_c_name, one_c_name)
        self.assertEqual(unit.unit_type, unit_type)
        self.assertEqual(unit.user_ids, self.user)
        self.assertEqual(unit.tag_ids, self.tag)
        self.assertTrue(unit.active)

    def test_name_is_required(self):
        """Test that the name field is required."""
        with self.assertRaises(ValidationError):
            self.ConfigurableUnit.create({
                'unit_type': 'configuration',
            })

    def test_unit_type_is_required(self):
        """Test that the unit_type field is required."""
        with self.assertRaises(ValidationError):
            self.ConfigurableUnit.create({
                'name': 'Test without type',
            })
