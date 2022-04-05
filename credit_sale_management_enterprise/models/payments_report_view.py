from odoo import tools
from odoo import _, fields, api, models

class PaymentReportView(models.Model):
    _name = 'payment.report.view'
    _description = "Payment Report View"
    _auto = False

    _order = "create_date desc"

    name = fields.Char(string='Payroll Reference', readonly=True)
    date = fields.Datetime(string='Create Date', readonly=True)
    


    payment_date = fields.Datetime(string='Payment Date', readonly=True)
    payment_report_id = fields.Many2one('payment.report', string="Payment Report", readonly=True)
    partner_id = fields.Many2one('res.partner', string="Customer", readonly=True)
    invoice_id = fields.Many2one('account.move', string="Invoice", readonly=True)
    company_id = fields.Many2one('res.company', string='Company', readonly=True)
    user_id = fields.Many2one('res.users', 'Salesperson', readonly=True)
    team_id = fields.Many2one('crm.team', 'Sales Team', readonly=True)
    move_id = fields.Many2one('account.move', string="Account Move", readonly=True)
    country_id = fields.Many2one('res.country', string="Country", readonly=True)
    total_amount = fields.Float(string='Total Amount', readonly=True)
    total_invoiced = fields.Float(string="Total Invoiced", readonly=True)
    total_untaxed_invoiced = fields.Float(string="Total Untaxed Invoiced", readonly=True)
    financial_discount = fields.Float(string="Cash Discount", readonly=True)
    salesperson_cost = fields.Float(string="Salesperson Cost", readonly=True)
    nbr = fields.Integer('# of Pay', readonly=True)
    canceled = fields.Integer(string="Canceled", readonly=True, help="Qty of payrolls Canceled by errors")
    state = fields.Selection([
            ('draft','Draft'),
            ('submit','Submit'),
            ('post','Post'),
            ('done','Done'),
            ('cancel','Cancel')
        ],
        string='State', readonly=True
    )

    def _select(self, fields=None):
        if not fields:
            fields = {}
        select_ = """
            coalesce(min(pay.id), -pr.id) AS id,
			pr.name AS name,
			pay.id AS payment_report_id,
			pay.invoice_partner_id as partner_id,
			pay.invoice_id as invoice_id,
			pr.company_id AS company_id,
			pr.user_id AS user_id,
            pr.team_id AS team_id,
			pr.state AS state,
			pr.create_date AS date,
            pay.payment_date AS payment_date,
			payment.move_id AS move_id,
			partner.country_id as country_id,
			count(*) as nbr,
            count(case pr.state when 'cancel' then 1 else null end) as canceled,
            CASE WHEN pay.invoice_id IS NOT NULL THEN sum(pay.amount) ELSE 0 END AS total_amount,
			CASE WHEN pay.invoice_id IS NOT NULL THEN sum(pay.invoice_amount_total) ELSE 0 END AS total_invoiced,
			CASE WHEN pay.invoice_id IS NOT NULL THEN sum(pay.invoice_amount_untaxed) ELSE 0 END AS total_untaxed_invoiced,
			CASE WHEN pay.invoice_id IS NOT NULL THEN sum(pay.cash_discount) ELSE 0 END AS financial_discount,
			CASE WHEN pay.invoice_id IS NOT NULL THEN sum(pay.salesperson_cost) ELSE 0 END AS salesperson_cost
        """    
        for field in fields.values():
            select_ += field
        return select_

    def _from(self, from_clause=''):
        from_ = """
            payment_report AS pay
                right OUTER JOIN payroll_payment AS pr ON (pr.id = pay.payroll_id)
				LEFT JOIN res_company AS company ON (company.id = pr.company_id)
                LEFT JOIN res_partner AS partner ON (partner.id = pay.invoice_partner_id)
                LEFT JOIN account_move AS invoice ON (invoice.id = pay.invoice_id)
                LEFT JOIN account_payment AS payment ON (payment.id = pay.payment_id)
				LEFT JOIN account_move AS move_id ON (move_id.id = payment.move_id)
            %s
        """ % from_clause
        return from_

    def _group(self, groupby=""):
        groupby_ = """
            pr.name,
			pay.id,
			pay.invoice_partner_id,
			pay.invoice_id,
			pr.company_id,
			pr.user_id,
            pr.team_id,
			pr.state,
			pr.create_date,
            pay.payment_date,
			payment.move_id,
			partner.country_id,
		 	pr.id %s
        """ % (groupby)
        return groupby_
        
    def _query(self, with_clause='', fields=None, groupby='', from_clause=''):
        if not fields:
            fields = {}
        with_ = ("WITH %s" % with_clause) if with_clause else ""
        return '%s (SELECT %s FROM %s GROUP BY %s)' % \
               (with_, self._select(fields), self._from(from_clause), self._group(groupby))

    def init(self):
        # self._table = "payment_report_view"
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""CREATE or REPLACE VIEW %s as (%s)""" % (self._table, self._query()))