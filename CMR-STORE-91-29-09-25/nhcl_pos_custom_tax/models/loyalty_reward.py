from odoo import fields, models, api, _


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    ref_loyalty_rule_id = fields.Many2one('loyalty.rule',string='Loyalty Rule')

    @api.onchange("discount_applicability")
    @api.constrains("discount_applicability")
    def _onchange_discounted_products(self):
        if self.discount_applicability == 'specific':
            for (i, j) in zip(range(0, len(self.program_id.rule_ids)), range(0, len(self.program_id.reward_ids))):
                self.program_id.reward_ids[j].discount_product_ids = self.program_id.rule_ids[i].product_ids


# class LoyaltyRule(models.Model):
#     _inherit = 'loyalty.rule'
#
#     def create_rewards(self):
#         if self.ref_product_ids:
#             vals = {
#                 'discount_product_ids': self.ref_product_ids,
#                 'program_id': self.program_id.id,
#                 'discount': 1
#             }
#             self.env['loyalty.reward'].create(vals)
