{
    'name': 'ALM Bug Tracker',
    'version': '19.0.1.0.1',
    'summary': 'A bug tracking system for ALM',
    'description': """
        A bug tracking system for the ALM application.
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
    'depends': [
        'alm_base',
        'alm_metadata',
        'alm_project',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/sequences.xml',
        'views/bug_views.xml',
        'views/bug_project_task_views.xml',
        'views/menu_views.xml',
        'wizards/bug_report_wizard_views.xml',
        'views/bug_report_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
