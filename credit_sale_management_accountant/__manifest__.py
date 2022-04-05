#en este archivo se declaran las vistas y las datas
# https://share.getcloudapp.com/4gulGqvN aqui estan la informacion que puedes traer

{
    'name': "Credit Sales Managment MS VITAMINS Accountant",
    'description': """
        We can managment the credit Sales
    """,
    'author': "Santiago Chaparro",
    'website': "http://www.msvitamins.co",
    'depends' : [
        'account',
        'credit_sale_management'
    ],
    'data': [
        'views/account_bank_statement_view.xml',
        'views/payment_payroll_view.xml',
    ],
    'application': True,
    'category': "General",
    'version': '1.0.0'
}