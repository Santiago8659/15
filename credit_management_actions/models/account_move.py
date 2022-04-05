from odoo import _, api, fields, models


class accountMove(models.Model):
    _inherit = 'account.move'

    credit_management_actions_ids = fields.One2many(comodel_name="credit.management", inverse_name="invoice_id", string="Credit Management Actions", copy=True, auto_join=True)