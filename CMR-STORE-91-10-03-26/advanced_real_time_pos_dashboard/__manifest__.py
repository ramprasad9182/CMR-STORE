# -*- coding: utf-8 -*-
{
    "name": "Advanced Real-Time POS Dashboard",
    "summary": "Live POS dashboard with real-time sales, orders, sessions & kitchen updates",
    "description": """
Advanced Real-Time POS Dashboard
================================
• Live POS orders & sessions
• Kitchen order monitoring
• Real-time updates using Odoo bus service
• OWL-based modern dashboard UI
• Designed for Odoo 19
    """,
    "author": "Aura odoo tech",
    "website": "http://auraodoo.tech",
    "category": "Point of Sale",
    "version": "1.0",
    "license": "LGPL-3",
    "depends": ["point_of_sale","pos_restaurant","bus","web"],
    "data": [
        "security/ir.model.access.csv",
        "views/pos_dashboard_menu.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "advanced_real_time_pos_dashboard/static/src/owl/dashboard.js",
            "advanced_real_time_pos_dashboard/static/src/owl/dashboard.xml",
            "advanced_real_time_pos_dashboard/static/src/scss/dashboard.scss",
        ],
    },
    'images': ['static/description/banner.gif'],
    "installable": True,
    "auto_install": False,
    "application": True,
}
