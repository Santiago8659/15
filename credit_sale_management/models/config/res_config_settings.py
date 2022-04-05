
from odoo import api, fields, models
from odoo.exceptions import UserError

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    payment_discount_account_id = fields.Many2one(
        related='company_id.payment_discount_account_id', 
        string="Discount Account",
        readonly=False
        )

    grace_days = fields.Integer(
        string='Grace days',
        default='5'
    )

    grace_days_to_report = fields.Integer(
        string='Grace Days to Report',
        default='1'
    )

    # check_discount = fields.Boolean(
    #     string='Check Discount',
    #     default='False'
    # )

    def set_values(self):
        res = super(ResConfigSettings, self).set_values()
        self.env['ir.config_parameter'].sudo().set_param('credit_sale_management.payment_discount_account_id', self.payment_discount_account_id.id)
        self.env['ir.config_parameter'].sudo().set_param('credit_sale_management.grace_days', self.grace_days)
        self.env['ir.config_parameter'].sudo().set_param('credit_sale_management.grace_days_to_report', self.grace_days_to_report)
        # self.env['ir.config_parameter'].sudo().set_param('credit_sale_management.check_discount', self.check_discount)
        return res 

    @api.model
    def get_values(self):
        res = super(ResConfigSettings, self).get_values()
        res['grace_days'] = self.env['ir.config_parameter'].sudo().get_param('credit_sale_management.grace_days')
        res['grace_days_to_report'] = self.env['ir.config_parameter'].sudo().get_param('credit_sale_management.grace_days_to_report')
        # res['check_discount'] = self.env['ir.config_parameter'].sudo().get_param('credit_sale_management.check_discount')
        return res

