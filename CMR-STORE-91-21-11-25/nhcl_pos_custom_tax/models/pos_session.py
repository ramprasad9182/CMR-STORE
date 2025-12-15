# -*- coding: utf-8 -*-
# Copyright (C) NextFlowIT

from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.session"

    def _loader_params_account_tax(self):
        res = super()._loader_params_account_tax()
        res["search_params"]["fields"].append("max_amount")
        res["search_params"]["fields"].append("min_amount")
        res["search_params"]["fields"].append("children_tax_ids")
        return res


    def _loader_params_loyalty_rule(self):
        res = super()._loader_params_loyalty_rule()
        res["search_params"]["fields"].append("serial_ids")
        return res

    def _loader_params_loyalty_reward(self):
        res = super()._loader_params_loyalty_reward()
        res["search_params"]["fields"].append("discount_product_id")
        res["search_params"]["fields"].append("product_price")
        res["search_params"]["fields"].append("buy_with_reward_price")
        res["search_params"]["fields"].append("reward_price")
        return res
