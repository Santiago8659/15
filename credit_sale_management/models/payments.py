from odoo import _, fields, api, models
from odoo.exceptions import UserError

from datetime import datetime

class PaymentReport(models.Model):
    _name = 'payment.report'
    _description = "Payment Report"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    

    #aaqui puedo hacer validaciones antes de que se cree el sistema

    #aqui van las acciones de los botones
    def action_confirm(self):
        for pay in self:
            pay.ensure_one()
            pay.check_discount()
            pay._compute_ref()
            pay.action_create_payment()
            pay.check_reconcile()
            pay._action_confirm()
    
    def _action_confirm(self):
        for pay in self:
            pay.confirm_date = fields.Datetime.now()
            pay.state = 'to_check'

    def action_draft(self):
        for pay in self:
            if pay.state_reconcile == 'reconciled':
                raise UserError(_('Cannot be modified after reconciled'))
            pay.ensure_one()
            pay.action_draft_payment()
            pay.amount_residual = 0
            pay.state = 'draft'

    def action_cancel(self):
        for pay in self:
            pay.action_cancel_payment()
            pay.state = 'cancel'

    def action_validate(self):
        for pay in self:
            pay.ensure_one()
            if pay.payment_id.move_id.state != 'posted':
                pay.amount_residual = pay.invoice_amount_residual
                pay.action_write_payment()
                pay.check_amount()
                pay.check_discount()
                pay.check_reconcile()
                pay.action_post_payment()
                
            pay.action_assign_outstanding_line()
            pay.state = 'done'
            return True

    def action_assign_outstanding_line(self):
        invoice = self.env['account.move'].search([('id','=',self.invoice_id.id)])
        account_move_line = self.payment_id.move_id.line_ids
        account_move_line = account_move_line.filtered(lambda line: line.account_id.user_type_id.type == 'receivable').id
        assing_invoice = invoice.js_assign_outstanding_line(account_move_line)
        return assing_invoice

    def action_break_reconcile(self):
        invoice = self.env['account.move'].search([('id', '=', self.invoice_id.id)])
        account_move_line = max(self.payment_id.move_id.line_ids.mapped('id'))
        break_reconcilie = invoice.js_assign_outstanding_line(account_move_line)

    def get_vals(self):
        for pay in self:
            vals = {}
            vals['payment_type'] = pay.payment_type
            vals['partner_type'] = pay.partner_type
            vals['partner_id'] = pay.invoice_partner_id.id
            vals['date'] = pay.payment_date
            # vals['destinantion_account_id'] = pay.destinantion_account_id
            vals['amount'] = pay.amount
            vals['ref'] = pay.ref
            vals['journal_id'] = pay.journal_id.id
            vals['payment_receipt_id'] = pay.id
            if pay.payroll_id:
                vals['payroll_id'] = pay.payroll_id.id
            return vals

    def action_write_payment(self):
        for pay in self:
            if pay.payment_id:
                vals = pay.get_vals()
                payment = self.env['account.payment'].sudo().search([('id', '=', pay.payment_id.id)]).write(vals)

    def action_create_payment(self):
        for pay in self:
            if pay.payment_id.id == False:
                vals = pay.get_vals()
                create = self.env['account.payment'].sudo().create(vals)
                pay.payment_id = create.id
            else:
                pay.action_write_payment()

    def action_cancel_payment(self):
        for pay in self:
            pay.payment_id.action_cancel()
    
    def action_post_payment(self):
        for pay in self:
            payment_id = self.env['account.payment'].sudo().search([('id','=',pay.payment_id.id)])
            payment_id_action = payment_id.action_post()

    def action_draft_payment(self):
        for pay in self:
            payment_id = self.env['account.payment'].sudo().search([('id','=',pay.payment_id.id)])
            payment_id_action = payment_id.action_draft()

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': self._name, 'default_res_id': self.id}
        return res

    def _create_discounts_vals_from_payment_report(self):
        discount_account_line = {
        'account_id': self.discount_account_id.id,
        'partner_id': self.invoice_partner_id.id,
        'name': self.discount_label, 
        'amount_currency': self.cash_discount,
        'currency_id': self.currency_id.id,
        'move_id': self.payment_id.move_id.id
        }
        discount_account_line['move_id'] = self.payment_id.move_id.id
        return discount_account_line
    
    def _create_account_move(self):
        for pay in self:
            move_id = pay.payment_id.move_id
            credit_lines = ''
            debit_lines = ''
            line_ids = move_id.line_ids.account_id.ids
            vals = pay._create_discounts_vals_from_payment_report()
            if not pay.discount_account_id.id in line_ids:
                discount_account_move_line = self.env['account.move.line'].sudo().create(vals)
            credit = pay.invoice_partner_id.property_account_receivable_id
            line_account = []
            for line in move_id.line_ids:
                line_account.append(line.account_id.code)
                if line.account_id.id == pay.invoice_partner_id.property_account_receivable_id.id:
                    credit = pay.invoice_partner_id.property_account_receivable_id
                    credit_lines = line.id
                if line.account_id.id == pay.discount_account_id.id:
                    debit = pay.discount_account_id
                    debit_lines = line.id
            balanced_value = (pay.cash_discount+self.payment_id.amount)
            move_id.sudo().write({'line_ids': [
                        (1, debit_lines, {'debit': pay.cash_discount}),
                        (1, credit_lines, {'credit': balanced_value}),
                    ]})

    def _remove_account_move(self):
        for pay in self:
            move_id = pay.payment_id.move_id
            credit_lines = ''
            debit_lines = ''
            for line in move_id.line_ids:
                if line.account_id.id == pay.invoice_partner_id.property_account_receivable_id.id:
                    credit_lines = line.id
                if line.account_id.id == pay.discount_account_id.id:
                    debit_lines = line.id
            balanced_value = (pay.cash_discount+self.payment_id.amount)
            move_id.sudo().write({'line_ids': [
                        (2, debit_lines, {'debit': pay.cash_discount, 'amount_currency': pay.cash_discount}),
                        (1, credit_lines, {'credit': balanced_value, 'amount_currency': -balanced_value}),
                    ]})

    
    #Aqui van las validaciones
    def check_amount(self):
        for pay in self:
            invoice_amount_residual = self.env['payment.report'].sudo().search([('id','=',pay.id)]).invoice_amount_residual
            if pay.amount > pay.invoice_amount_residual:
                raise UserError(f'En el recibo de pago {pay.name}: Se esta intentando registar un pago por valor mayor al audeudado, no se puede')
            elif pay.amount == False or pay.amount == 0:
                raise UserError(f'En el recibo de pago {pay.name}: No se puede registar un pago sin valor o por valor 0')

    def check_reconcile(self):
        for pay in self:
            if pay.payment_difference_handling == 'reconcile':
                pay.check_account_balanced()
                if pay.payment_id:
                    pay._create_account_move()
            else:
                pay._remove_account_move()
            #crear una funcion que en caso de que se actualice debe eliminar las cuentas añadidas y ajustarlas

    def check_account_balanced(self):
        for pay in self:
            balanced = int(pay.invoice_amount_residual) - int(pay.amount) - int(pay.cash_discount)
            if balanced != 0:
                total_payment = int(pay.amount + pay.cash_discount)
                residual_amount = int(pay.invoice_amount_residual-total_payment)
                raise UserError (f'En el recibo de pago {pay.name}, la suma del valor pagado {int(pay.amount)} y el descuento {int(pay.cash_discount)} es igual a {total_payment} y no es igual al valor adeudado {int(pay.invoice_amount_residual)}, por favor revisar la diferencia de {residual_amount}')

    def check_discount(self):
        for pay in self:
            return True
            if pay.payment_difference_handling == 'reconcile':
            #aqui tenemos que luego revisar si e descuento es antes de iva?
                payment_term_discount = pay.invoice_id.invoice_payment_term_id.discount
                partner_discount = pay.invoice_partner_id.discount
                calculate_cash_discount = (pay.cash_discount / pay.invoice_amount_total)*100
                if partner_discount != 0 or payment_term_discount != 0:
                    if partner_discount != 0:
                        line_ids = pay.invoice_id.line_ids
                        for line in line_ids:
                            if line.discount == partner_discount:
                                raise UserError(f'En el recibo de pago {pay.name}, para el producto {line.product_id.name} el descuento esta aplicado directamente en la factura')
                    if pay.cash_discount != 0:
                        if partner_discount != 0 and calculate_cash_discount > partner_discount or payment_term_discount != 0 and calculate_cash_discount > payment_term_discount:
                            raise UserError(f'En el recibo de pago {pay.name}, el descuento aprovado {partner_discount}% / {payment_term_discount}%, el descuento registrado es {calculate_cash_discount}% y no puede ser mayor al aprovado')
                elif payment_term_discount == 0 and pay.cash_discount != 0:
                    raise UserError(f'En el recibo de pago {pay.name}, para la factura {pay.invoice_id.name} no se ha configurado ninguna descuento, el descuento registrado es {calculate_cash_discount}% por favor revisar')
                elif partner_discount != 0 and payment_term_discount != 0:
                    raise UserError(f'En el recibo de pago {pay.name}, para el asociado {pay.invoice_partner_id.name} tiene configurado el descuento dos veces, por favor revisar')

        #aqui vamos a validar:
        #1- en caso que se tenga configurado un descuento en el partner entonces validar el desceutn ode la orden de venta asociada a la factura
        #2- en caso que tenga configurado una condicion de pago, entonces verificar el desceunto que esta en esa condicon
    @api.depends('state')
    def _compute_attachment_number(self):
        for pay in self:
            attachment_number = self.env['ir.attachment'].search_count([('res_model', '=', pay._name), ('res_id', 'in', pay.ids)])
            pay.attachment_number = attachment_number
        
    attachment_number = fields.Integer(
        string='attachment_number',compute='_compute_attachment_number', store=True)
        
    def _compute_payment_receipt_attachment_id(self):
        for pay in self:
            attachment_ids = self.env['ir.attachment'].search([('res_model', '=', pay._name), ('res_id', 'in', pay.ids)]).ids
            self.payment_receipt_attachment_id = [(6, 0, attachment_ids)]

    @api.depends('journal_id')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.journal_id.currency_id or pay.company_id.currency_id

    @api.depends('amount', 'cash_discount','state')
    def _compute_payment_diference(self):
        for pay in self:
            if pay.payment_difference_handling == 'reconcile':
                pay.payment_difference = pay.invoice_amount_residual - pay.amount + pay.amount_residual
            else:
                if pay.state in ['draft', 'to_check']:
                    pay.payment_difference = pay.invoice_amount_residual - pay.amount + pay.amount_residual
                else:
                    pay.payment_difference = pay.amount_residual  - pay.amount

    @api.depends('amount', 'cash_discount')
    def _compute_final_payment_diference(self):
        for pay in self:
            pay.final_payment_difference = pay.invoice_amount_residual - pay.amount - pay.cash_discount + pay.amount_residual

    @api.depends('amount', 'cash_discount')
    def _compute_ref(self):
        for pay in self:
            status_payment = ''
            if (pay.invoice_amount_residual - pay.amount) > 0 and (pay.final_payment_difference - pay.cash_discount) > 0:
                status_payment = 'Abono'
            else:
                status_payment = 'Cancela'
            pay.ref = f'{pay.invoice_id.name} - {pay.create_uid.name} - {status_payment}'

    @api.depends('amount')
    def _compute_internal_reference(self):
        for pay in self:
            pay.internal_reference = f'({pay.invoice_id.name} - {pay.invoice_partner_id.name})'

    @api.depends('invoice_id')
    def _compute_invoice_partner_id(self):
        for pay in self:
            if pay.invoice_id.partner_id.id:
                invoice_partner_id = pay.invoice_id.partner_id.id
                pay.invoice_partner_id = invoice_partner_id
            else:
                pay.invoice_partner_id = None

    @api.depends('invoice_id')
    def _compute_note_invoice(self):
        for pay in self:
            invoices_due = self.env['account.move'].search([('partner_id.id','=',pay.invoice_partner_id.id),('payment_state', 'in', ('not_paid','partial')),('state', '=','posted')])
            if len(invoices_due.ids) != 0:
                date = []
                for i in invoices_due:
                    if i.invoice_date_due != False:
                        date.append(i.invoice_date_due)
                min_date_invoices_due = min(date)
                max_date_invoices_due = max(date)
                if min_date_invoices_due == pay.invoice_date_due:
                    pay.note_invoice = f'Esa es la Factura Correcta'
                    pay.not_invoice = False
                else:
                    first_invoices_due = self.env['account.move'].search([('partner_id.id','=',pay.invoice_partner_id.id),('payment_state', 'in', ('not_paid','partial')),('invoice_date_due', '=', min_date_invoices_due)])
                    invoices = []
                    for i in first_invoices_due:
                        invoice = f'{i.name} / {i.invoice_date} / vence: {i.invoice_date_due}'
                        invoices.append(invoice)
                    invoices = ", ".join(invoices)
                    pay.note_invoice = f'UPS, Esta no es la factura mas vieja, intenta con {invoices}'
                    pay.not_invoice = True
            else:
                pay.note_invoice = f''
    
    @api.depends('payment_date')
    def _compute_not_on_time(self):
        date_time_format = '%Y-%m-%d %H:%M:%S.%f'
        date_format = '%Y-%m-%d'
        grace_days_to_report = self.env['ir.config_parameter'].sudo().get_param('credit_sale_management.grace_days_to_report')
        for pay in self:
            payment_date = pay.payment_date
            if pay.create_date:
                if payment_date:
                    payment_date = datetime.strptime(str(payment_date), date_format).date()
                    payment_report = pay.create_date
                    payment_report = datetime.strptime(str(payment_report), date_time_format).date()
                    days = abs(int((payment_date - payment_report).days))
                    if days > int(grace_days_to_report):
                        pay.not_on_time = True
                    else:
                        pay.not_on_time = False
            else:
                pay.not_on_time = False


    @api.onchange('payment_difference_handling')
    def _reset_cash_discount(self):
        for pay in self:
            if pay.payment_difference_handling == 'open':
                pay.cash_discount = 0

    @api.depends('amount', 'payment_date', 'state')
    def _calculate_note_cash_discount(self):
        grace_days = self.env['ir.config_parameter'].sudo().get_param('credit_sale_management.grace_days')
        grace_days = int(grace_days)
        format = '%Y-%m-%d'
        for pay in self:
            if pay.payment_date is False or pay.payment_difference_handling == 'open':
                today = fields.Date.today()
                pay.note_cash_discount = f''
                pay.not_discount = False
            else:
                today = pay.payment_date
                today = datetime.strptime(str(today), format)
                invoice_date_due = datetime.strptime(str(pay.invoice_id.invoice_date_due), format)
                days = (int((today - invoice_date_due).days)-grace_days)
                if days > grace_days:
                    pay.note_cash_discount = f'La factura esta vencida, no tiene descuento, tiene {days} dias de vencido'
                    pay.not_discount = True
                else:
                    pay.note_cash_discount = f'La obligación esta en el tiempo de pago'
                    pay.not_discount = False

    @api.depends('invoice_id')
    def _compute_residual_amount(self):
        for pay in self:
            pay.invoice_amount_residual = pay.invoice_id.amount_residual

    def time_to_report(self):
        #aqui vamos a calcular el tiempo desde que se hizo el pago hasta que se hizo el reporte
        pass

    @api.depends('user_id', 'payment_receipt')
    def _compute_allow_journal_id(self):
        for pay in self:
            allow_journal_id = self.env['saleperson.bank'].sudo().search([('user_id', '=', pay._uid)]).journal_id
            journal_id_domain_company = []
            for journal in allow_journal_id:
                if journal.company_id == pay.company_id:
                    journal_id_domain_company.append(journal.id)
            if allow_journal_id:
                pay.allow_journal_id = [(6, 0, journal_id_domain_company)]
            else:
                pay.allow_journal_id = False
    
    @api.depends('state', 'not_discount', 'not_invoice', 'not_on_time')
    def _compute_register_error_logs(self):
        error_logs = []
        not_discount = self.env['payment.error.log'].sudo().search([('name', '=', 'Discount Not Applicable')]).id 
        not_inovice = self.env['payment.error.log'].sudo().search([('name', '=', 'Fist Generate First Payment')]).id 
        not_attachment = self.env['payment.error.log'].sudo().search([('name', '=', 'Cash Receipt Not Attached')]).id
        not_on_time = self.env['payment.error.log'].sudo().search([('name', '=', 'Payment Date Different From The Report')]).id
        for pay in self:
            if pay.not_discount:
                pay.error_log = [(4, not_discount, 0)]
            else:
                pay.error_log = [(3, not_discount, 0)]
            if pay.not_invoice:
                pay.error_log = [(4, not_inovice, 0)]
            else:
                pay.error_log = [(3, not_inovice, 0)]
            if pay.attachment_number == 0:
                pay.error_log = [(4, not_attachment, 0)]
            else:
                pay.error_log = [(3, not_attachment, 0)]
            if pay.not_on_time:
                pay.error_log = [(4, not_on_time, 0)]
            else:
                pay.error_log = [(3, not_on_time, 0)]

    internal_reference = fields.Char(string="Name", store=True, compute='_compute_internal_reference')

    name = fields.Char(string='Payment Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))

    state = fields.Selection([
            ('draft','Draft'),
            ('to_check','To Check'),
            ('done','Done'),
            ('reject','Reject'),
            ('cancel','Canceled')
        ], string='Status', default='draft', tracking=True)

    state_reconcile = fields.Selection([
        ('to_reconcile','To reconcile'),
        ('reconciled','reconciled')
    ], string='Reconciliation Status', default='to_reconcile', readonly=True)

    confirm_date = fields.Datetime(string="Confirm Date")

    # == is in the model ==
    payment_type = fields.Selection([
        ('outbound', 'Send Money'),
        ('inbound', 'Receive Money'),], string='Payment Type', default='inbound', required=True)
    partner_type = fields.Selection([
        ('customer', 'Customer'),
        ('supplier', 'Vendor'),], default='customer', tracking=True, required=True)

    # == Payment Information ==
    #falta añadir en el dominio que solo le salgan las facturas de los clientes que estan asociados a el
    invoice_id = fields.Many2one(
        comodel_name='account.move', string="Invoice", store= True, required=True,
        domain="[('move_type', '=','out_invoice'),('payment_state', 'in', ('not_paid','partial')),('state', '=','posted'),('company_id', '=', company_id)]")
    
    note_invoice = fields.Char(
        string='Note', compute="_compute_note_invoice", readonly=True)

    not_invoice = fields.Boolean(
        default=False)

    invoice_payment_state = fields.Selection(
        related='invoice_id.payment_state', string='Payment State')

    invoice_partner_id = fields.Many2one(
        comodel_name='res.partner', string="Customer", store=True, readonly=True, compute='_compute_invoice_partner_id')

    # partner_discount = fields.Float(related='invoice_partner_id.discount')

    partner_property_payment_term_id = fields.Many2one(related='invoice_partner_id.property_payment_term_id')

    invoice_date = fields.Date(
        related='invoice_id.invoice_date', store=True)

    invoice_date_due = fields.Date(
        related='invoice_id.invoice_date_due', store=True)

    payment_date = fields.Date(
        string="Date", required=True, tracking=True)

    not_on_time = fields.Boolean(
        default=False, compute='_compute_not_on_time', store=False)
    
    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency', store = True, readonly = False, compute = '_compute_currency_id')

    invoice_amount_total = fields.Monetary(
        string='Invoice Amount Total', related='invoice_id.amount_total', store=True)
    invoice_amount_untaxed = fields.Monetary(
        string='Invoice Amount Untaxed', related='invoice_id.amount_untaxed', store=True)


    amount_residual = fields.Monetary(
        string='Residual Amount', readonly='True')
    invoice_amount_residual = fields.Monetary(
        string='Residual Amount', readonly=True, _depends_context = 'invoice_id', compute='_compute_residual_amount', depends=['invoice_id'])
    new_invoice_amount_residual = fields.Monetary(
        string='New Invoice Residual Amount')
        
    amount = fields.Monetary(
        string='Amount', tracking=True)

    payment_difference = fields.Monetary(
        string='Payment Difference', compute='_compute_payment_diference')
    
    final_payment_difference = fields.Monetary(
        string='Final Payment Difference', compute='_compute_final_payment_diference')

    payment_difference_handling = fields.Selection([
        ('open', 'Keep open'),
        ('reconcile', 'Mark as fully paid'),
    ], default='open', string="Payment Difference Handling")

    discount_account_id = fields.Many2one(
        comodel_name='account.account', string="Discount Account", 
        default = lambda self: self.env['res.company'].sudo().search([('id','=', self.env.company.id)]).payment_discount_account_id.id, copy=False,
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]")
    #se debe crear un campo computado con la informacion que iria o con la informacion que se ponga manual
    discount_label = fields.Char(
        string='Discount Line Label', default='Discount')

    cash_discount = fields.Monetary(
        string='Cash Discount', tracking=True)

    note_cash_discount = fields.Char(
        string='Note', compute='_calculate_note_cash_discount')
    
    not_discount = fields.Boolean(
        default=False ,compute="_calculate_note_cash_discount", store=False)

    salesperson_cost = fields.Monetary(string="Salesperson Cost")

    #aqui vamos a hacer el campo computado que calcule el costo de sales person


    
    ref = fields.Char(string='Memo', readonly=False, tracking=True)
    
    comment = fields.Char(string='Comment', tracking=True)

    task_message = fields.Selection([('discount_value','Discount Value Error'),('invoice_error','Error en la Factura'),('attach_receipt','Attach Receipt')], string='Task Message')

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company',readonly=True, store=True, 
        default=lambda self: self.env['res.company']._company_default_get('payroll.payment')
        )
    
    journal_id = fields.Many2one(
        comodel_name='account.journal', string="Bank", store=True, required=True, domain="[('type','=','bank'),('company_id','=',company_id)]")

    allow_journal_id = fields.Many2many(
        comodel_name='account.journal', domain="[('type','=','bank'),('company_id','=',company_id)]", compute='_compute_allow_journal_id',
        # default=[(6, 0, lambda self: self.env['saleperson.bank'].sudo().search([('user_id', '=', self._uid)]).ids)],
        string="Allow Journal")
    
    payment_id = fields.Many2one(
        comodel_name='account.payment', string="Payment", store=True, readonly=True)

    move_id = fields.Many2one(
        related='payment_id.move_id', string="Account Move", store=True)
    
    payroll_id = fields.Many2one(
        comodel_name="payroll.payment", string="Payroll", readonly=True)

    #Esta es la cuenta
    destination_account_id = fields.Many2one(
        comodel_name='account.account',string='Destination Account', store=True, readonly=False,
        #compute='_compute_destination_account_id',
        domain="[('user_type_id.type', 'in', ('receivable', 'payable')), ('company_id', '=', company_id)]",check_company=True)

    payment_receipt_number = fields.Integer(
        string="Payment Receipt Number", tracking=True)
    
    payment_receipt = fields.Binary(
        string='Payment Receipt')

    payment_receipt_attachment_id = fields.Many2many(
        comodel_name='ir.attachment', string="Attachment",compute='_compute_payment_receipt_attachment_id')

    user_id = fields.Many2one(
        comodel_name='res.users', string='Saleperson', default=lambda self: self._uid)

    error_log = fields.Many2many(
        comodel_name='payment.error.log', compute="_compute_register_error_logs",readonly=False, string="Error Log")

    
    def demo(self):
        for pay in self:
            attachment_ids = self.env['ir.attachment'].search([('res_model', '=', pay._name), ('res_id', 'in', pay.ids)]).ids
            self.payment_receipt_attachment_id = [(6, 0, attachment_ids)]



    def create_task_in_activity_mixin(self):
        model_id = self.env['ir.model'].sudo().search([('model','=','payroll.payment')]).id
        parent_id = self.env['hr.employee'].sudo().search([('user_id.id','=',self.user_id.id)]).parent_id.user_id.id
        vals = {
        'res_model_id':model_id,
        'res_id':self.payroll_id.id,
        'activity_type_id':4,
        'date_deadline': fields.date.today(),
        'user_id': parent_id or self.user_id.id,
        'automated':True
        }

        if self.task_message == 'discount_value':
            vals['summary'] = f'({self.name}):Revisar el valor de Descuento'
            vals['note'] = 'El valor de descuento aplicado no es el correcto o El vendedor {self.user_id.name} aplico un descuento mayor al establecido'
        if self.task_message == 'invoice_error':
            vals['summary'] = f'({self.name}):La Factura es incorrecta'
            vals['note'] = 'Por favor realizar la gestion de cartera correspondiente para generar el recaudo cuanto antes.'

        if self.task_message == 'attach_receipt':
            vals['summary'] = f'({self.name}):Falta adjuntar el recibo de la consignacion'
            vals['note'] = 'Por favor enviar el soporte del pago de la consignacion.'

        create = self.env['mail.activity'].sudo().create(vals)

    #todo crear un field, con el valor de descuento sugerido
    #context = "{'form_view_ref' : 'hr_expense.hr_expense_view_form_without_header', 'default_company_id': company_id, 'default_employee_id': employee_id}" >


    @api.model
    def create(self, vals):
        result = super(PaymentReport, self).create(vals)
        result.check_amount()
        if vals.get('name', _('New')) == _('New'):
            write_vals = {}
            write_vals['name'] = self.env['ir.sequence'].next_by_code(self._name) or _('New')
        result.write(write_vals)
        return result

