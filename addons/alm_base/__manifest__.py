{
    'name': 'ALM Base',
    'version': '19.0.1.0.2',
    'summary': 'Base models for ALM application',
    'description': """
        This module provides base models and functionalities for the ALM application.
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
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'alm_theme',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/configurable_unit_tag_views.xml',
        'views/configurable_unit_version_views.xml',
        'views/configurable_unit_views.xml',
        'views/menu_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'assets': {},
}
