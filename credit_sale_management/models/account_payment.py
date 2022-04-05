#aqui vamos a heredar 

#1- account.payment
#2-account.statement

from odoo import _, api, fields, models


class accountPayment(models.Model):
    _inherit = 'account.payment'

    payment_receipt_id = fields.Many2one(
        comodel_name='payment.report',
        string="Payment Receipt",
        store=True, readonly=True)
    payroll_id = fields.Many2one(
        comodel_name="payroll.payment",
        string="Payroll",
        readonly=True
    )