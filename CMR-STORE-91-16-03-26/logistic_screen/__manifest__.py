{
    'name': 'Logistic Screen',
    'version': '1.0',
    'category': 'Logistics',
    "author": "New Horizons Cybersoft Ltd",
    "website": "https://www.nhclindia.com/",
    'summary': 'Logistics',
    'description': """
This module contains all the common features of Transport and Check.
    """,
    'depends': ['purchase', 'base', 'product', 'nhcl_customizations'],

    'data': [
        'data/sequence.xml',
        'security/ir.model.access.csv',
        'views/logistic_screen_entry.xml',
        'views/transports_check_view.xml',
        'views/delivery_check_view.xml',
        'views/open_parel.xml',
    ],

    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
