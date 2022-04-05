#en este archivo se declaran las vistas y las datas
# https://share.getcloudapp.com/4gulGqvN aqui estan la informacion que puedes traer

{
    'name': "Credit Sales Managment MS VITAMINS",
    'description': """
        We can managment the credit Sales
    """,
    'author': "Santiago Chaparro",
    'website': "http://www.msvitamins.co",
    'depends' : [
        'contacts',
        'sale',
        'account'
    ],
    'data': [
        'security/credit_sales_managment_security.xml',
        'security/ir.model.access.csv',
        'security/group.xml',
        'report/report_payment.xml',
        'report/payment_receipt.xml',
        'views/account_move.xml',
        'views/payment_report_view.xml',
        'views/account_payment_view.xml',
        'views/account_payment_term_view.xml',
        'views/config/res_config_settings_views.xml',
        'wizard/cancel_reason_wizard_view.xml',
        'data/data.xml',
    ],
    'application': True,
    'category': "General",
    'version': '1.0.0'
}