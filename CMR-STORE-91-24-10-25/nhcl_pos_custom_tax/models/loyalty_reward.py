from odoo import fields, models, api, _


class LoyaltyReward(models.Model):
    _inherit = 'loyalty.reward'

    ref_loyalty_rule_id = fields.Many2one('loyalty.rule',string='Loyalty Rule')

    reward_type =fields.Selection(selection_add=[

        ('discount_on_product', 'Discounted Product')],ondelete={'discount_on_product': 'cascade'})

    discount_product_id = fields.Many2one('product.product',string="Discount On Product")

    product_price = fields.Float('Price')



    @api.depends('reward_type', 'reward_product_id', 'discount_mode', 'reward_product_tag_id',

                 'discount', 'currency_id', 'discount_applicability', 'all_discount_product_ids')

    def _compute_description(self):

        for reward in self:

            reward_string = ""

            if reward.reward_type == 'discount_on_product':

                products = reward.discount_product_id

                if len(products) == 0:

                    reward_string = _('Discount Product')

                elif len(products) == 1:

                    reward_string = _('Discount Product - %s',

                                      reward.discount_product_id.with_context(display_default_code=False).display_name)

                reward.description = reward_string

            else:

                super(LoyaltyReward, reward)._compute_description()

    @api.onchange("discount_applicability")
    @api.constrains("discount_applicability")
    def _onchange_discounted_products(self):
        for record in self:
            if record.discount_applicability == 'specific':
                for (i, j) in zip(range(0, len(record.program_id.rule_ids)), range(0, len(record.program_id.reward_ids))):
                    record.program_id.reward_ids[j].discount_product_ids = record.program_id.rule_ids[i].product_ids


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
