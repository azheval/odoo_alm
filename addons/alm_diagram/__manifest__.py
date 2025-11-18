{
    'name': 'ALM Diagramming',
    'version': '19.0.1.0.0',
    'summary': 'Provides diagramming capabilities for ALM models using embedded Draw.io.',
    'description': """
        This module integrates an embedded Draw.io editor into Odoo forms
        to allow visual modeling of processes and data flows.
        It supports both generating diagrams from existing data and
        updating data based on user-drawn diagrams.
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
    'data': [
        'data/config_data.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'alm_diagram/static/src/js/process_diagram_widget.js',
            'alm_diagram/static/src/xml/process_diagram_widget.xml',
            'alm_diagram/static/src/scss/process_diagram_widget.scss',
            'alm_diagram/static/src/js/data_flow_diagram_widget.js',
            'alm_diagram/static/src/xml/data_flow_diagram_widget.xml',
            'alm_diagram/static/src/js/field_mapping_diagram_widget.js',
            'alm_diagram/static/src/xml/field_mapping_diagram_widget.xml',
        ],
    },
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
