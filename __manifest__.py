# -*- coding: utf-8 -*-
{
    'name': "Boton descuento en factura",

    'summary': """
       Boton para aplicar descuento en factura
        """,

    'description': """
        Este módulo añade un botón en las facturas que permite aplicar un descuento
        directamente sobre el total de la factura. El descuento se puede aplicar
        de forma manual o automática, y se refleja en el total de la factura.
    """,

    'author': "GonzaOdoo",
    'website': "http://www.yourcompany.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/master/odoo/addons/base/module/module_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '1.0',

    # any module necessary for this one to work correctly
    'depends': ['account','delivery'],

    # always loaded
    "data": ["security/ir.model.access.csv",
             "views/discount.xml",
             "views/delivery_carrier.xml",
            ],
}
