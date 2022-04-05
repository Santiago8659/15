from odoo import _, api, fields, models


class accountPaymentTerm(models.Model):
    _inherit = 'account.payment.term'

    discount = fields.Float(
        string="Discount")