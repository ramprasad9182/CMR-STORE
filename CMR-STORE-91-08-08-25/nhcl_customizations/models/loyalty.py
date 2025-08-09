from odoo import fields, models, _ , api
from datetime import date
from collections import defaultdict


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
            if record.date_from and record.date_to:
                record.is_active = record.date_from <= today <= record.date_to
            else:
                record.is_active = False

    @api.model
    def get_total_promo(self):
        promotions = self.search_read(
            [('is_active', '=', True)],
            ['id', 'name']
        )
        promo_map = {}
        for promo in promotions:
            if promo['id'] not in promo_map:
                promo_map[promo['id']] = promo['name']

        promotion_list = [{"id": "All", "name": "All Promotions"}]
        promotion_list += [{"id": id_, "name": name} for id_, name in promo_map.items()]

        return {
            'promotions': promotions,
            'promotion_list': promotion_list
        }

    @api.model
    def get_category_summary_from_active_promotions(self):
        programs = self.search([('is_active', '=', True)])
        category_map = defaultdict(lambda: {
            'category_name': '',
            'promotion_count': 0,
            'total_serials': 0,
            'sold_serials': 0,
            'promotion_ids': set(),
            'serial_names': []
        })

        for promo in programs:
            for rule in promo.rule_ids:
                category = rule.product_category_id
                if not category:
                    continue

                # Get top-level parent category
                top_category = category
                while top_category.parent_id:
                    top_category = top_category.parent_id

                cat_id = top_category.id
                entry = category_map[cat_id]
                entry['category_name'] = top_category.name
                entry['promotion_ids'].add(promo.id)

                serials = rule.serial_ids
                entry['total_serials'] += len(serials)
                entry['serial_names'].extend(serials.mapped('name'))

        # Flatten and deduplicate all serial names
        all_serial_names = list(set(
            name for entry in category_map.values() for name in entry['serial_names']
        ))

        # Get sold serials from pos.order.line
        sold_lines = self.env['pos.order.line'].search([
            ('order_id.state', 'in', ['paid', 'done']),
            ('pack_lot_ids.lot_name', 'in', all_serial_names),
        ])
        sold_serial_names = set(sold_lines.mapped('pack_lot_ids.lot_name'))

        # Update sold counts
        for entry in category_map.values():
            sold_count = sum(1 for name in entry['serial_names'] if name in sold_serial_names)
            entry['sold_serials'] = sold_count

        # Prepare final result
        result = []
        for cat_data in category_map.values():
            result.append({
                'category': cat_data['category_name'],
                'promotion_count': len(cat_data['promotion_ids']),
                'total_serials': cat_data['total_serials'],
                'sold_serials': cat_data['sold_serials'],
                'available_serials': cat_data['total_serials'] - cat_data['sold_serials'],
            })

        return result




class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.model
    def get_parent_product(self):
        parent_product = self.search_read([('parent_id', '=', False)], ['id', 'name'])


        parent_map = {}
        for parent in parent_product:
            if parent['id'] not in parent_map:
                parent_map[parent['id']] = parent['name']

        parent_list = [{"id": "All", "name": "All Categories"}]
        parent_list += [{"id": id_, "name": name} for id_, name in parent_map.items()]

        return {
            'parent_product': parent_product,
            'parent_list': parent_list
        }