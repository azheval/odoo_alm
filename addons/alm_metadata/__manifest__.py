{
    'name': 'ALM Metadata',
    'version': '19.0.1.0.0',
    'summary': 'Manages metadata objects and their types',
    'description': """
        This module provides models and functionalities for the ALM metadata management.
        ---
        Developer:
        Valentin Aharonak
        E-mail: azheval@gmail.com
        Telegram: @valentin_azharonak
        GitHub: https://github.com/azheval
    """,
    'author': 'Valentin Aharonak, azheval@gmail.com',
    'website': 'https://github.com/azheval/odoo_alm',
    'category': 'ALM',
    'depends': ['alm_base'],
    'data': [
        'security/ir.model.access.csv',
        'data/metadata_object_type_data.xml',
        'views/metadata_object_type_views.xml',
        'views/metadata_object_views.xml',
        'views/metadata_object_attribute_views.xml',
        'views/metadata_configurable_unit_version_views.xml',
        'views/metadata_loader_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
