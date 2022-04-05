from odoo import api, fields, models, tools
from odoo.exceptions import UserError

class ResCompany(models.Model):
    _inherit = "res.company"

    payment_discount_account_id = fields.Many2one(
        comodel_name='account.account', 
        string="Discount Account",
        domain="[('deprecated', '=', False), ('company_id', '=', company_id)]"
        )
