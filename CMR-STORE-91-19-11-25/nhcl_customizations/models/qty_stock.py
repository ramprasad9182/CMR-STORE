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
        """
        Return dict {'done': float, 'ready': float, 'done_display': str, 'ready_display': str}
        using stock.move.quantity as the source for both states.
        - done: sum of move.quantity where picking.state == 'done' and picking_type = Receipts
        - ready: sum of move.quantity where move.state == 'assigned' and picking_type = Receipts
        """
        name = 'Receipts'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}

        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()

        # find the picking type (exact match, fallback to ilike)
        pt = PickingType.search([('name', '=', name)], limit=1)
        if not pt:
            pt = PickingType.search([('name', 'ilike', name)], limit=1)
        if not pt:
            _logger.warning("get_receipts_totals: no picking.type found with name '%s'", name)
            return result

        pt_id = pt.id
        _logger.info("get_receipts_totals: using picking.type id=%s name=%s", pt_id, pt.name)

        # 1) DONE: try DB aggregation on stock.move.quantity for pickings in state 'done'
        done_total = 0.0
        try:
            g_done = Move.read_group(
                [('picking_type_id', '=', pt_id), ('state', '=', 'done')],
                ['quantity:sum'],
                []
            )
            _logger.debug("get_receipts_totals: raw DONE group (attempt): %s", g_done)
            if g_done and isinstance(g_done, list) and len(g_done) >= 1:
                done_total = float(g_done[0].get('quantity') or 0.0)
        except Exception as e:
            _logger.warning("get_receipts_totals: read_group on quantity failed for DONE, falling back to python sum. Error: %s", e)
            try:
                moves = Move.search([('picking_type_id', '=', pt_id), ('state', '=', 'done')])
                s = 0.0
                for m in moves:
                    try:
                        s += float(m.quantity or 0.0)
                    except Exception:
                        s += float(getattr(m, 'quantity', 0.0) or 0.0)
                done_total = s
                _logger.debug("get_receipts_totals: done_total from Python loop = %s (count %s)", done_total, len(moves))
            except Exception as e2:
                _logger.exception("get_receipts_totals: fallback python sum for DONE failed: %s", e2)
                done_total = 0.0

        # 2) READY: aggregate stock.move.quantity for moves in 'assigned'
        ready_total = 0.0
        try:
            g_ready = Move.read_group(
                [('picking_type_id', '=', pt_id), ('state', '=', 'assigned')],
                ['quantity:sum'],
                []
            )
            _logger.debug("get_receipts_totals: raw READY group (attempt): %s", g_ready)
            if g_ready and isinstance(g_ready, list) and len(g_ready) >= 1:
                ready_total = float(g_ready[0].get('quantity') or 0.0)
        except Exception as e:
            _logger.warning("get_receipts_totals: read_group on quantity failed for READY, falling back to python sum. Error: %s", e)
            try:
                moves = Move.search([('picking_type_id', '=', pt_id), ('state', '=', 'assigned')])
                s = 0.0
                for m in moves:
                    try:
                        s += float(m.quantity or 0.0)
                    except Exception:
                        s += float(getattr(m, 'quantity', 0.0) or 0.0)
                ready_total = s
                _logger.debug("get_receipts_totals: ready_total from Python loop = %s (count %s)", ready_total, len(moves))
            except Exception as e2:
                _logger.exception("get_receipts_totals: fallback python sum for READY failed: %s", e2)
                ready_total = 0.0

        # fill numeric values and formatted display
        result['done'] = float(done_total or 0.0)
        result['ready'] = float(ready_total or 0.0)
        result['done_display'] = self._format_number(result['done'])
        result['ready_display'] = self._format_number(result['ready'])

        _logger.info("get_receipts_totals: final result %s", result)
        return result

    @api.model
    def get_internal_transfers_totals(self, **kwargs):
        name = 'Internal Transfers'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name', '=', name)], limit=1) or PickingType.search([('name', 'ilike', name)], limit=1)
        if not pt:
            _logger.warning("get_internal_transfers_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_internal_transfers_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        # DONE
        done_total = 0.0
        try:
            g_done = Move.read_group([('picking_type_id', '=', pt_id), ('state', '=', 'done')], ['quantity:sum'], [])
            if g_done: done_total = float(g_done[0].get('quantity') or 0.0)
        except Exception as e:
            _logger.warning("get_internal_transfers_totals: read_group failed for DONE, falling back. Error: %s", e)
            try:
                moves = Move.search([('picking_type_id', '=', pt_id), ('state', '=', 'done')])
                s = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)
                done_total = s
            except Exception as e2:
                _logger.exception("get_internal_transfers_totals: fallback failed: %s", e2); done_total = 0.0
        # READY
        ready_total = 0.0
        try:
            g_ready = Move.read_group([('picking_type_id', '=', pt_id), ('state', '=', 'assigned')], ['quantity:sum'], [])
            if g_ready: ready_total = float(g_ready[0].get('quantity') or 0.0)
        except Exception as e:
            _logger.warning("get_internal_transfers_totals: read_group failed for READY, falling back. Error: %s", e)
            try:
                moves = Move.search([('picking_type_id', '=', pt_id), ('state', '=', 'assigned')])
                s = sum(float(getattr(m, 'quantity', 0.0) or 0.0) for m in moves)
                ready_total = s
            except Exception as e2:
                _logger.exception("get_internal_transfers_totals: fallback failed: %s", e2); ready_total = 0.0
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_internal_transfers_totals: final result %s", result)
        return result


    @api.model
    def get_delivery_orders_totals(self, **kwargs):
        name = 'Delivery Orders'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name', '=', name)], limit=1) or PickingType.search([('name', 'ilike', name)], limit=1)
        if not pt:
            _logger.warning("get_delivery_orders_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_delivery_orders_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            if g_done: done_total = float(g_done[0].get('quantity') or 0.0)
            else: done_total = 0.0
        except Exception as e:
            _logger.warning("get_delivery_orders_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            if g_ready: ready_total = float(g_ready[0].get('quantity') or 0.0)
            else: ready_total = 0.0
        except Exception as e:
            _logger.warning("get_delivery_orders_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_delivery_orders_totals: final result %s", result)
        return result


    @api.model
    def get_pos_orders_totals(self, **kwargs):
        name = 'PoS Orders'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_pos_orders_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_pos_orders_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_pos_orders_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_pos_orders_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_pos_orders_totals: final result %s", result)
        return result


    @api.model
    def get_manufacturing_totals(self, **kwargs):
        name = 'Manufacturing'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_manufacturing_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_manufacturing_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_manufacturing_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_manufacturing_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_manufacturing_totals: final result %s", result)
        return result


    @api.model
    def get_resupply_subcontractor_totals(self, **kwargs):
        name = 'Resupply Subcontractor'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_resupply_subcontractor_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_resupply_subcontractor_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_resupply_subcontractor_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_resupply_subcontractor_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_resupply_subcontractor_totals: final result %s", result)
        return result


    @api.model
    def get_dropship_totals(self, **kwargs):
        name = 'Dropship'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_dropship_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_dropship_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_dropship_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_dropship_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_dropship_totals: final result %s", result)
        return result


    @api.model
    def get_dropship_subcontractor_totals(self, **kwargs):
        name = 'Dropship Subcontractor'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_dropship_subcontractor_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_dropship_subcontractor_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_dropship_subcontractor_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_dropship_subcontractor_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_dropship_subcontractor_totals: final result %s", result)
        return result


    @api.model
    def get_vendor_return_totals(self, **kwargs):
        name = 'Vendor Return'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_vendor_return_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_vendor_return_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_vendor_return_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_vendor_return_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_vendor_return_totals: final result %s", result)
        return result


    @api.model
    def get_damage_receipts_totals(self, **kwargs):
        name = 'Damage-Receipts'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_damage_receipts_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_damage_receipts_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_damage_receipts_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_damage_receipts_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_damage_receipts_totals: final result %s", result)
        return result


    @api.model
    def get_product_exchange_pos_totals(self, **kwargs):
        name = 'Product Exchange - POS'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_product_exchange_pos_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_product_exchange_pos_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_product_exchange_pos_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_product_exchange_pos_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_product_exchange_pos_totals: final result %s", result)
        return result


    @api.model
    def get_receipts_damage_totals(self, **kwargs):
        name = 'Receipts-Damage'
        result = {'done': 0.0, 'ready': 0.0, 'done_display': '0', 'ready_display': '0'}
        PickingType = self.env['stock.picking.type'].sudo()
        Move = self.env['stock.move'].sudo()
        pt = PickingType.search([('name','=',name)], limit=1) or PickingType.search([('name','ilike',name)], limit=1)
        if not pt:
            _logger.warning("get_receipts_damage_totals: no picking.type found with name '%s'", name); return result
        pt_id = pt.id; _logger.info("get_receipts_damage_totals: using picking.type id=%s name=%s", pt_id, pt.name)
        try:
            g_done = Move.read_group([('picking_type_id','=',pt_id),('state','=','done')], ['quantity:sum'], [])
            done_total = float(g_done[0].get('quantity') or 0.0) if g_done else 0.0
        except Exception as e:
            _logger.warning("get_receipts_damage_totals: read_group failed for DONE, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','done')]); done_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        try:
            g_ready = Move.read_group([('picking_type_id','=',pt_id),('state','=','assigned')], ['quantity:sum'], [])
            ready_total = float(g_ready[0].get('quantity') or 0.0) if g_ready else 0.0
        except Exception as e:
            _logger.warning("get_receipts_damage_totals: read_group failed for READY, falling back. Error: %s", e)
            moves = Move.search([('picking_type_id','=',pt_id),('state','=','assigned')]); ready_total = sum(float(getattr(m,'quantity',0.0) or 0.0) for m in moves)
        result['done']=float(done_total); result['ready']=float(ready_total)
        result['done_display']=self._format_number(result['done']); result['ready_display']=self._format_number(result['ready'])
        _logger.info("get_receipts_damage_totals: final result %s", result)
        return result

