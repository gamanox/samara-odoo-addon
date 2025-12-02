{
    "name": "parish_intentions_eshop",
    "summary": "Capture and manage mass intentions from the Odoo eCommerce shop (Odoo 17)",
    "version": "17.0.1.0.0",
    "category": "Website",
    "author": "Parroquia",
    "license": "LGPL-3",
    "depends": ["website_sale", "sale_management"],
    'data': [
    'views/menu.xml',
    'views/parish_chapel_views.xml',
    'views/parish_chapel_schedule_views.xml',
    'views/parish_intention_views.xml',
    'security/ir.model.access.csv',
],
   
    "assets": {
        "web.assets_frontend": [
            "parish_intentions_eshop/static/src/scss/style.scss"
        ]
    },
    "installable": True,
    "application": False
}

    