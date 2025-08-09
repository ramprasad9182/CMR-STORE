# -*- coding: utf-8 -*-
{
    'name': 'NHCL POS Custom Tax',
    'summary': 'Pos Custom Tax',
    'author' : 'New Horizons CyberSoft Ltd',
    "description": """ This Module is use for Tax Computation with Multi Taxes in Point of Sale, we will help you to calculation on Product Tax. """,
    'category': 'Accounting',
    'company': 'New Horizons CyberSoft Ltd',
    'maintainer': 'New Horizons CyberSoft Ltd',
    'website': "https://www.nhclindia.com",
    'depends': ['account_tax_python', 'point_of_sale','pos_loyalty','nhcl_customizations', 'pos_restaurant',
        'stock_account','sale'],
    'version': '1.0',
    'data': [
        'security/ir.model.access.csv',
        'views/account_tax_view.xml',
        'views/sale_order_view.xml',
        'reports/sale_hrs_report_views.xml',
        'reports/report_views.xml',
        'wizard/pos_analysis_views.xml',
        'reports/pos_analysis_report_views.xml',
        'reports/pos_analysis_report_templates.xml'
    ],
    'assets': {
        'point_of_sale._assets_pos': [
            'nhcl_pos_custom_tax/static/src/override/models/*',
            'nhcl_pos_custom_tax/static/src/app/control_buttons/reward_button/*',
            'nhcl_pos_custom_tax/static/src/override/screens/receiptScreen.xml',
        ],
     },
    'images': ['static/description/background.gif'],
    'installable': True,
    'application': False,
    'auto_install': False,
    "currency": "INR",
}
