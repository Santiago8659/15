#en este archivo se declaran las vistas y las datas
# https://share.getcloudapp.com/4gulGqvN aqui estan la informacion que puedes traer

{
    'name': "Credit Sales Management Commission MS VITAMINS",
    'description': """
        We can affect the sales commission from payment
    """,
    'author': "Santiago Chaparro",
    'website': "http://www.msvitamins.co",
    'depends' : [
        'contacts',
        'sale',
        'account'
    ],
    'data': [
        'views/payment_view.xml'
    ],
    'application': True,
    'category': "General",
    'version': '1.0.0'
}