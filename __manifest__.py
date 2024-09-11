{
    'name': 'Server Management',
    'version': '17.0.1.0',
    'category': 'Tools',
    'summary': 'Manage servers within Odoo',
    'description': """
        This Odoo module allows users to manage servers,
        execute server commands via SSH, and track planned and unplanned maintenance activities.
        The module provides functionality to define servers, issue commands, and monitor server maintenance events.
    """,
    'author': 'Malik Abo Shabab',
    'depends': ['base','mail'],
    'data': [
        'security/groups.xml',
        'security/ir.model.access.csv',
        'views/server_views.xml',
        'views/service_views.xml',
        'views/command_views.xml',
        'data/cron_jobs.xml',
    ],
    'external_dependencies': {
        'python': ['paramiko'],
    },
    'installable': True,
    'application': True,
}
