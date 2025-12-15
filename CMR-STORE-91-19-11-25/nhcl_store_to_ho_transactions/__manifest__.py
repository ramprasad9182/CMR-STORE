{
    "name": "Store to HO Transactions",
    "category": "Extra Tools",
    "version": "17.0",
    "author": "New Horizons Cybersoft Ltd",
    "website": "https://www.nhclindia.com/",
    "description": """Ho to Store CMR Integration""",
    "depends": ['base', 'base_setup','account','nhcl_customizations'],
    "data": [
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'views/store_eod_transaction_job_view.xml',
        'views/store_job_log_view.xml',
        'views/purchase_request_view.xml'

    ],
    "demo": [],
    "application": False,
    "installable": True,
    "auto-intall": False
}
