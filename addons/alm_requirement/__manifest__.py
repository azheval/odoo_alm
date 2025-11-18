{
    'name': 'ALM Requirement',
    'version': '19.0.1.0.0',
    'summary': 'Module for managing application requirements.',
        'description': """
        Module managing application requirements for the ALM application.
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
        'alm_base',
        'project',
        'alm_project',
        'alm_metadata',
        'alm_data_flow',
        'alm_bug_tracker',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_sequence_data.xml',
        'views/requirement_category_views.xml',
        'views/requirement_requirement_views.xml',
        'views/project_task_views.xml',
        'views/metadata_object_views.xml',
        'views/alm_process_views.xml',
        'views/alm_process_function_views.xml',
        'views/bug_views.xml',
        'views/alm_data_flow_views.xml',
        'views/alm_data_flow_integration_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
}
