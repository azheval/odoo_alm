{
    'name': 'ALM Test',
    'version': '19.0.1.0.0',
    'category': 'ALM',
    'summary': 'Module for managing test cases, test suites, and their execution.',
    'description': """
        This module managing test cases, test suites, and their execution.
        ---
        Developer:
        Valentin Aharonak
        E-mail: azheval@gmail.com
        Telegram: @valentin_azharonak
        GitHub: https://github.com/azheval
    """,
    'author': 'Valentin Aharonak, azheval@gmail.com',
    'website': 'https://github.com/azheval/odoo_alm',
    'license': 'LGPL-3',
    'depends': [
        'alm_base',
        'alm_data_flow',
        'alm_requirement',
        'alm_bug_tracker',
        'alm_diagram',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/test_suite_views.xml',
        'views/test_case_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
