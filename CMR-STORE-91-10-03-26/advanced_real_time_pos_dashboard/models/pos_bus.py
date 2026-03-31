# -*- coding: utf-8 -*-

from odoo import models, api


class PosOrder(models.Model):
    _inherit = "pos.order"

    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            self.env["bus.bus"]._sendone(
                "pos_realtime_dashboard",
                "notification",
                {
                    "type": "new_order",
                    "order_id": order.id,
                    "name": order.name,
                    "amount_total": order.amount_total,
                    "state": order.state,
                    "date_order": order.date_order.isoformat() if order.date_order else False,
                    "partner_id": order.partner_id.id if order.partner_id else False,
                    "partner_name": order.partner_id.name if order.partner_id else "Walk-in Customer",
                    "session_id": order.session_id.id,
                    "session_name": order.session_id.name,
                    "pos_reference": order.pos_reference,
                    "lines_count": len(order.lines),
                }
            )
        return orders

    def write(self, vals):
        res = super().write(vals)
        for order in self:
            self.env["bus.bus"]._sendone(
                "pos_realtime_dashboard",  # channel
                "notification",  # notification type
                {
                    "type": "order_update",
                    "order_id": order.id,
                    "name": order.name,
                    "state": order.state,
                    "amount_total": order.amount_total,
                }
            )
        return res


class PosSession(models.Model):
    _inherit = "pos.session"

    def open_frontend_cb(self):
        res = super().open_frontend_cb()

        for session in self:
            self.env["bus.bus"]._sendone(
                "pos_realtime_dashboard",
                "notification",
                {
                    "type": "session_opened",
                    "session_id": session.id,
                    "name": session.name,
                    "user_id": session.user_id.id if session.user_id else False,
                    "user_name": session.user_id.name if session.user_id else "",
                    "config_id": session.config_id.id if session.config_id else False,
                    "config_name": session.config_id.name if session.config_id else "",
                    "state": session.state,
                }
            )

        return res

    def action_pos_session_closing_control(self):
        res = super().action_pos_session_closing_control()

        for session in self:
            self.env["bus.bus"]._sendone(
                "pos_realtime_dashboard",
                "notification",
                {
                    "type": "session_closing",
                    "session_id": session.id,
                    "name": session.name,
                    "state": session.state,
                    "total_payments_amount": session.total_payments_amount,
                }
            )

        return res