class PaymentErrorLog(models.Model):
    _name = 'payment.error.log'
    _description = "Payment Error Log"

    name = fields.Char(string='Name')
    severity = fields.Integer(string="Severity")

class salepersonBank(models.Model):
    _name = 'saleperson.bank'

    name = fields.Char(string='Saleperson', compute='_compute_name')

    @api.depends('user_id')
    def _compute_name(self):
        for u in self:
            u.name = u.user_id.name

    user_id = fields.Many2one(
        comodel_name='res.users',
        string='Saleperson',
        required=True
    )

    journal_id = fields.Many2many(
        comodel_name='account.journal',
        string="Bank",
        store=True,
        domain="[('type','=','bank')]")

class PayrollPayment(models.Model):
    _name = 'payroll.payment'
    _description = "Payroll Payment"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = "create_date desc"

    internal_reference = fields.Char(string="Name", store=True, compute='_compute_internal_reference')
    name = fields.Char(string='Payment Reference', required=True, copy=False, readonly=True, states={'draft': [('readonly', False)]}, index=True, default=lambda self: _('New'))
    
    @api.depends('total_amount')
    def _compute_internal_reference(self):
        for pay in self:
            date = fields.Date.today()
            create_uid = pay.create_uid.name
            total_amount = pay.total_amount
            pay.internal_reference = f'{date} // {create_uid} // {total_amount}'



    @api.depends('user_id', 'payment_receipt')
    def _compute_allow_journal_id(self):
        for pay in self:
            allow_journal_id = self.env['saleperson.bank'].sudo().search([('user_id', '=', pay._uid)]).journal_id
            journal_id_domain_company = []
            for journal in allow_journal_id:
                if journal.company_id == pay.company_id:
                    journal_id_domain_company.append(journal.id)
            if allow_journal_id:
                pay.allow_journal_id = [(6, 0, journal_id_domain_company)]
            else:
                pay.allow_journal_id = False
    
    allow_journal_id = fields.Many2many(
        comodel_name='account.journal', domain="[('type','=','bank'),('company_id','=',company_id)]", compute='_compute_allow_journal_id', string="Allow Journal")

    @api.depends('state')
    def _compute_attachment_number(self):
        for pay in self:
            ids = pay.payment_receipt.ids
            ids.append(pay.id)
            attachment_number = self.env['ir.attachment'].search_count([('res_model', 'in', ['payment.report', pay._name]), ('res_id', 'in', ids)])
            pay.attachment_number = attachment_number
    
    attachment_number = fields.Integer(string='Attachment Number', compute='_compute_attachment_number', store=True)

    @api.depends('payment_receipt', 'payment_receipt.amount')
    def _compute_total_amount(self):
        for pay in self:
            pay.total_amount = sum(pay.payment_receipt.mapped('amount'))

    @api.depends('payment_receipt')
    def _compute_currency_id(self):
        for pay in self:
            pay.currency_id = pay.payment_receipt.currency_id or pay.company_id.currency_id

    def _compute_amount_residual(self):
        self.amount_residual = 0

    def link_payroll(self):
        for line in self.payment_receipt:
            if line.id:
                if line.payroll_id.id is False:
                    line.payroll_id = self.id
                else:
                    if line.payroll_id.id == self.id:
                        pass
                    else:
                        raise UserError(_('Este pago %s ya esta relacionado el la planilla %s, no se puede relacionar dos veces') %(line.name, line.payroll_id.name))
            else:
                raise UserError(_('Debes asignar a un pago a la planilla'))

    # def vals_to_post(self):
    #     self.create_account_bank_statement_line()
    #     vals = {}
    #     vals['account.bank.statement.line'] = ""


    # def create_account_bank_statement_line(self):
    #     vals = {}
    #     vals['date'] = ""
    #     vals['payment_ref'] = ""
    #     vals['amount'] = ""

    #     create_line = self.env['account.bank.statement.line'].sudo().create(vals)
    #     return create_line

    def action_post_payroll(self):
        for pay in self:
            for p in pay.payment_receipt:
                if p.state == 'to_check':
                    p.action_validate()
                if p.state == 'draft':
                    raise UserError(f'El recivo de pago {p.name}, esta en estado borrador, debe estar en estado validado para poderlo publicar')
            pay.state = 'post'
            pay.action_done_payroll()
            pay.approving_user = self.env.uid
            pay.account_date = fields.datetime.now()

    def action_submit_payroll(self):
        for pay in self:
            if pay.payment_receipt:
                pay.state = 'submit'
                # pay.link_payroll()
                
                for p in pay.payment_receipt:
                    if p.payment_id:
                        p._action_confirm()
                    else:
                        p.action_confirm()
            else:
                raise UserError(_('Para la Planilla %s: no se puede enviar sin ningun pago registrado')% pay.name)
        return True

    def action_draft_payroll(self):
        for pay in self:
            if pay.state_reconcile == 'reconciled':
                raise UserError(_('Cannot be modified after reconciled'))
            pay.state = 'draft'
            for p in pay.payment_receipt:
                p.action_draft()
            return True

    def action_done_payroll(self):
        for pay in self:
            pay.state = 'done'
            return True
        
    def action_cancel_payroll(self):
        wizardData = {
            'payroll_payment_id' : self.id
        }
        wizard = self.env['cancel.reason.wizard'].create(wizardData)
        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Reazon Wizard'),
            'res_model': 'cancel.reason.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'view_id': self.env.ref('credit_sale_management.cancel_reason_wizard_form_view').id,
            'target': 'new',
        }

        for pr in self:
            pr.state = 'cancel'
            for pay in pr.payment_receipt:
                pay.action_draft()
                pay.action_cancel()
            return True

    def action_get_attachment_view(self):
        res = self.env['ir.actions.act_window']._for_xml_id('base.action_attachment')
        res['domain'] = [('res_model', '=', self._name), ('res_id', 'in', self.ids)]
        res['context'] = {'default_res_model': self._name, 'default_res_id': self.id}
        return res


    date = fields.Datetime(string="Date")

    account_date = fields.Datetime(string='Account Date', readonly=True, tracking=True)

    reconciliation_date = fields.Datetime(string="Reconciliation Date", readonly=True, tracking=True)
    
    state = fields.Selection([
            ('draft','Draft'),
            ('submit','Submit'),
            ('post','Post'),
            ('done','Done'),
            ('cancel','Canceled')
        ],
        string='State', default='draft', tracking=True
    )

    state_reconcile = fields.Selection([
        ('to_reconcile','To reconcile'),
        ('reconciled','reconciled')
    ], string='Reconciliation Status', default='to_reconcile', readonly=True)

    

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('payroll.payment')
        )

    currency_id = fields.Many2one(
        comodel_name='res.currency', string='Currency', store = True, readonly = False, compute = '_compute_currency_id')

    user_id = fields.Many2one(
        comodel_name='res.users', string='Saleperson',
        default=lambda self: self._uid
    )

    @api.model
    def _get_default_team(self):
        return self.env['crm.team']._get_default_team_id()
        
    team_id = fields.Many2one(
        'crm.team', 'Sales Team',
        change_default=True, default=_get_default_team, check_company=True,  # Unrequired company
        domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")

    payment_support = fields.Binary(string='Payment Support')

    total_amount = fields.Float(
        string='Total Amount', compute='_compute_total_amount', store=True)

    amount_residual = fields.Float(
        string='Total Amount', compute='_compute_amount_residual', store=True)

    approving_user = fields.Many2one(comodel_name='res.users', string='Approving User'
    )

    journal_id = fields.Many2one(comodel_name='account.journal',string='Bank', store=True, required=True, domain="[('type','=','bank'),('company_id','=',company_id)]")

    payment_receipt = fields.Many2many(comodel_name='payment.report', string="Payment Receipt")
    
    payment_support = fields.Binary(string='Payment Support')

    error_count = fields.Integer(string='Error Count', compute='_compute_errors_count', store='True')

    comment = fields.Text(string="Comment")

    cancel_reason = fields.Char(string="Cancel Reason")

    

    @api.depends('state')   
    def _compute_errors_count(self):
        for p in self:
            p.error_count = 0
            for pay in p.payment_receipt:
                error_log = pay.error_log
                count_error_log = len(error_log.mapped('id'))
                p.error_count += count_error_log

    def no_action(self):
        pass


    # mostrar opciona verifico
    # soporte de consignacion
    # banco
    #seleccionar varios pagos y desde ahi crear la planilla
    #se debe verificar que no sea un pago que ya esta reportado
    #crear la planilla directamente desde el pago


    def _compute_approving_user(self):
        pass

    def demo(self):
        self._compute_attachment_number()
        
     #aaqui puedo hacer validaciones antes de que se cree el sistema
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            seq_date = None
            vals['name'] = self.env['ir.sequence'].next_by_code(self._name) or _('New')
        result = super(PayrollPayment, self).create(vals)
        if result.payment_receipt:
            for p in result.payment_receipt:
                p.payroll_id = result.id
        return result

    def write(self, vals):
        # print('Start write----', vals)

        #aqui quitamos la relacion
        payment_receipts = vals.get('payment_receipt')
        if payment_receipts:
            payment_receipts_ids = payment_receipts[0][2]
            if self.payment_receipt:
                for p in self.payment_receipt:
                    if p not in payment_receipts_ids:
                        p.payroll_id = False


        result = super(PayrollPayment, self).write(vals)


        #aqui actualizmaos las relaciones 
        if self.payment_receipt:
             for p in self.payment_receipt:
                    p.payroll_id = self.id
                    
        # print('return data----', result)
        return result