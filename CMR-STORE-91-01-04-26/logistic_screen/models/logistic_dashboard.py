# -*- coding: utf-8 -*-
from odoo import models, api, fields,_
from dateutil.relativedelta import relativedelta
from datetime import datetime, time
from collections import Counter
import re
import logging
_logger = logging.getLogger(__name__)


class LogisticScreen(models.Model):
    _inherit = 'logistic.screen.data'

    @api.model
    def get_delivery_period_counts(self, **kwargs):
        Delivery = self.env['delivery.check'].sudo()

        # Scope to the correct "screen"
        base = [('delivery_entry_types', '=', 'manual')]

        # Date anchors
        today = fields.Date.context_today(self)
        week_start = today - relativedelta(days=6)  # last 7 days inclusive
        month_start = today - relativedelta(days=29)  # last 30 days inclusive

        # Handle Date vs Datetime fields cleanly
        ld_field = Delivery._fields.get('logistic_date')
        is_datetime = bool(ld_field and ld_field.type == 'datetime')

        def range_domain(start_date, end_date):
            """Inclusive start/end filter for logistic_date."""
            if is_datetime:
                start_dt = datetime.combine(start_date, time.min)
                end_dt = datetime.combine(end_date, time.max)
                return [
                    ('logistic_date', '>=', fields.Datetime.to_string(start_dt)),
                    ('logistic_date', '<=', fields.Datetime.to_string(end_dt)),
                ]
            else:
                return [
                    ('logistic_date', '>=', start_date),
                    ('logistic_date', '<=', end_date),
                ]

        def cnt(state_domain, *, exact=None, start=None, end=None):
            dom = list(base) + list(state_domain)
            if exact is not None:
                dom += range_domain(exact, exact)
            else:
                dom += range_domain(start, end)
            return Delivery.search_count(dom)

        # States
        draft_domain = [('state', '=', 'draft')]
        done_domain = [('state', 'in', ['delivered', 'delivery', 'done'])]

        # Draft buckets
        draft_today = cnt(draft_domain, exact=today)
        draft_week = cnt(draft_domain, start=week_start, end=today)
        draft_month = cnt(draft_domain, start=month_start, end=today)

        # Done buckets
        done_today = cnt(done_domain, exact=today)
        done_week = cnt(done_domain, start=week_start, end=today)
        done_month = cnt(done_domain, start=month_start, end=today)

        return {
            "draft": {"today": draft_today, "week": draft_week, "month": draft_month},
            "done": {"today": done_today, "week": done_week, "month": done_month},
        }

    @api.model
    def get_partial_delivered_count(self, **kwargs):

        Delivery = self.env['delivery.check']
        count = Delivery.search_count([('delivery_entry_types', '=', 'manual'),
                                       ("overall_remaining_bales", ">=", 1),
                                       ('state', '=', 'delivery')])
        return {"partial_delivered": int(count)}

    @api.model
    def get_status_transit_delayed(self, **kwargs):

        today = fields.Date.context_today(self)
        Lr = self.env['delivery.check']
        in_transit = Lr.search_count([('delivery_entry_types', '=', 'manual'), ('state', '=', 'draft')])
        delayed = Lr.search_count(
            [('delivery_entry_types', '=', 'manual'), ('state', '=', 'done'), ('logistic_date', '>', today)])
        canceled = Lr.search_count([('delivery_entry_types', '=', 'manual'), ('state', '=', 'cancel')])
        return {"in_transit": int(in_transit), "delayed": int(delayed), "canceled": int(canceled)}

    @api.model
    def get_status_delivered(self, **kwargs):

        Delivery = self.env['delivery.check']
        count = [('state', '=', 'delivery')]
        delivered = Delivery.search_count([('delivery_entry_types', '=', 'manual')] + count)
        return {"delivered": int(delivered)}

    @api.model
    def get_top5_products_delivered(self, **kwargs):
        Delivery = self.env['delivery.check'].sudo()

        # Domain: manual OR state in ('delivered','delivery')
        domain = ['|', ('delivery_entry_types', '=', 'manual'), ('state', '=', 'delivered')]

        # Optional date filters
        date_from = (kwargs or {}).get('date_from')
        date_to = (kwargs or {}).get('date_to')
        if date_from:
            domain += [('logistic_date', '>=', date_from)]
        if date_to:
            domain += [('logistic_date', '<=', date_to)]

        ids = Delivery.search(domain).ids
        if not ids:
            return {"total": 0, "max": 0, "items": []}

        counts = Counter()
        BATCH = 1000

        for i in range(0, len(ids), BATCH):
            rows = Delivery.browse(ids[i:i + BATCH]).read(['item_details'])
            for r in rows:
                s = r.get('item_details') or ''
                if not isinstance(s, str):
                    try:
                        s = str(s)
                    except Exception:
                        s = ''

                # substring after first closing bracket ']' if present
                rb = s.find(']')
                after = s[rb + 1:].strip() if rb != -1 else s.strip()
                after = re.sub(r'\s+', ' ', after)  # normalize spaces

                # split on hyphen, trimming spaces around segments
                parts = [p.strip() for p in re.split(r'\s*-\s*', after) if p.strip() != ""]

                cat = ""
                # If first segment is exactly one alphabetical character, return the FIRST TWO segments joined by '-'
                # e.g. parts = ['H','GAGRAS','ETHNIC ...'] -> cat = 'H-GAGRAS'
                if parts and len(parts[0]) == 1 and parts[0].isalpha():
                    if len(parts) >= 2:
                        cat = f"{parts[0].strip()}-{parts[1].strip()}"
                    else:
                        # no second segment: fallback to full 'after' text (or mark uncategorized)
                        cat = after or ""
                else:
                    # Default behavior: take text after ']' up to first '-' (i.e., parts[0]) if exists
                    if parts:
                        cat = parts[0].strip()
                    else:
                        cat = after

                # Final fallback
                if not cat:
                    cat = _("Uncategorized")

                counts[cat] += 1

        top = counts.most_common(5)
        items = []
        total = 0
        for cat, cnt in top:
            items.append({
                "key": cat,
                "product_name": cat,
                "parent_category": cat,
                "count": int(cnt),
            })
            total += int(cnt)

        max_count = max((it["count"] for it in items), default=0)
        payload = {"total": total, "max": max_count, "items": items}

        _logger.debug("Top5 delivered categories (two-segment single-letter rule): %s", payload)
        return payload

    @api.model
    def get_open_parcel_state_counts(self, **kwargs):
        Parcel = self.env['open.parcel'].sudo()
        base = []
        draft = Parcel.search_count(base + [('state', '=', 'draft')])
        done = Parcel.search_count(base + [('state', '=', 'done')])
        return {
            "draft": int(draft),
            "done": int(done),
        }

    @api.model
    def get_divisionwise_bale_totals(self, top_n=5, **kwargs):
        """
        Returns:
          [
            {"division_name": "H-GAGRAS", "parcel_bale_total": 123.0},
            ...
          ]
        Also returns (as additional keys):
          - delivery_ids: list of delivery.check ids used for aggregation
          - division_delivery_ids: { division_name: [delivery_id, ...], ... }
        """
        try:
            Parcel = self.env['open.parcel'].sudo()
            parcel_domain = [
                ('state', '=', 'draft'),
                ('parcel_lr_no', '!=', False),
            ]
            parcels = Parcel.search_read(parcel_domain, ['parcel_lr_no', 'parcel_bale'])

            # aggregate bale qty per LR (from parcels)
            lr_bale_map = {}
            for p in parcels:
                lr = str(p.get('parcel_lr_no') or '').strip()
                if not lr:
                    continue
                bale_val = p.get('parcel_bale') or 0
                try:
                    qty = float(bale_val)
                except Exception:
                    qty = 0.0
                lr_bale_map[lr] = lr_bale_map.get(lr, 0.0) + qty

            if not lr_bale_map:
                return {
                    "results": [],
                    "delivery_ids": [],
                    "division_delivery_ids": {},
                }

            lr_list = list(lr_bale_map.keys())

            Delivery = self.env['delivery.check'].sudo()
            deliveries = Delivery.search([('logistic_lr_number', 'in', lr_list)], order='id desc')

            # map LR -> latest delivery id and keep deliveries for later parsing
            lr_to_delivery_id = {}
            delivery_by_lr = {}
            for d in deliveries:
                lr_val = d.logistic_lr_number
                if lr_val is None:
                    continue
                lr_key = str(lr_val).strip()
                if lr_key not in lr_to_delivery_id:
                    lr_to_delivery_id[lr_key] = d.id
                    delivery_by_lr[lr_key] = d

            if not lr_to_delivery_id:
                return {
                    "results": [],
                    "delivery_ids": [],
                    "division_delivery_ids": {},
                }

            # read item_details for those delivery ids (batch)
            delivery_ids = list(set(lr_to_delivery_id.values()))
            BATCH = 1000
            id_to_item = {}
            for i in range(0, len(delivery_ids), BATCH):
                chunk = delivery_ids[i:i + BATCH]
                rows = Delivery.browse(chunk).read(['item_details'])
                for r in rows:
                    did = r.get('id')
                    s = r.get('item_details') or ''
                    if not isinstance(s, str):
                        try:
                            s = str(s)
                        except Exception:
                            s = ''
                    id_to_item[did] = s or ''

            # For each delivery id determine the division_name using same parsing logic
            def parse_division_from_item(s):
                s = (s or '').strip()
                if not s:
                    return _('Uncategorized')
                rb = s.find(']')
                after = s[rb + 1:].strip() if rb != -1 else s.strip()
                after = re.sub(r'\s+', ' ', after)
                parts = [p.strip() for p in re.split(r'\s*-\s*', after) if p.strip()]
                if parts and len(parts[0]) == 1 and parts[0].isalpha():
                    if len(parts) >= 2:
                        return f"{parts[0]}-{parts[1]}"
                    else:
                        return after or _('Uncategorized')
                else:
                    return parts[0] if parts else after or _('Uncategorized')

            # build mapping: division_name -> list of delivery_ids and aggregate bale totals
            division_delivery_ids = {}
            division_totals = Counter()

            for lr, bale_qty in lr_bale_map.items():
                delivery_id = lr_to_delivery_id.get(lr)
                if not delivery_id:
                    continue
                item_text = id_to_item.get(delivery_id, '') or ''
                division_name = parse_division_from_item(item_text)
                division_delivery_ids.setdefault(division_name, []).append(delivery_id)
                division_totals[division_name] += bale_qty

            if not division_totals:
                return {
                    "results": [],
                    "delivery_ids": delivery_ids,
                    "division_delivery_ids": division_delivery_ids,
                }

            results = [
                {"division_name": name, "parcel_bale_total": round(total, 2)}
                for name, total in division_totals.items()
            ]
            results.sort(key=lambda x: x['parcel_bale_total'], reverse=True)
            top = results[:int(top_n)]

            return {
                "results": top,
                "delivery_ids": delivery_ids,
                "division_delivery_ids": division_delivery_ids,
            }

        except Exception as e:
            _logger.exception("Error in get_divisionwise_bale_totals: %s", e)
            return {"results": [], "delivery_ids": [], "division_delivery_ids": {}}