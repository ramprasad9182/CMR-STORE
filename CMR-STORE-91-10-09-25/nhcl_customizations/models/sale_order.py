from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import re

class sale_order(models.Model):
    _inherit = 'sale.order'

    so_type = fields.Selection(
        [('advertisement', 'Advertisement'), ('ho_operation', 'HO Operation'), ('inter_state','Inter State'), ('intra_state','Intra State'), ('others', 'Others')],
        string='SO Type', required=True, tracking=True)
    dummy_so_type = fields.Selection(
        [('advertisement', 'Advertisement'), ('ho_operation', 'HO Operation'),
         ('others', 'Others')], string='Dummy SO Type', compute='_compute_nhcl_so_type')
    barcode_scanned = fields.Char(string="Scan Barcode")
    picking_document = fields.Many2one('stock.picking', string="Document", copy=False)
    operation_type = fields.Selection([('scan','Scan'), ('import','Import'), ('document','Document')], string="Operation Type", tracking=True, copy=False)
    transpoter_id = fields.Many2one('dev.transport.details',string='Transport by')
    entered_qty = fields.Float(string='Lot Qty', copy=False)

    def get_so_type(self):
        if self.partner_id and self.env.company.state_id:
            if self.partner_id.state_id.id == self.env.company.state_id.id:
                self.so_type = 'intra_state'
            else:
                self.so_type = 'inter_state'
        else:
            self.so_type = ''

    # Picking Document Lines Creation
    def get_picking_lines(self):
        # Gather lot_id + sale_serial_type combinations already used in other sale orders
        used_lots = self.env['sale.order.line'].sudo().search([
            ('order_id', '!=', self.id),
            ('lot_ids', '!=', False),
            ('sale_serial_type', '!=', False)
        ])
        used_combinations = set()
        for line in used_lots:
            for lot in line.lot_ids:
                used_combinations.add((lot.name, line.sale_serial_type))
        self.order_line.unlink()
        existing_order = self.env['sale.order'].sudo().search(
            [('picking_document', '=', self.picking_document.id), ('id', '!=', self.id)], limit=1)
        if existing_order:
            raise ValidationError(
                f"This picking document '{self.picking_document.name}' is already used in Sale Order '{existing_order.name}'.")

        picking = self.env['stock.picking'].sudo().search([('name', '=', self.picking_document.name)])

        for line in picking.move_line_ids_without_package:
            if not line.product_id:
                raise ValidationError(f"No Products Found in '{picking.name}'.")

            if not line.lot_id:
                continue
            if not line.lot_id.product_qty > 0:
                continue
            # Skip if this (lot.name + serial_type) is already used elsewhere
            if (line.lot_id.name, line.lot_id.serial_type) in used_combinations:
                continue
            lot_ids = [(6, 0, line.lot_id.ids)]
            barcodes = line.lot_id.mapped('ref')
            barcodes = [barcode for barcode in barcodes if barcode]
            branded_barcode_value = ', '.join(set(barcodes))
            self.order_line.create({
                'order_id': self.id,
                'product_id': line.product_id.id,
                'family_id': line.product_id.categ_id.parent_id.parent_id.parent_id.id,
                'category_id': line.product_id.categ_id.parent_id.parent_id.id,
                'class_id': line.product_id.categ_id.parent_id.id,
                'brick_id': line.product_id.categ_id.id,
                'lot_ids': lot_ids,
                'branded_barcode': branded_barcode_value or line.product_id.barcode,
                'type_product': line.type_product,
                'product_uom_qty': line.quantity,
                'price_unit': line.lot_id.cost_price,
                'sale_serial_type': line.lot_id.serial_type,
            })
            line.lot_id.is_uploaded = True

    @api.onchange('barcode_scanned')
    def _onchange_barcode_scanned(self):
        if not self.so_type:
            if self.barcode_scanned:
                raise ValidationError('Please choose a So Type before scanning a barcode.')
            return

        if self.barcode_scanned:
            barcode = self.barcode_scanned
            gs1_pattern = r'01(\d{14})21([A-Za-z0-9]+)'
            ean13_pattern = r'(\d{13})'
            custom_serial_pattern = r'^(R\d+)'

            def search_product(barcode_field, barcode_value):
                product = self.env['product.product'].search([(barcode_field, '=', barcode_value)], limit=1)
                if not product:
                    template = self.env['product.template'].search([(barcode_field, '=', barcode_value)], limit=1)
                    if template:
                        product = template.product_variant_id
                return product

            def global_lot_qty(lot, current_type):
                sale_lines = self.env['sale.order.line'].search([
                    ('lot_ids.name', '=', lot.name),
                    ('company_id', '=', self.env.company.id),
                    ('sale_serial_type', '=', current_type),
                    ('order_id.state', 'not in', ['cancel'])
                ])
                return sum(sale_lines.mapped('product_uom_qty'))

            def global_serial_used_orders(serial, current_type):
                sale_lines = self.env['sale.order.line'].search([
                    ('lot_ids.name', '=', serial),
                    ('company_id', '=', self.env.company.id),
                    ('sale_serial_type', '=', current_type),
                    ('order_id.state', 'not in', ['cancel'])
                ])
                return sale_lines.mapped('order_id.name')

            existing_order_line_cmds = [(4, line.id) for line in self.order_line]

            # GS1 Barcode
            if re.match(gs1_pattern, barcode):
                product_barcode, scanned_number = re.match(gs1_pattern, barcode).groups()
                product = search_product('barcode', product_barcode)
                if not product:
                    raise ValidationError(f"No product found with barcode {product_barcode}.")
                if product.tracking not in ('serial', 'lot'):
                    raise ValidationError(f'Product {product.display_name} must have serial or lot tracking.')

                lot = self.env['stock.lot'].search([
                    ('product_id', '=', product.id), ('product_qty', '>', 0),
                    ('name', '=', scanned_number), ('type_product', '=', 'un_brand'),
                    ('company_id', '=', self.company_id.id)
                ], limit=1)
                if lot.rs_price <= 0.0:
                    raise ValidationError(f"Zero RSP for this {lot.name}")

                if not lot:
                    raise ValidationError(f'No lot/serial number found for {scanned_number}.')

                sale_serial_type = 'return' if lot.serial_type == 'return' else 'regular'
                if product.tracking == 'serial':
                    if self.entered_qty > 1:
                        raise ValidationError("Serial Product: Qty must be 1.")
                    if scanned_number in self.order_line.filtered(
                            lambda l: l.sale_serial_type == sale_serial_type).mapped('lot_ids.name'):
                        raise ValidationError(f"Serial number {scanned_number} is already used in this order.")
                    existing_orders = global_serial_used_orders(scanned_number, sale_serial_type)
                    if existing_orders:
                        raise ValidationError(
                            f"Serial {scanned_number} already used in: {', '.join(set(existing_orders))}")
                    qty = 1
                else:
                    if not self.entered_qty or self.entered_qty <= 0:
                        raise ValidationError("Enter a valid quantity for lot tracked product.")
                    qty = self.entered_qty
                    existing_qty = global_lot_qty(lot, sale_serial_type)
                    stock_location = self.env.ref("stock.stock_location_stock")
                    lot_qty = self.env['stock.move.line'].sudo().search([
                        ('move_line_picking_type', '=', 'receipt'),
                        ('lot_id', '=', lot.id),
                        ('location_dest_id', '=', stock_location.id)])
                    if existing_qty + qty > sum(lot_qty.mapped('quantity')):
                        raise ValidationError(f'Qty for lot {lot.name} exceeds available stock.')
                new_line = (0, 0, {
                    'product_id': product.id,
                    'family_id': lot.product_id.categ_id.parent_id.parent_id.parent_id.id,
                    'category_id': lot.product_id.categ_id.parent_id.parent_id.id,
                    'class_id': lot.product_id.categ_id.parent_id.id,
                    'brick_id': lot.product_id.categ_id.id,
                    'product_uom_qty': qty,
                    'lot_ids': [(4, lot.id)],
                    'branded_barcode': lot.ref,
                    'type_product': lot.type_product,
                    'price_unit': lot.cost_price,
                    'sale_serial_type': sale_serial_type,
                })
                lot.is_uploaded = True
                self.order_line = [new_line] + existing_order_line_cmds

            # EAN-13 Barcode
            elif re.match(ean13_pattern, barcode):
                ean13_barcode = re.match(ean13_pattern, barcode).group(1)
                lots = self.env['stock.lot'].search([
                    ('ref', '=', ean13_barcode),
                    ('product_qty', '>', 0), ('type_product', '=', 'brand'),
                    ('company_id', '=', self.company_id.id)
                ], order='name')
                if not lots:
                    raise ValidationError(f"No lots found with EAN-13 barcode {ean13_barcode}.")
                product = lots[0].product_id
                if not product or product.tracking not in ('serial', 'lot'):
                    raise ValidationError(f'Product must be tracked.')

                used_names = set(self.order_line.mapped('lot_ids.name'))
                available_lot = None
                for lot in lots:
                    sale_serial_type = 'return' if lot.serial_type == 'return' else 'regular'
                    if lot.name in used_names:
                        continue
                    if product.tracking == 'serial':
                        if self.entered_qty and self.entered_qty > 1:
                            raise ValidationError("Serial product: Qty must be 1.")
                        existing_orders = global_serial_used_orders(lot.name, sale_serial_type)
                        if existing_orders:
                            continue
                        qty = 1
                        available_lot = lot
                        break
                    else:
                        if not self.entered_qty or self.entered_qty <= 0:
                            raise ValidationError("Enter valid quantity for lot tracked product.")
                        existing_qty = global_lot_qty(lot, sale_serial_type)
                        stock_location = self.env.ref("stock.stock_location_stock")
                        lot_qty = self.env['stock.move.line'].sudo().search([
                            ('move_line_picking_type', '=', 'receipt'),
                            ('lot_id', '=', lot.id),
                            ('location_dest_id', '=', stock_location.id)])
                        if existing_qty + self.entered_qty <= sum(lot_qty.mapped('quantity')):
                            qty = self.entered_qty
                            available_lot = lot
                            break
                if not available_lot:
                    raise ValidationError(f"All lots for barcode {ean13_barcode} are used or exceed quantity.")
                if available_lot.rs_price <= 0.0:
                    raise ValidationError(f"Zero RSP for this {available_lot.name}")
                new_line = (0, 0, {
                    'product_id': product.id,
                    'family_id': available_lot.product_id.categ_id.parent_id.parent_id.parent_id.id,
                    'category_id': available_lot.product_id.categ_id.parent_id.parent_id.id,
                    'class_id': available_lot.product_id.categ_id.parent_id.id,
                    'brick_id': available_lot.product_id.categ_id.id,
                    'product_uom_qty': qty,
                    'lot_ids': [(4, available_lot.id)],
                    'branded_barcode': available_lot.ref,
                    'type_product': available_lot.type_product,
                    'price_unit': available_lot.cost_price,
                    'sale_serial_type': sale_serial_type,
                })
                available_lot.is_uploaded = True
                self.order_line = [new_line] + existing_order_line_cmds

            # Custom Serial Barcode
            elif re.match(custom_serial_pattern, barcode):
                prefix = re.match(custom_serial_pattern, barcode).group(1)
                lots = self.env['stock.lot'].search([
                    ('ref', '=', prefix), ('product_qty', '>', 0),
                    ('company_id', '=', self.company_id.id)
                ])
                if not lots:
                    lots = self.env['stock.lot'].search([
                        ('name', '=like', f'{prefix}%'), ('product_qty', '>', 0),
                        ('company_id', '=', self.company_id.id)
                    ])
                if not lots:
                    raise ValidationError(f"No lots found for custom barcode {prefix}")

                selected_lot = None
                qty = 0
                for lot in lots:
                    product = lot.product_id
                    sale_serial_type = 'return' if lot.serial_type == 'return' else 'regular'
                    if product.tracking == 'serial':
                        if self.entered_qty > 1:
                            raise ValidationError("Serial product: Qty must be 1.")
                        if lot.name in self.order_line.filtered(
                                lambda l: l.sale_serial_type == sale_serial_type).mapped('lot_ids.name'):
                            raise ValidationError(f"Serial {lot.name} already used in this order.")
                        existing_orders = global_serial_used_orders(lot.name, sale_serial_type)
                        if existing_orders:
                            raise ValidationError(
                                f"Serial {lot.name} already used in: {', '.join(set(existing_orders))}")
                        selected_lot = lot
                        qty = 1
                        break
                    elif product.tracking == 'lot':
                        if not self.entered_qty or self.entered_qty <= 0:
                            raise ValidationError("Enter a valid quantity for lot tracked product.")
                        existing_qty = global_lot_qty(lot, sale_serial_type)
                        stock_location = self.env.ref("stock.stock_location_stock")
                        lot_qty = self.env['stock.move.line'].sudo().search([
                            ('move_line_picking_type', '=', 'receipt'),
                            ('lot_id', '=', lot.id),
                            ('location_dest_id', '=', stock_location.id)])
                        if existing_qty + self.entered_qty <= sum(lot_qty.mapped('quantity')):
                            selected_lot = lot
                            qty = self.entered_qty
                            break
                if not selected_lot:
                    raise ValidationError(f"No available lot found for {prefix} that meets constraints.")
                if selected_lot.rs_price <= 0.0:
                    raise ValidationError(f"Zero RSP for this {selected_lot.name}")
                new_line = (0, 0, {
                    'product_id': selected_lot.product_id.id,
                    'family_id': selected_lot.product_id.categ_id.parent_id.parent_id.parent_id.id,
                    'category_id': selected_lot.product_id.categ_id.parent_id.parent_id.id,
                    'class_id': selected_lot.product_id.categ_id.parent_id.id,
                    'brick_id': selected_lot.product_id.categ_id.id,
                    'product_uom_qty': qty,
                    'lot_ids': [(4, selected_lot.id)],
                    'branded_barcode': selected_lot.ref,
                    'type_product': selected_lot.type_product,
                    'price_unit': selected_lot.cost_price,
                    'sale_serial_type': sale_serial_type
                })
                selected_lot.is_uploaded = True
                self.order_line = [new_line] + existing_order_line_cmds
            else:
                raise ValidationError('Invalid barcode format.')

            self.barcode_scanned = False
            self.entered_qty = False

    # Removing sale order lines
    def reset_product_lines(self):
        self.picking_document = False
        for rec in self.order_line:
            for lot in rec.lot_ids:
                lot.is_uploaded = False
            rec.unlink()
                

    # @api.onchange('so_type')
    # def _check_operation_type(self):
    #     for order in self:
    #         if order.partner_id:
    #             if order.partner_id.parent_id and order.partner_id.parent_id == order.company_id.partner_id:
    #                 # Branch company: only 'HO operation', 'Intra', 'Others' are allowed
    #                 if order.so_type not in ['advertisement','ho_operation', 'intra_state', 'others']:
    #                     raise ValidationError("Invalid selection for a branch. Only 'Advt.', 'HO Operation', 'Intra', and 'Others' are allowed.")
    #             else:
    #                 # Main company: only 'HO operation', 'Inter', 'Others' are allowed
    #                 if order.so_type not in ['advertisement','ho_operation', 'inter_state', 'others']:
    #                     raise ValidationError("Invalid selection for a main companies. Only 'Advt.', 'HO Operation', 'Inter', and 'Others' are allowed.")

    @api.depends('so_type')
    def _compute_nhcl_so_type(self):
        if self.so_type == 'ho_operation':
            self.dummy_so_type = 'ho_operation'
        elif self.so_type == 'advertisement':
            self.dummy_so_type = 'advertisement'
        elif self.so_type == 'others':
            self.dummy_so_type = 'others'
        elif self.so_type == 'inter_state':
            self.dummy_so_type = 'ho_operation'
        elif self.so_type == 'intra_state':
            self.dummy_so_type = 'ho_operation'
        else:
            self.dummy_so_type = ''

    def inter_company_create_purchase_order(self, company):
        """ Create a Purchase Order from the current SO (self)
            Note : In this method, reading the current SO is done as sudo, and the creation of the derived
            PO as intercompany_user, minimizing the access right required for the trigger user
            :param company : the company of the created PO
            :rtype company : res.company record
        """
        for rec in self:
            if not company or not rec.company_id.partner_id:
                continue

            # find user for creating and validating SO/PO from company
            intercompany_uid = company.intercompany_user_id and company.intercompany_user_id.id or False
            if not intercompany_uid:
                raise ValidationError(_('Provide one user for intercompany relation for %(name)s '), name=company.name)
            # check intercompany user access rights
            if not self.env['purchase.order'].with_user(intercompany_uid).check_access_rights('create',
                                                                                              raise_exception=False):
                raise ValidationError(_("Inter company user of company %s doesn't have enough access rights", company.name))

            company_partner = rec.company_id.partner_id.with_user(intercompany_uid)
            # create the PO and generate its lines from the SO
            # read it as sudo, because inter-compagny user can not have the access right on PO
            po_vals = rec.sudo()._prepare_purchase_order_data(company, company_partner)
            inter_user = self.env['res.users'].sudo().browse(intercompany_uid)
            for line in rec.order_line.sudo():
                po_vals['order_line'] += [(0, 0, rec._prepare_purchase_order_line_data(line, rec.date_order, company))]
            purchase_order = self.env['purchase.order'].create(po_vals)
            for k in purchase_order.order_line:
                k._compute_tax_id()

            msg = _("Automatically generated from %(origin)s of company %(company)s.", origin=self.name,
                    company=company.name)
            purchase_order.message_post(body=msg)

            # write customer reference field on SO
            if not rec.client_order_ref:
                rec.client_order_ref = purchase_order.name

            # auto-validate the purchase order if needed
            if company.auto_validation:
                purchase_order.with_user(intercompany_uid).button_confirm()


    def _prepare_purchase_order_data(self, company, company_partner):
        """ Generate purchase order values, from the SO (self)
            :param company_partner : the partner representing the company of the SO
            :rtype company_partner : res.partner record
            :param company : the company in which the PO line will be created
            :rtype company : res.company record
        """
        self.ensure_one()
        # find location and warehouse, pick warehouse from company object
        warehouse = company.warehouse_id and company.warehouse_id.company_id.id == company.id and company.warehouse_id or False
        if not warehouse:
            raise ValidationError(_('Configure correct warehouse for company(%s) from Menu: Settings/Users/Companies', company.name))
        picking_type_id = self.env['stock.picking.type'].search([
            ('code', '=', 'incoming'), ('warehouse_id', '=', warehouse.id)
        ], limit=1)
        if not picking_type_id:
            intercompany_uid = company.intercompany_user_id.id
            picking_type_id = self.env['purchase.order'].with_user(intercompany_uid)._default_picking_type()
        return {
            'name': self.env['ir.sequence'].sudo().next_by_code('purchase.order'),
            'origin': self.name,
            'partner_id': company_partner.id,
            'nhcl_po_type': self.so_type,
            'picking_type_id': picking_type_id.id,
            'date_order': self.date_order,
            'company_id': company.id,
            'fiscal_position_id': company_partner.property_account_position_id.id,
            'payment_term_id': company_partner.property_supplier_payment_term_id.id,
            'auto_generated': True,
            'auto_sale_order_id': self.id,
            'partner_ref': self.name,
            'currency_id': self.currency_id.id,
            'order_line': [],
        }


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_ids = fields.Many2many('stock.lot', string="Serial Numbers")
    branded_barcode = fields.Char(string="Barcode")
    type_product = fields.Selection([('brand', 'Brand'), ('un_brand', 'UnBrand'), ('others', 'Others')],
                                    string='Brand Type', copy=False)
    sale_serial_type = fields.Selection([('regular', 'Regular'), ('return', 'Returned')],
                                        string='Serial Type', copy=False, tracking=True)
    family_id = fields.Many2one('product.category', string='Family', copy=False)
    category_id = fields.Many2one('product.category', string='Category', copy=False)
    class_id = fields.Many2one('product.category', string='Class', copy=False)
    brick_id = fields.Many2one('product.category', string='Brick', copy=False)

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.order_id and not self.order_id.so_type:
            # Clear the product_id and raise an error if no stock_type is selected
            self.product_id = False
            raise ValidationError(
                "You must select a SO Type before selecting a product."
            )
    def remove_sale_order_line(self):
        for rec in self:
            # for lot in rec.lot_ids:
            #     lot.is_uploaded = False
            rec.unlink()

    def _action_launch_stock_rule(self, previous_product_uom_qty=False):
        """ Override to ensure lot/serial numbers are carried over to stock moves """
        moves = super(SaleOrderLine, self)._action_launch_stock_rule(previous_product_uom_qty)
        for rec in self:
            for move_id in rec.move_ids:
                move_id.write({
                    'lot_ids': rec.lot_ids.ids
                })
                for move_line in move_id.move_line_ids:
                    if rec.product_id.id == move_line.product_id.id and rec.lot_ids.name == move_line.lot_name:
                        move_line.write({
                            'internal_ref_lot': rec.branded_barcode,

                        })
        for move_line in self.order_id.picking_ids.move_line_ids_without_package:
            if move_line.lot_id:
                move_line.write({
                    'internal_ref_lot': move_line.lot_id.ref,
                    'type_product': move_line.lot_id.type_product,
                    'categ_1': move_line.lot_id.category_1,
                    'categ_2': move_line.lot_id.category_2,
                    'categ_3': move_line.lot_id.category_3,
                    'categ_4': move_line.lot_id.category_4,
                    'categ_5': move_line.lot_id.category_5,
                    'categ_6': move_line.lot_id.category_6,
                    'categ_7': move_line.lot_id.category_7,
                    'categ_8': move_line.lot_id.category_8,
                    'descrip_1': move_line.lot_id.description_1,
                    'descrip_2': move_line.lot_id.description_2,
                    'descrip_3': move_line.lot_id.description_3,
                    'descrip_4': move_line.lot_id.description_4,
                    'descrip_5': move_line.lot_id.description_5,
                    'descrip_6': move_line.lot_id.description_6,
                    'descrip_7': move_line.lot_id.description_7,
                    'descrip_8': move_line.lot_id.description_8,
                    'descrip_9': move_line.lot_id.description_9,
                    'cost_price': move_line.lot_id.cost_price,
                    'mr_price': move_line.lot_id.mr_price,
                    'rs_price': move_line.lot_id.rs_price,
                })
        return moves
