#en este archivo se declaran las vistas y las datas
# https://share.getcloudapp.com/4gulGqvN aqui estan la informacion que puedes traer

{
    'name': "Credit Management Actions",
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
        'security/ir.model.access.csv',
        'views/credit_management_view.xml',
        'views/res_partner_view.xml',
        'views/account_move_view.xml',
        'data/data.xml'
    ],
    'application': False,
    'category': "General",
    'version': '1.0.0'
}