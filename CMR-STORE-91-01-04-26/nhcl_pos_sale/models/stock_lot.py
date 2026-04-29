from odoo import api, models, fields


class StockLot(models.Model):
    _inherit = 'stock.lot'

    product_qty_pos = fields.Float('On Hand Quantity POS', compute='_product_qty_pos', store=True)

    @api.depends('product_qty')
    def _product_qty_pos(self):
        for lot in self:
            lot.product_qty_pos = lot.product_qty