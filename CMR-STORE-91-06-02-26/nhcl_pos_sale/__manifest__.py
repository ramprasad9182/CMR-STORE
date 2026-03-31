{
    'name': 'NHCL POS Sale',
    'Version': '17.0.1.1.0',
    'category': 'Point of Sale',
    'author': 'New Horizons CyberSoft Ltd',
    'company': 'New Horizons CyberSoft Ltd',
    'maintainer': 'New Horizons CyberSoft Ltd',
    'website': "https://www.nhclindia.com",
    'depends': ['point_of_sale','web','hr','pos_hr','stock','ultimate_pos_shortcuts','pos_discount'],
    'data': [
        'security/ir.model.access.csv',
        'views/pos_orderline_views.xml',
        'views/hr_employee_views.xml',
        'views/session_stock_check.xml',
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'nhcl_pos_sale/static/src/**/*',

            ],
    },
    'licence':'AGPL-3',
    'installable': True,
    'auto_install': False,
    'application': False,
}
