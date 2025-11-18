{
    'name': 'ALM Theme',
    'version': '19.0.1.0.0',
    'summary': 'Custom theme for the ALM application.',
    'description': """
        This module provides a custom backend theme for the ALM application, enhancing the user interface with specific styles and branding.
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
        'web',
    ],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'alm_theme/static/src/scss/theme.scss',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
