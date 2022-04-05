from odoo import _, api, fields, models
import re
import logging
from math import copysign
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class accountBankStatement(models.Model):
    _inherit = 'account.bank.statement'


    def button_bank_reconcile_payroll(self):
        for st_line in self.line_ids:
            if st_line.payroll_id and not st_line.is_reconciled:
                st_line.button_make_reconciliation()


class accountBankStatementline(models.Model):
    _inherit="account.bank.statement.line"

    payroll_id = fields.Many2one(comodel_name='payroll.payment', string="Payroll Payment")
    payroll_total_amount = fields.Float(related="payroll_id.total_amount", string="Payroll Total Amount")

    def _get_write_off_move_lines_dict(self, st_line, residual_balance):
        ''' Get move.lines dict (to be passed to the create()) corresponding to the reconciliation model's write-off lines.
        :param st_line:             An account.bank.statement.line record.(possibly empty, if performing manual reconciliation)
        :param residual_balance:    The residual balance of the statement line.
        :return: A list of dict representing move.lines to be created corresponding to the write-off lines.
        '''
        self.ensure_one()
        return []
        # if self.rule_type == 'invoice_matching' and (not self.match_total_amount or (self.match_total_amount_param == 100)):
        #     return []
        
        lines_vals_list = []
        
        
        for line in self.line_ids:
            currency_id = st_line.currency_id or st_line.journal_id.currency_id or self.company_id.currency_id
            if not line.account_id or currency_id.is_zero(residual_balance):
                return []

            if line.amount_type == 'percentage':
                balance = residual_balance * (line.amount / 100.0)
            elif line.amount_type == "regex":
                match = re.search(line.amount_string, st_line.payment_ref)
                if match:
                    sign = 1 if residual_balance > 0.0 else -1
                    try:
                        extracted_balance = float(re.sub(r'\D' + self.decimal_separator, '', match.group(1)).replace(self.decimal_separator, '.'))
                        balance = copysign(extracted_balance * sign, residual_balance)
                    except ValueError:
                        balance = 0
                else:
                    balance = 0
            else:
                balance = line.amount * (1 if residual_balance > 0.0 else -1)

            writeoff_line = {
                'name': f'{line.move_id.name}: {line.label}' or st_line.payment_ref,
                'balance': balance,
                'debit': balance > 0 and balance or 0,
                'credit': balance < 0 and -balance or 0,
                'account_id': line.account_id.id,
                'currency_id': False,
                'analytic_account_id': line.analytic_account_id.id,
                'analytic_tag_ids': [(6, 0, line.analytic_tag_ids.ids)],
                'reconcile_model_id': self.id,
                'journal_id': line.journal_id.id,
            }
            lines_vals_list.append(writeoff_line)

            residual_balance -= balance

            if line.tax_ids:
                writeoff_line['tax_ids'] = [(6, None, line.tax_ids.ids)]
                tax = line.tax_ids
                # Multiple taxes with force_tax_included results in wrong computation, so we
                # only allow to set the force_tax_included field if we have one tax selected
                if line.force_tax_included:
                    tax = tax[0].with_context(force_price_include=True)
                tax_vals_list = self._get_taxes_move_lines_dict(tax, writeoff_line)
                lines_vals_list += tax_vals_list
                if not line.force_tax_included:
                    for tax_line in tax_vals_list:
                        residual_balance -= tax_line['balance']

        return lines_vals_list
    
    def _prepare_reconciliation_model(self, st_line, aml_ids=[], partner=None):
        ''' Prepare the reconciliation of the statement line with some counterpart line but
        also with some auto-generated write-off lines.

        The complexity of this method comes from the fact the reconciliation will be soft meaning
        it will be done only if the reconciliation will not trigger an error.
        For example, the reconciliation will be skipped if we need to create an open balance but we
        don't have a partner to get the receivable/payable account.

        This method works in two major steps. First, simulate the reconciliation of the account.move.line.
        Then, add some write-off lines depending the rule's fields.

        :param st_line: An account.bank.statement.line record.
        :param aml_ids: The ids of some account.move.line to reconcile.
        :param partner: An optional res.partner record. If not specified, fallback on the statement line's partner.
        :return: A list of dictionary to be passed to the account.bank.statement.line's 'reconcile' method.
        '''
        self.ensure_one()
        liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()

        if st_line.to_check:
            st_line_residual = -liquidity_lines.balance
        elif suspense_lines.account_id.reconcile:
            st_line_residual = sum(suspense_lines.mapped('amount_residual'))
        else:
            st_line_residual = sum(suspense_lines.mapped('balance'))

        partner = partner or st_line.partner_id

        # has_full_write_off= any(rec_mod_line.amount == 100.0 for rec_mod_line in self.line_ids)
        has_full_write_off = True

        lines_vals_list = []
        amls = self.env['account.move.line'].browse(aml_ids)
        st_line_residual_before = st_line_residual
        aml_total_residual = 0
        for aml in amls:
            aml_total_residual += aml.amount_residual
            if aml.balance * st_line_residual > 0:
                # Meaning they have the same signs, so they can't be reconciled together
                assigned_balance = -aml.amount_residual
            elif has_full_write_off:
                assigned_balance = -aml.amount_residual
                st_line_residual -= min(-aml.amount_residual, st_line_residual, key=abs)
            else:
                assigned_balance = min(-aml.amount_residual, st_line_residual, key=abs)
                st_line_residual -= assigned_balance

            lines_vals_list.append({
                'id': aml.id,
                'balance': assigned_balance,
                'currency_id': st_line.move_id.company_id.currency_id.id,
            })


        write_off_amount = max(aml_total_residual, -st_line_residual_before, key=abs) + st_line_residual_before + st_line_residual
        reconciliation_overview, open_balance_vals = st_line._prepare_reconciliation(lines_vals_list)
        writeoff_vals_list = []
        # self._get_write_off_move_lines_dict(st_line, write_off_amount)

        for line_vals in writeoff_vals_list:
            st_line_residual -= st_line.company_currency_id.round(line_vals['balance'])

        # Check we have enough information to create an open balance.
        if open_balance_vals and not open_balance_vals.get('account_id'):
            return []

        return lines_vals_list + writeoff_vals_list


    def button_make_reconciliation(self):
        st_line = self
        liquidity_lines, suspense_lines, other_lines = st_line._seek_for_lines()
        # _logger.info("st_line_residual: %s" %st_line_residual)



        aml_ids = self.payroll_id.payment_receipt.move_id.line_ids.ids
        prepare_lines_vals_list = self._prepare_reconciliation_model(st_line, aml_ids)

        # _logger.info("prepare lines vals: %s" %prepare_lines_vals_list)
        lines_vals_list = []
        
        for line in prepare_lines_vals_list:
            if line.get('balance') < 0:
                lines_vals_list.append(line)

        # _logger.info("lines vals: %s" %lines_vals_list)
        
        reconcile = self.reconcile(lines_vals_list)
        st_line.payroll_id.write({
            'state_reconcile': 'reconciled',
            'reconciliation_date': fields.Datetime.now(),
            'bank_statement_id': st_line.statement_id.id,
            'bank_statement_line_id': st_line.id,
        })
        for pay in self.payroll_id.payment_receipt:
                pay.state_reconcile = 'reconciled'
                

    def button_undo_reconciliation(self):
        result = super(accountBankStatementline, self).button_undo_reconciliation()
        for st_line in self:
            if st_line.payroll_id:
                st_line.payroll_id.write({
                    'state_reconcile': 'to_reconcile',
                    'reconciliation_date': False,
                    'bank_statement_id': False,
                    'bank_statement_line_id': False,
                })
                for pay in st_line.payroll_id.payment_receipt:
                    pay.state_reconcile = 'to_reconcile'
        return result
        