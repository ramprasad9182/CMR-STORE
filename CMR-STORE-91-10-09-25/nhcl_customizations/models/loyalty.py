from odoo import fields, models, _ , api
from datetime import datetime, timedelta, date
from collections import defaultdict
import logging
_logger = logging.getLogger(__name__)


class LoyaltyRule(models.Model):
    _inherit = 'loyalty.rule'

    serial_ids = fields.Many2many('stock.lot', string="Serial No's", copy=False)
    category_1_ids = fields.Many2many('product.attribute.value', 'cat_1', string='Color', copy=False,
                                      domain=[('attribute_id.name', '=', 'Color')])
    category_2_ids = fields.Many2many('product.attribute.value', 'cat_2', string='Fit', copy=False,
                                      domain=[('attribute_id.name', '=', 'Fit')])
    category_3_ids = fields.Many2many('product.attribute.value', 'cat_3', string='Brand', copy=False,
                                      domain=[('attribute_id.name', '=', 'Brand')])
    category_4_ids = fields.Many2many('product.attribute.value', 'cat_4', string='Pattern', copy=False,
                                      domain=[('attribute_id.name', '=', 'Pattern')])
    category_5_ids = fields.Many2many('product.attribute.value', 'cat_5', string='Border Type', copy=False,
                                      domain=[('attribute_id.name', '=', 'Border Type')])
    category_6_ids = fields.Many2many('product.attribute.value', 'cat_6', string='Border Size', copy=False,
                                      domain=[('attribute_id.name', '=', 'Border Size')])
    category_7_ids = fields.Many2many('product.attribute.value', 'cat_7', string='Size', copy=False,
                                      domain=[('attribute_id.name', '=', 'Size')])
    category_8_ids = fields.Many2many('product.attribute.value', 'cat_8', string='Design', copy=False,
                                      domain=[('attribute_id.name', '=', 'Design')])
    description_1_ids = fields.Many2many('product.aging.line',string='Product Ageing', copy=False)

    description_2_ids = fields.Many2many('product.attribute.value', 'des_2', string='Range', copy=False,
                                         domain=[('attribute_id.name', '=', 'Range')])
    description_3_ids = fields.Many2many('product.attribute.value', 'des_3', string='Collection', copy=False,
                                         domain=[('attribute_id.name', '=', 'Collection')])
    description_4_ids = fields.Many2many('product.attribute.value', 'des_4', string='Fabric', copy=False,
                                         domain=[('attribute_id.name', '=', 'Fabric')])
    description_5_ids = fields.Many2many('product.attribute.value', 'des_5', string='Exclusive', copy=False,
                                         domain=[('attribute_id.name', '=', 'Exclusive')])
    description_6_ids = fields.Many2many('product.attribute.value', 'des_6', string='Print', copy=False,
                                         domain=[('attribute_id.name', '=', 'Print')])
    description_7_ids = fields.Many2many('product.attribute.value', 'des_7', string='Days Ageing', copy=False)
    description_8_ids = fields.Many2many('product.attribute.value', 'des_8', string='Description 8', copy=False)
    loyalty_line_id = fields.One2many('loyalty.line', 'loyalty_id', string='Loyalty Lines')
    # range_from = fields.Integer(string='Range From', copy=False)
    # range_to = fields.Integer(string='Range To', copy=False)
    ref_product_ids = fields.Many2many('product.product', 'ref_product_id',string="Product", copy=False)
    type_filter = fields.Selection([('filter', 'Attribute Filter'), ('serial', 'Serial'),('cart','Cart'),('grc','GRC')], string='Filter Type', copy=False)
    product_category_ids = fields.Many2many('product.category', string='Categories')
    day_ageing_slab = fields.Selection([('1', '0-30'), ('2', '30-60'),
                                        ('3', '60-90'), ('4', '90-120'),
                                        ('5', '120-150'), ('6', '150-180'),
                                        ('7', '180-210'), ('8', '210-240'),
                                        ('9', '240-270'), ('10', '270-300'),
                                        ('11', '300-330'), ('12', '330-360')
                                        ])
    serial_nos = fields.Text(string="Serials")


    def reset_to_filters(self):
        self.ensure_one()
        self.loyalty_line_id.unlink()
        self.category_1_ids = False
        self.category_2_ids = False
        self.category_3_ids = False
        self.category_4_ids = False
        self.category_5_ids = False
        self.category_6_ids = False
        self.category_7_ids = False
        self.category_8_ids = False
        self.description_1_ids = False
        self.description_2_ids = False
        self.description_3_ids = False
        self.description_4_ids = False
        self.description_5_ids = False
        self.description_6_ids = False
        self.description_7_ids = False
        self.description_8_ids = False
        self.serial_ids = False
        self.product_ids = False
        self.product_category_id = False
        self.product_tag_id = False
        # self.range_from = False
        # self.range_to = False
        self.ref_product_ids = False
        self.serial_nos = False
        # self.product_ids = False

    def apply_loyalty_rule(self):
        self.loyalty_line_id.unlink()

        distinct_product_ids = set()
        loyalty_line_vals = []
        matching_lots = self.env['stock.lot']
        if self.type_filter in ['serial','grc','filter']:
            if self.serial_nos:
                serial_list = [s.strip() for s in self.serial_nos.split(',') if s.strip()]
                lots = self.env['stock.lot'].search([('name', 'in', serial_list)])
                self.serial_ids = [(6, 0, lots.ids)]
                matching_lots = self.serial_ids
                for lot in matching_lots:
                    distinct_product_ids.add(lot.product_id.id)
                    loyalty_line_vals.append((0, 0, {
                        'lot_id': lot.id,
                        'product_id': lot.product_id.id
                    }))
        self.update({
            'loyalty_line_id': loyalty_line_vals,
            'product_ids': [(6, 0, list(distinct_product_ids))]
        })
        return matching_lots

    @api.model
    def create(self, vals):
        res = super(LoyaltyRule, self).create(vals)
        if res.type_filter in ['serial','grc','filter']:
            res.apply_loyalty_rule()
        return res


