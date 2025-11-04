from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    """Inherited product.template class to add fields and functions"""
    _inherit = 'product.template'

    nhcl_product_type = fields.Selection([('unbranded', 'Un-Branded'), ('branded', 'Branded'),('others', 'Others')],
                                         string='Brand Type')
    nhcl_type = fields.Selection(
        [('advertisement', 'Advertisement'), ('ho_operation', 'HO Operation'), ('others', 'Others')],
        string='Article Type', default='ho_operation')
    category_abbr = fields.Char(string='Prefix', store=True, )
    product_suffix = fields.Char(string="Suffix", copy=False, tracking=True)
    max_number = fields.Integer(string='Max')
    serial_no = fields.Char(string="Serial No")
    product_description = fields.Html(string="Product Description")
    web_product = fields.Char(string="Website  Product Name")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)
    segment = fields.Selection([('apparel','Apparel'), ('non_apparel','Non Apparel'), ('others','Others')], string="Segment", copy=False, tracking=True)
    item_type = fields.Selection([('inventory', 'Inventory'), ('non_inventory', 'Non Inventory')], string="Item Type", default='inventory',
                                 copy=False, tracking=True)

    @api.depends('categ_id')
    def _compute_category_abbr(self):
        for product in self:
            if product.categ_id:
                product.category_abbr = self._get_category_abbr(product.categ_id.display_name)
            else:
                product.category_abbr = False

    def _get_category_abbr(self, phrase):
        # Split the phrase by '/' and take the first part
        first_segment = phrase.split('/')[0].strip()
        first_segment = first_segment.replace('-', ' ')
        words = first_segment.split()
        if len(words) == 1:
            return words[0][0]
        # Otherwise, get the first letter of each word and combine them
        initials = ''.join(word[0] for word in words if word)
        return initials

    @api.onchange('categ_id')
    def creating_product_name_from_categ(self):
        if self.categ_id and self.nhcl_type == 'ho_operation':
            display_name_modified = self.categ_id.display_name.replace(' / ', '-')
            self.name = display_name_modified


class ProductCategory(models.Model):
    _inherit = 'product.category'

    max_num = fields.Integer(string="Max Number")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)


    @api.model
    def create(self, vals):
        if 'parenr_id' in vals and vals['parent_id'] != False:
            existing_product = self.env['product.category'].search([('name', '=', vals['name']), ('parent_id', '=', vals['parent_id'])])
            if existing_product:
                return False
        elif 'parenr_id' in vals and vals['parent_id'] == False:
            existing_parent = self.env['product.category'].search([('name', '=', vals['name'])])
            if existing_parent:
                return False
        else:
            return super(ProductCategory, self).create(vals)

class ProductProduct(models.Model):
    _inherit = "product.product"

    category_abbr = fields.Char(string='Prefix', store=True)
    product_suffix = fields.Char(string="Suffix", copy=False, tracking=True)
    max_number = fields.Integer(string='Max')
    serial_no = fields.Char(string="Serial No")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)
    nhcl_display_name = fields.Char(string="Nhcl Display Name")


    @api.model
    def create(self, vals):
        res = super(ProductProduct, self).create(vals)
        res._get_nhcl_display_name()
        return res

    def _get_nhcl_display_name(self):
        for rec in self:
            if rec.default_code:
                product_attribute_name = len(rec.default_code)
                rec.nhcl_display_name = rec.display_name[product_attribute_name+3:]
            else:
                rec.nhcl_display_name = rec.display_name

    # @api.depends('name', 'default_code', 'product_tmpl_id')
    # @api.depends_context('display_default_code', 'seller_id', 'company_id', 'partner_id', 'use_partner_name')
    # def _compute_display_name(self):
    #     for rec in self:
    #         super(ProductProduct, self)._compute_display_name()
    #         rec._get_nhcl_display_name()


class ProductAttributeValue(models.Model):
    _inherit = "product.attribute.value"
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)

    @api.depends("name")
    def _compute_display_name(self):
        super()._compute_display_name()
        for i in self:
            i.display_name = f"{i.name}"


class ProductAttribute(models.Model):
    _inherit = "product.attribute"

    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)


class ProductAging(models.Model):
    _name = 'product.aging'

    product_aging_ids = fields.One2many('product.aging.line','product_aging_id', string="Product Aging")
    name = fields.Char(string="Prefix Name")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)

class ProductAgingLine(models.Model):
    _name = 'product.aging.line'

    product_aging_id = fields.Many2one('product.aging', string="Aging")
    name = fields.Char(string="Name")
    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)



class ProductTemplateAttributeValue(models.Model):
    _inherit = "product.template.attribute.value"

    attribute_name = fields.Char(
        related="attribute_line_id.attribute_id.name",
        store=True
    )

    _order = "attribute_name"


