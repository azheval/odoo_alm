# -*- coding: utf-8 -*-

from odoo.tests.common import TransactionCase
from psycopg2 import IntegrityError

class TestConfigurableUnitVersion(TransactionCase):
    
    def setUp(self, *args, **kwargs):
        super(TestConfigurableUnitVersion, self).setUp(*args, **kwargs)
        self.ConfigurableUnit = self.env['one_c_alm.configurable.unit']
        self.Version = self.env['one_c_alm.configurable.unit.version']
        
        self.unit = self.ConfigurableUnit.create({
            'name': 'Test Unit for Versioning',
            'unit_type': 'configuration',
        })

    def test_create_version(self):
        """Test creating a version for a configurable unit."""
        version_name = '1.0.0'
        
        version = self.Version.create({
            'name': version_name,
            'unit_id': self.unit.id,
            'state': 'development',
        })
        
        self.assertEqual(version.name, version_name)
        self.assertEqual(version.unit_id, self.unit)
        self.assertEqual(version.state, 'development')
        self.assertEqual(self.unit.version_ids, version)

    def test_version_uniqueness_per_unit(self):
        """Test that version name is unique per configurable unit."""
        self.Version.create({
            'name': '1.0.0',
            'unit_id': self.unit.id,
        })
        
        with self.assertRaises(IntegrityError):
            self.Version.create({
                'name': '1.0.0',
                'unit_id': self.unit.id,
            })

    def test_version_can_be_same_for_different_units(self):
        """Test that different units can have same version name."""
        unit2 = self.ConfigurableUnit.create({
            'name': 'Another Test Unit',
            'unit_type': 'library',
        })

        version1 = self.Version.create({
            'name': '2.0.0',
            'unit_id': self.unit.id,
        })

        version2 = self.Version.create({
            'name': '2.0.0',
            'unit_id': unit2.id,
        })
        
        self.assertEqual(version1.name, version2.name)
        self.assertNotEqual(version1.unit_id, version2.unit_id)

    def test_unit_type_propagation(self):
        """Test that unit_type is correctly propagated and stored."""
        unit_config = self.ConfigurableUnit.create({
            'name': 'Config Unit',
            'unit_type': 'configuration',
        })
        version_config = self.Version.create({
            'name': '1.0.0',
            'unit_id': unit_config.id,
        })
        self.assertEqual(version_config.unit_type, 'configuration')

        unit_library = self.ConfigurableUnit.create({
            'name': 'Library Unit',
            'unit_type': 'library',
        })
        version_library = self.Version.create({
            'name': '1.0.0',
            'unit_id': unit_library.id,
        })
        self.assertEqual(version_library.unit_type, 'library')

        # Test update of unit_type (though not expected in real use, related field should reflect)
        unit_config.unit_type = 'extension'
        self.assertEqual(version_config.unit_type, 'extension')

    def test_includes_ids_creation(self):
        """Test creating a version with included versions."""
        unit_lib1 = self.ConfigurableUnit.create({'name': 'Lib1', 'unit_type': 'library'})
        version_lib1 = self.Version.create({'name': '1.0.0', 'unit_id': unit_lib1.id})

        unit_lib2 = self.ConfigurableUnit.create({'name': 'Lib2', 'unit_type': 'library'})
        version_lib2 = self.Version.create({'name': '2.0.0', 'unit_id': unit_lib2.id})

        unit_config = self.ConfigurableUnit.create({'name': 'Main Config', 'unit_type': 'configuration'})
        version_config = self.Version.create({
            'name': '3.0.0',
            'unit_id': unit_config.id,
            'includes_ids': [(6, 0, [version_lib1.id, version_lib2.id])]
        })

        self.assertEqual(len(version_config.includes_ids), 2)
        self.assertIn(version_lib1, version_config.includes_ids)
        self.assertIn(version_lib2, version_config.includes_ids)

    def test_includes_ids_add_remove(self):
        """Test adding and removing included versions."""
        unit_config = self.ConfigurableUnit.create({'name': 'Main Config', 'unit_type': 'configuration'})
        version_config = self.Version.create({'name': '1.0.0', 'unit_id': unit_config.id})

        unit_lib1 = self.ConfigurableUnit.create({'name': 'Lib1', 'unit_type': 'library'})
        version_lib1 = self.Version.create({'name': '1.0.0', 'unit_id': unit_lib1.id})

        unit_lib2 = self.ConfigurableUnit.create({'name': 'Lib2', 'unit_type': 'library'})
        version_lib2 = self.Version.create({'name': '2.0.0', 'unit_id': unit_lib2.id})

        # Add first library
        version_config.write({'includes_ids': [(4, version_lib1.id)]})
        self.assertEqual(len(version_config.includes_ids), 1)
        self.assertIn(version_lib1, version_config.includes_ids)

        # Add second library
        version_config.write({'includes_ids': [(4, version_lib2.id)]})
        self.assertEqual(len(version_config.includes_ids), 2)
        self.assertIn(version_lib1, version_config.includes_ids)
        self.assertIn(version_lib2, version_config.includes_ids)

        # Remove first library
        version_config.write({'includes_ids': [(3, version_lib1.id)]})
        self.assertEqual(len(version_config.includes_ids), 1)
        self.assertNotIn(version_lib1, version_config.includes_ids)
        self.assertIn(version_lib2, version_config.includes_ids)

    def test_includes_ids_no_self_inclusion(self):
        """Test that a version cannot include itself."""
        unit_config = self.ConfigurableUnit.create({'name': 'Main Config', 'unit_type': 'configuration'})
        version_config = self.Version.create({'name': '1.0.0', 'unit_id': unit_config.id})

        # Attempt to include itself
        with self.assertRaises(IntegrityError): # Or ValidationError, depending on Odoo's internal handling
            version_config.write({'includes_ids': [(4, version_config.id)]})