class LoyaltyLine(models.Model):
    _name = 'loyalty.line'

    loyalty_id = fields.Many2one('loyalty.rule',string='Loyalty', copy=False)
    lot_id = fields.Many2one('stock.lot',string='Lot/Serial', copy=False)
    product_id = fields.Many2one('product.product',string='Product', copy=False)


class LoyaltyProgram(models.Model):
    _inherit = "loyalty.program"

    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)
    is_active = fields.Boolean(string='Is Active', compute='_compute_is_active', store=True)
    is_vendor_return = fields.Boolean(string='Vendor Return', copy=False)

    @api.depends('date_from', 'date_to')
    def _compute_is_active(self):
        today = date.today()
        for record in self:
            record.is_active = bool(record.date_from and record.date_to and record.date_from <= today <= record.date_to)

    def cron_update_is_active(self):
        """Cron job to recompute 'is_active' daily"""
        records = self.search([])
        records._compute_is_active()

    @api.model
    def get_total_promo(self):
        # return active promos; leave selection empty by default in UI
        promotions = self.search_read([], ['id', 'name'])
        return {
            'promotions': promotions,  # [{id, name}, ...]
            'promotion_list': []  # empty = no preselected filter
        }

    @api.model
    def search_promotions(self, q="", limit=50):
        domain = [("is_active", "=", True)]
        if q:
            domain.append(("name", "ilike", q))
        recs = self.search(domain, limit=limit, order="name asc")
        return [{"id": r.id, "name": r.name} for r in recs]

    @api.model
    def get_category_summary_from_active_promotions(self, **kwargs):
        """
        kwargs:
          category_ids=[int|dict], promo_ids=[int|dict],
          period_days=int,                           # SOLD window only
          group_by="root"|"parent"|"self" (default "root"),
          company_ids=[int|dict], pos_config_ids=[int|dict]
        """

        # ---------- helpers
        def _to_ids(val):
            out = []
            for x in (val or []):
                if isinstance(x, int):
                    out.append(x)
                elif isinstance(x, str) and x.isdigit():
                    out.append(int(x))
                elif isinstance(x, dict):
                    xid = x.get("id") or x.get("value") or x.get("res_id")
                    if isinstance(xid, int):
                        out.append(xid)
            return out

        def _grouped_cat(cat):
            if not cat:
                return None
            grp = cat
            if group_by == "root":
                while grp.parent_id:
                    grp = grp.parent_id
            elif group_by == "parent":
                grp = grp.parent_id or grp
            return grp

        def _iter_rule_categories(rule):
            cats = set()
            if getattr(rule, "product_category_id", False):
                cats.add(rule.product_category_id)
            if hasattr(rule, "product_category_ids"):
                cats.update(rule.product_category_ids)
            if hasattr(rule, "product_tmpl_ids") and rule.product_tmpl_ids:
                cats.update(rule.product_tmpl_ids.mapped("categ_id"))
            if hasattr(rule, "product_ids") and rule.product_ids:
                cats.update(rule.product_ids.mapped("product_tmpl_id.categ_id"))
            return {c for c in cats if c}

        def _most_specific_target(prod_cat, targeted_set):
            """Return the closest (deepest) targeted ancestor of prod_cat."""
            node = prod_cat
            while node:
                if node in targeted_set:
                    return node
                node = node.parent_id
            return None

        # ---------- parse filters
        filter_cat_ids     = set(_to_ids(kwargs.get("category_ids")))
        filter_promo_ids   = set(_to_ids(kwargs.get("promo_ids")))
        filter_company_ids = set(_to_ids(kwargs.get("company_ids")))
        filter_config_ids  = set(_to_ids(kwargs.get("pos_config_ids")))

        group_by = (kwargs.get("group_by") or "root").lower()

        period_days_raw = kwargs.get("period_days") or 0
        try:
            period_days = int(period_days_raw)
        except Exception:
            period_days = 0

        today    = fields.Date.context_today(self)
        since_dt = fields.Datetime.now() - timedelta(days=period_days) if period_days > 0 else None

        # ---------- STRICT active promotion domain (require BOTH dates; today inside window)
        domain_programs = [
            '&', '&', '&',
                ('active', '=', True),
                ('is_active', '=', True),
                '&', ('date_from', '!=', False), ('date_to', '!=', False),
                '&', ('date_from', '<=', today), ('date_to', '>=', today),
        ]
        if filter_promo_ids:
            domain_programs = ['&'] + domain_programs + [('id', 'in', list(filter_promo_ids))]

        promo_model = self.with_context(active_test=True)
        programs = promo_model.search(domain_programs)
        if not programs:
            _logger.info("Dashboard: No ACTIVE promotions with strict domain=%s", domain_programs)
            return []

        # ---------- promo-aware POS attribution (detect field if present)
        line_model = self.env["pos.order.line"]
        _promo_line_field = None
        for f in ("promotion_id", "promo_id", "program_id", "applied_promotion_id", "promotion_applied_id"):
            if f in line_model._fields:
                _promo_line_field = f
                break

        # ---------- per-(promo, grouped category) working map (BUCKETS)
        promo_cat = defaultdict(lambda: {
            "promotion_id": 0,
            "promotion_name": "",
            "category_id": 0,          # grouped category id (per group_by)
            "category_name": "",
            "serial_names": set(),     # whitelist assigned to THIS bucket (no duplication)
            "cap_total": 0,            # whitelist size OR numeric cap (only when unambiguous)
            "sold_serials": 0,         # to be filled post sales scan
        })
        promo_serial_pool   = defaultdict(set)  # promo_id -> union of whitelist serial names
        promo_targeted_cats = dict()            # promo_id -> set(self-level targeted categories)

        # ---------- build caps & serial pools PER PROMO (bucketized)
        for promo in programs.sudo():
            rules = promo.rule_ids.filtered(lambda r: getattr(r, "active", True))
            if not rules:
                continue

            # self-level targeted categories for this promo (used for "most-specific" mapping)
            targeted_cats = set()
            for rule in rules:
                targeted_cats.update(_iter_rule_categories(rule))
            targeted_cats = {c for c in targeted_cats if c}
            promo_targeted_cats[promo.id] = targeted_cats

            # pre-create empty buckets so categories appear even if zero
            for cat in targeted_cats:
                grp = _grouped_cat(cat)
                if not grp:
                    continue
                if filter_cat_ids and grp.id not in filter_cat_ids:
                    continue
                key = (promo.id, grp.id)
                e = promo_cat[key]
                e["promotion_id"]   = promo.id
                e["promotion_name"] = getattr(promo, "name", f"Promotion {promo.id}") or f"Promotion {promo.id}"
                e["category_id"]    = grp.id
                e["category_name"]  = grp.name or "Uncategorized"

            # now distribute serials/caps into exactly ONE bucket each
            for rule in rules:
                rule_cats = _iter_rule_categories(rule)
                if not rule_cats:
                    continue

                serials = getattr(rule, "serial_ids", self.env["stock.lot"].browse())
                if serials:
                    # SERIAL WHITELIST: map each lot to the most-specific targeted category, then group
                    for lot in serials:
                        lot_name = lot.name or ""
                        if not lot_name:
                            continue
                        prod = getattr(lot, "product_id", False)
                        prod_cat = prod.product_tmpl_id.categ_id if prod else False
                        if not prod_cat:
                            continue
                        target_self = _most_specific_target(prod_cat, targeted_cats)
                        if not target_self:
                            continue
                        grp = _grouped_cat(target_self)
                        if not grp or (filter_cat_ids and grp.id not in filter_cat_ids):
                            continue
                        key = (promo.id, grp.id)
                        e = promo_cat[key]
                        e["serial_names"].add(lot_name)     # lot belongs to ONE bucket only
                        promo_serial_pool[promo.id].add(lot_name)
                else:
                    # NUMERIC CAP: only allocate when rule targets exactly ONE category (avoid duplication)
                    cap_numeric = 0
                    for fname in ("qty_cap", "quantity_cap", "qty", "quantity", "limit_qty"):
                        if fname in rule._fields:
                            try:
                                cap_numeric = max(cap_numeric, int(getattr(rule, fname) or 0))
                            except Exception:
                                pass
                    if cap_numeric and len(rule_cats) == 1:
                        only_cat = next(iter(rule_cats))
                        grp = _grouped_cat(only_cat)
                        if grp and (not filter_cat_ids or grp.id in filter_cat_ids):
                            key = (promo.id, grp.id)
                            e = promo_cat[key]
                            e["cap_total"] += int(cap_numeric)
                    elif cap_numeric and len(rule_cats) > 1:
                        _logger.debug(
                            "Promo %s rule %s numeric cap with multiple categories; "
                            "skipping cap allocation to avoid double counting.",
                            promo.id, rule.id
                        )

        if not promo_cat:
            _logger.info("Dashboard: No rows after active promo/rule filtering.")
            return []

        # finalize totals per bucket (whitelist size has priority)
        for e in promo_cat.values():
            if e["serial_names"]:
                e["cap_total"] = len(e["serial_names"])
            else:
                e["cap_total"] = int(e["cap_total"] or 0)

        # ---------- SOLD scan per promo (net of returns, within scope; period applies ONLY here)
        for promo in programs.sudo():
            domain = [
                ("order_id.state", "in", ["paid", "done"]),
                ("pack_lot_ids.lot_name", "!=", False),
            ]
            if since_dt:
                domain.append(("order_id.date_order", ">=", fields.Datetime.to_string(since_dt)))
            if filter_company_ids:
                domain.append(("order_id.company_id", "in", list(filter_company_ids)))
            if filter_config_ids:
                domain.append(("order_id.config_id", "in", list(filter_config_ids)))

            targeted_cats = promo_targeted_cats.get(promo.id, set()) or set()

            # Prefer explicit promo link; else fall back to the promo's whitelist pool
            if _promo_line_field:
                domain.append((_promo_line_field, "=", promo.id))
                use_fallback_pool = False
                fallback_pool = set()
            else:
                fallback_pool = promo_serial_pool.get(promo.id, set())
                if fallback_pool:
                    domain.append(("pack_lot_ids.lot_name", "in", list(fallback_pool)))
                    use_fallback_pool = True
                else:
                    continue  # cannot attribute sales to this promo

            sold_lines = line_model.sudo().search(domain)

            # Net events per serial, bucketed by grouped category chosen via most-specific targeted cat
            events = defaultdict(list)  # lot_name -> list[(date, sign, grouped_cat_id)]
            for ln in sold_lines:
                qty = ln.qty or 0.0
                sign = 1 if qty > 0 else (-1 if qty < 0 else 0)
                if not sign:
                    continue
                prod_cat = ln.product_id.product_tmpl_id.categ_id if ln.product_id else False
                target_self = _most_specific_target(prod_cat, targeted_cats) if prod_cat else None
                grp = _grouped_cat(target_self) if target_self else None
                grp_id = grp.id if grp else None

                for pl in ln.pack_lot_ids:
                    name = pl.lot_name or ""
                    if not name:
                        continue
                    if use_fallback_pool and fallback_pool and name not in fallback_pool:
                        continue
                    if not grp_id:
                        continue
                    events[name].append((ln.order_id.date_order, sign, grp_id))

            sold_net_serials = set()
            sold_net_by_group = defaultdict(set)  # grouped_cat_id -> set(lot_name)
            for lot_name, evs in events.items():
                evs.sort(key=lambda t: t[0] or fields.Datetime.now())
                bal = 0
                last_pos_grp = None
                for (dt, sgn, cat_id) in evs:
                    if sgn > 0:
                        bal += 1
                        if cat_id:
                            last_pos_grp = cat_id
                    elif sgn < 0:
                        bal -= 1
                if bal > 0:
                    sold_net_serials.add(lot_name)
                    if last_pos_grp:
                        sold_net_by_group[last_pos_grp].add(lot_name)

            # write sold counts back into this promo's buckets
            for (promo_id, cat_id), e in list(promo_cat.items()):
                if promo_id != promo.id:
                    continue
                if e["serial_names"]:
                    e["sold_serials"] = sum(1 for n in e["serial_names"] if n in sold_net_serials)
                else:
                    e["sold_serials"] = len(sold_net_by_group.get(cat_id, set()))

        # ---------- roll up per grouped category (active promos only)
        final_by_cat = defaultdict(lambda: {
            "category_id": 0,
            "category_name": "",
            "promotion_ids": set(),
            "total_serials": 0,
            "sold_serials": 0,
        })

        for (promo_id, cat_id), e in promo_cat.items():
            if not cat_id:
                continue
            if filter_cat_ids and cat_id not in filter_cat_ids:
                continue
            total = int(e["cap_total"] or 0)
            sold  = int(e["sold_serials"] or 0)
            row = final_by_cat[cat_id]
            row["category_id"] = cat_id
            row["category_name"] = e["category_name"]
            if total > 0:
                row["promotion_ids"].add(promo_id)     # counts only promos contributing capacity
            row["total_serials"] += total
            row["sold_serials"]  += min(sold, total)

        result = []
        for cat_id, row in final_by_cat.items():
            total = int(row["total_serials"])
            sold  = min(int(row["sold_serials"]), total)
            result.append({
                "category_id": row["category_id"],
                "category_name": row["category_name"],
                "promotion_count": len(row["promotion_ids"]),
                "promotion_ids": sorted(row["promotion_ids"]),
                "total_serials": total,
                "sold_serials": sold,
                "available_serials": max(0, total - sold),
            })

        result.sort(key=lambda r: (r["category_name"] or "").lower())
        _logger.info("Dashboard: Active promotions=%s (strict domain applied)", programs.ids)
        return result


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def get_parent_product(self):
        rows = self.search_read([('parent_id', '=', False)], ['id', 'name'], order='name asc')
        return {
            'parent_product': rows,  # [{id,name}]
            'parent_list': []  # empty = no preselected filter
        }

    @api.model
    def search_top_categories(self, q="", limit=50):
        domain = [("parent_id", "=", False)]
        if q:
            domain.append(("name", "ilike", q))
        recs = self.search(domain, limit=limit, order="name asc")
        return [{"id": r.id, "name": r.name} for r in recs]
