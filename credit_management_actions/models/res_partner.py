from odoo import _, api, fields, models


class accountMove(models.Model):
    _inherit = 'res.partner'

    credit_management_actions_ids = fields.One2many(comodel_name="credit.management", inverse_name="partner_id", string="Credit Management Actions", readonly=True)
    

    @api.depends('credit_management_actions_ids')
    def _compute_count_cma(self):
        for res in self:
            res.count_cma = len(res.credit_management_actions_ids.ids)

    count_cma = fields.Integer(string="Qty of Actions", compute="_compute_count_cma")


