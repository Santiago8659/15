#en este archivo se declaran las vistas y las datas
# https://share.getcloudapp.com/4gulGqvN aqui estan la informacion que puedes traer

{
    'name': "Credit Sales Managment MS VITAMINS Report",
    'description': """
        We can managment the credit Sales
    """,
    'author': "Santiago Chaparro",
    'website': "http://www.msvitamins.co",
    'depends' : [
        'credit_sale_management'
    ],
    'data': [
        'security/ir.model.access.csv',
        'security/rules.xml',
        'views/payment_report_e_view.xml',
        'views/payment_dashboard.xml'
    ],
    'application': False,
    'category': "General",
    'version': '1.0.0'
}