from odoo import models, fields, api

class PosExchangeWizard(models.TransientModel):
    _name = 'pos.exchange.wizard'
    _description = 'POS Exchange Wizard'

    reason = fields.Text(string='Reason', required=True)
    nhcl_picking_id = fields.Many2one('stock.picking', string="Picking")
    bypass_exchange_wizard = fields.Boolean(string="Flag", default=False)

    def action_confirm(self):
        self.ensure_one()
        if self.nhcl_picking_id:
            self.nhcl_picking_id.exchange_reason = self.reason
            self.nhcl_picking_id.with_context(bypass_exchange_wizard=True).button_validate()


    @api.onchange('nhcl_picking_id')
    def onchange_nhcl_picking_id(self):
        if self.nhcl_picking_id:
            reasons = []
            for move in self.nhcl_picking_id.move_ids_without_package:
                if move.nhcl_exchange and move.serial_no:
                    reasons.append(f"Serial {move.serial_no} is added.")
            self.reason = '\n'.join(reasons)


class MessageWizard(models.TransientModel):
    _name = 'message.wizard'

    def get_default(self):
        if self.env.context.get("message", False):
            return self.env.context.get("message")
        return False

    message = fields.Text('Message', required=True, default=get_default)