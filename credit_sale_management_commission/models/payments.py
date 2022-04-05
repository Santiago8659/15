from odoo import _, fields, api, models
from odoo.exceptions import UserError

from datetime import datetime

class PaymentReport(models.Model):
    _inherit = 'payment.report'

    not_commission = fields.Boolean(string="Not Commission", default=False)

    @api.onchange('not_commission')
    def oncange_not_comission(self):
        print('im working')
        self.invoice_id.not_commission = self.not_commission

class PayrollPayment(models.Model):
    _inherit = 'payroll.payment'

    not_commission = fields.Boolean(string="Not Commission", default=False)

    @api.onchange('not_commission')
    def oncange_not_comission(self):
        for pay in self.payment_receipt:
            pay.not_commission, pay.invoice_id.not_commission  = self.not_commission, self.not_commission 
