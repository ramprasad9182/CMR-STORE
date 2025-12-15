import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def _format_number(self, value):
        """Return nicely formatted string: thousands sep, no .0 for integers, 2 decimals otherwise."""
        try:
            v = float(value or 0.0)
        except Exception:
            return "0"
        if abs(v - int(v)) < 1e-9:
            return "{:,.0f}".format(v)  # no decimals for whole numbers
        return "{:,.2f}".format(v)      # two decimals otherwise

    @api.model
    def get_receipts_totals(self, **kwargs):

        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()


        domain_base = [('picking_type_id.stock_picking_type', '=', 'receipt')]


        # compute done_total (state = done)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_main_damage_totals(self, **kwargs):

        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()


        domain_base = [('picking_type_id.stock_picking_type', '=', 'main_damage')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result


    @api.model
    def get_damage_main_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()

        domain_base = [('picking_type_id.stock_picking_type', '=', 'damage_main')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_return_main_totals(self, **kwargs):

        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()

        domain_base = [('picking_type_id.stock_picking_type', '=', 'return_main')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_delivery_orders_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()
        domain_base = [('picking_type_id.stock_picking_type', '=', 'return')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_good_return_damage_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()
        domain_base = [('picking_type_id.stock_picking_type', '=', 'damage')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_PoS_Orders_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()
        domain_base = [('picking_type_id.stock_picking_type', '=', 'pos_order')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_manufacturing_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()
        domain_base = [('picking_type_id.stock_picking_type', '=', 'manufacturing')]

        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result

    @api.model
    def get_pos_exchange_totals(self, **kwargs):
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        Move = self.env['stock.move'].sudo()


        domain_base = [('picking_type_id.stock_picking_type', '=', 'exchange')]


        # compute done_total (state = done)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'done')], ['quantity:sum'], [])
            done_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'done')])
            done_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        # compute ready_total (state = assigned)
        try:
            g = Move.read_group(domain_base + [('state', '=', 'assigned')], ['quantity:sum'], [])
            ready_total = float(g[0].get('quantity') or 0.0) if g else 0.0
        except Exception:
            moves = Move.search(domain_base + [('state', '=', 'assigned')])
            ready_total = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)

        result['done'] = float(done_total)
        result['ready'] = float(ready_total)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        return result
