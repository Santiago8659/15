# from odoo import _, fields, api, models
# from odoo.exceptions import UserError

# from datetime import datetime

# class PaymentAccountLine(models.Model):
#     _inherit = 'payment.report'

#     def _create_account_move(self):
#         for pay in self:
#             move_id = pay.payment_id.move_id
#             credit_lines = ''
#             debit_lines = ''
#             line_ids = move_id.line_ids.account_id.ids
#             vals = pay._create_discounts_vals_from_payment_report()
#             if not pay.discount_account_id.id in line_ids:
#                 discount_account_move_line = self.env['account.move.line'].create(vals)
#             credit = pay.invoice_partner_id.property_account_receivable_id
#             for line in move_id.line_ids:
#                 if line.account_id.id == pay.invoice_partner_id.property_account_receivable_id.id:
#                     credit = pay.invoice_partner_id.property_account_receivable_id
#                     credit_lines = line.id
#                 if line.account_id.id == pay.discount_account_id.id:
#                     debit = pay.discount_account_id
#                     debit_lines = line.id
#             balanced_value = (pay.cash_discount+self.payment_id.amount)
#             move_id.write({'line_ids': [
#                         (1, debit_lines, {'debit': pay.cash_discount}),
#                         (1, credit_lines, {'credit': balanced_value}),
#                     ]})

#     def _remove_account_move(self):
#         for pay in self:
#             move_id = pay.payment_id.move_id
#             credit_lines = ''
#             debit_lines = ''
#             for line in move_id.line_ids:
#                 if line.account_id.id == pay.invoice_partner_id.property_account_receivable_id.id:
#                     credit_lines = line.id
#                 if line.account_id.id == pay.discount_account_id.id:
#                     debit_lines = line.id
#             balanced_value = (pay.cash_discount+self.payment_id.amount)
#             move_id.write({'line_ids': [
#                         (2, debit_lines, {'debit': pay.cash_discount, 'amount_currency': pay.cash_discount}),
#                         (1, credit_lines, {'credit': balanced_value, 'amount_currency': -balanced_value}),
#                     ]})