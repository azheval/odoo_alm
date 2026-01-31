{
    'name': 'ALM Project',
    'version': '19.0.2.0.0',
    'summary': 'Integrates ALM entities with Odoo Project and Task management',
    'description': """
        This module extends Odoo's project and task management functionalities
        to integrate with ALM configurable units and versions.
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
        'alm_base',
        'project',
    ],
    'data': [
        'views/project_task_views.xml',
        'views/project_project_views.xml',
        'views/project_menu_extension_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'alm_project/static/lib/frappe_gantt/frappe-gantt.css',
            'alm_project/static/lib/frappe_gantt/frappe-gantt.min.js',
            'alm_project/static/src/js/timeline_view.js',
            'alm_project/static/src/xml/timeline_view.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
}
