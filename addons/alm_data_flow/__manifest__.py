{
    'name': 'ALM Data Flow',
    'version': '19.0.1.0.1',
    'summary': 'Models and manages data flows and integrations within ALM.',
    'description': """
        This module provides models for defining and managing data flows,
        processes, functions, and integration mappings within the ALM system.
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
        'alm_metadata',
        'alm_diagram',
    ],
    'data': [
        'security/ir.model.access.csv',
        'views/alm_data_flow_data_flow_views.xml',
        'views/alm_data_flow_data_flow_node_views.xml',
        'views/alm_data_flow_data_flow_edge_views.xml',
        'views/alm_data_flow_process_views.xml',
        'views/alm_data_flow_process_function_views.xml',
        'views/alm_data_flow_process_node_views.xml',
        'views/alm_data_flow_process_edge_views.xml',
        'views/alm_data_flow_integration_views.xml',
        'views/alm_data_flow_field_map_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}