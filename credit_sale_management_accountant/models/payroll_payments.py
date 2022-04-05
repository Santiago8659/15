from odoo import _, fields, api, models

class PayrollPayment(models.Model):
    _inherit = 'payroll.payment'

    reconciliation_date = fields.Datetime(string="Reconciliation Date", readonly=True, tracking=True)

    state_reconcile = fields.Selection([
        ('to_reconcile','To reconcile'),
        ('reconciled','reconciled')
    ], string='Reconciliation Status', default='to_reconcile', readonly=True)

    bank_statement_line_id = fields.Many2one(comodel_name="account.bank.statement.line", string="Bank Statement Line", groups="account.group_account_user")
    bank_statement_id = fields.Many2one(comodel_name="account.bank.statement", string="Bank Statement", groups="account.group_account_user")

    def action_view_bank_statement_view(self):
        action = self.env["ir.actions.actions"]._for_xml_id("account.action_bank_statement_tree")
        bank_statement_id = self.bank_statement_id
        form_view = [(self.env.ref('account.view_bank_statement_form').id, 'form')]
        if 'views' in action:
            action['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
        else:
            action['views'] = form_view
        action['res_id'] = bank_statement_id.id
        return action