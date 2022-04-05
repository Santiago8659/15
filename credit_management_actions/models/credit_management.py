from odoo import _, api, fields, models
from odoo.exceptions import UserError
import logging
import datetime

_logger = logging.getLogger(__name__)


class CreditManagement(models.Model):
    _name = 'credit.management'
    _description = 'Credit Management'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    


    #todo action en caso de que se seleccione que es una visita del vendedor, crear una tarea en odoo asignada al vendedor
    def demo(self):
        self.import_button()


    def _prepare_vals_to_task(self):
        invoice_model_id = self.env['ir.model'].sudo().search([('model','=','account.move')]).id
        credit_management_model_id = self.env['ir.model'].sudo().search([('model','=','credit.management')]).id
        vals_to_create = []
        vals = {
            'res_model_id':invoice_model_id,
            'res_id': self.invoice_id.id,
            'automated':True
        }

        if self.type_contact == "salesperson_visit":
            date = self.estimated_date_visit
            vals['summary'] = _('Collection Visit')
            vals['note'] = _("Action: Make collection visit for the date %s, Comment: %s") %(date, self.comment)
            vals['date_deadline'] = date
            vals['user_id'] = self.partner_id.user_id.id or self.invoice_id.invoice_user_id.id
            vals['activity_type_id'] = 4
            vals_to_create.append(vals)

            #here is the action to de collection agent
            date_to_check = self.estimated_date_visit + datetime.timedelta(days=1)
            task_collection_agent = {
                'res_model_id':credit_management_model_id,
                'res_id':  self.id,
                'automated': True,
                'summary': _('Verify the effectiveness of the visit'),
                'note': _("Action: Verify the effectiveness of the visit made %s, Comment: %s") %(self.estimated_date_visit, self.comment),
                'date_deadline': date_to_check,
                'user_id': self._uid,
                'activity_type_id': 2
            }
            vals_to_create.append(task_collection_agent)

        elif self.type_contact in ["family_message", "unlocated"]:
            
            date = (self.create_date + datetime.timedelta(days=3)).date()
            vals['summary'] = _('Contact Again')
            vals['note'] = _("Action: Make a new follow-up call on %s, Comment: %s") %(date, self.comment)
            vals['date_deadline'] = date
            vals['user_id'] = self._uid
            vals['activity_type_id'] = 2
            vals['res_id'] = self.id
            vals['res_model_id'] = credit_management_model_id
            vals_to_create.append(vals)

        elif self.type_contact in ["family_message", "unlocated"]:
            
            date = (self.create_date + datetime.timedelta(days=3)).date()
            vals['summary'] = _('Contact Again')
            vals['note'] = _("Action: Make a new follow-up call on %s, Comment: %s") %(date, self.comment)
            vals['date_deadline'] = date
            vals['user_id'] = self._uid
            vals['activity_type_id'] = 2
            vals['res_id'] = self.id
            vals['res_model_id'] = credit_management_model_id
            vals_to_create.append(vals)
        return vals_to_create

    def create_task_in_activity_mixin(self):
        vals = self._prepare_vals_to_task()
        _logger.info("estos son los valores%s", vals)
        create = self.env['mail.activity'].sudo().create(vals)

    # se debe generar un consecutivo
    name = fields.Char(
        string='Name')

    type_contact = fields.Selection([('payment_agreement','Payment Agreement'),('paying','Paying'),('unlocated','Unlocated'),('family_message','Family Message'),('salesperson_visit','Salesperson Visit')],
        string='Type of Contact', tracking=True)
    
    comment = fields.Text(
        string='Comment', tracking=True
    )
    #definir que ocurre en cada uno de los contactos
    

    company_id = fields.Many2one(
        comodel_name='res.company', string='Company', readonly=True,
        default=lambda self: self.env['res.company']._company_default_get('payroll.payment')
        )

    invoice_id = fields.Many2one(
        comodel_name="account.move", string='Invoice', store= True)
    partner_id = fields.Many2one(
        related='invoice_id.partner_id', store=True, string='Customer')
    invoice_date = fields.Date(related='invoice_id.invoice_date', string="Invoice Date")
    invoice_date_due = fields.Date(related='invoice_id.invoice_date_due', string="Invoice Date Due")
    invoice_payment_status = fields.Selection(related="invoice_id.payment_state", string="Payment State")
    saleperson_id = fields.Many2one(related="invoice_id.invoice_user_id",string="Saleperson")

    currency_id = fields.Many2one(
        related='invoice_id.currency_id', string='Currency', store=True, readonly = False
    )

    invoice_amount_total = fields.Monetary(
        string='Invoice Amount Total', related='invoice_id.amount_total', store=True)

    estimated_date_visit = fields.Date(string="Estimated Date of Visit")

    estimated_date_to_pay = fields.Date(string="Estimated Date to Pay")


    # <-- method modifitor -->
    
    #dias de mora

    #seleccion de varias opciones, llamas, programar visita, 

    #compromiso de pago, cuantos dias, el cliente queda bloqueado (hasta que se haga el pago)
    
    #añadir los dias en mora


    #que cuando el cliente pago se genere un color

    #mensaje, el cliente sale para gestion, cada tres dias durante un periodo de 2 meses despues de eso ya no se gestona mas y queda en estado no localizado

    #cuando se abra el cliente, salgan todos los acuerdos que se han hecho con el cliente

    # Colores en funcion del estado de la facutra, en especial verde si el cliente ya pago, en acuerdo de pago


    @api.model
    def create(self, vals):
        if vals.get('name') is None:
            vals['name'] = self.env['ir.sequence'].next_by_code(self._name)
        result = super(CreditManagement, self).create(vals)
        write_partner_id = result.partner_id.write({
            "credit_management_actions_ids": [(4,result.id,0)]
        })
        result.create_task_in_activity_mixin()
        return result
        