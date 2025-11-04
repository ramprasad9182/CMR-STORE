# -*- coding: utf-8 -*-
from odoo import fields, models, api
class InheritUsers(models.Model):
    _inherit = 'res.users'

    allow_discount_button = fields.Boolean(string="POS - Enable Discount ")
    allow_numpad_button = fields.Boolean(string="POS - Enable Numpad ")
    allow_plusminus_button = fields.Boolean(string="POS - Enable Plus-Minus")
    allow_qty_button = fields.Boolean(string="POS - Enable Qty")
    allow_customer_selection = fields.Boolean(string="POS - Enable Customer")
    allow_remove_button = fields.Boolean(string="POS - Enable Remove Order Line")
    allow_price_button = fields.Boolean(string="POS - Enable Price")
    allow_payment_button = fields.Boolean(string="POS - Enable Payment")
    allow_refund_button = fields.Boolean(string="POS - Enable Refund")
    allow_new_order_button = fields.Boolean(string="POS - Enable New Order")
    allow_delete_order_button = fields.Boolean(string="POS - Enable Delete Order")
