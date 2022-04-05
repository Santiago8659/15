from odoo import _, api, fields, models
from odoo.exceptions import UserError


class cancelReasonWizard(models.TransientModel):
    _name='cancel.reason.wizard'
    _description='Cancel Reason Wizard'

    payroll_payment_id = fields.Many2one(comodel_name='payroll.payment', string="Payroll Payment")
    comment = fields.Text(string="Comment")


    def action_cancel_reason_wizard(self):
        for pr in self.payroll_payment_id:
                pr.state = 'cancel'
                pr.cancel_reason = self.comment
                for pay in pr.payment_receipt:
                    pay.action_draft()
                    pay.action_cancel()