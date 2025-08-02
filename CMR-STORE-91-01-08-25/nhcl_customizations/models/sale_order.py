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

    # Picking Document Lines Creation
    def get_picking_lines(self):
        existing_order = self.env['sale.order'].sudo().search(
            [('picking_document', '=', self.picking_document.id), ('id', '!=', self.id)], limit=1)
        if existing_order:
            raise ValidationError(
                f"This picking document '{self.picking_document.name}' is already used in Sale Order '{existing_order.name}'.")
        picking = self.env['stock.picking'].sudo().search([('name', '=', self.picking_document.name)])
        for line in picking.move_ids_without_package:
            if line.product_id:
                lot_ids = [(6, 0, line.lot_ids.ids)]

                # Collect barcode references, ensuring we exclude False values
                barcodes = line.lot_ids.mapped('ref')
                # Filter out any False or None values
                barcodes = [barcode for barcode in barcodes if barcode]
                # Remove duplicates by converting to a set, then back to a list
                unique_barcodes = list(set(barcodes))
                # Join unique barcodes into a single string
                branded_barcode_value = ', '.join(unique_barcodes)

                if branded_barcode_value:
                    self.order_line.create({
                        'order_id': self.id,
                        'product_id': line.product_id.id,
                        'lot_ids': lot_ids,
                        'branded_barcode': branded_barcode_value,
                        'type_product': line.type_product,
                        'product_uom_qty': line.quantity
                    })
                else:
                    self.order_line.create({
                        'order_id': self.id,
                        'product_id': line.product_id.id,
                        'lot_ids': lot_ids,
                        'product_uom_qty': line.quantity,
                        'type_product': line.type_product,
                        'branded_barcode': line.product_id.barcode

                    })
            else:
                raise ValidationError(f"No Products Found in '{picking.name}'.")

    @api.onchange('barcode_scanned')
    def _onchange_barcode_scanned(self):
        if not self.so_type:
            if self.barcode_scanned:
                raise ValidationError('Please select a So Type before scanning a barcode.')
            return
        if self.barcode_scanned:
            barcode = self.barcode_scanned
            gs1_pattern = r'01(\d{14})21([A-Za-z0-9]+)'
            gs1_match = re.match(gs1_pattern, barcode)
            ean13_pattern = r'(\d{13})'
            ean13_match = re.match(ean13_pattern, barcode)
            custom_serial_pattern = r'^(R\d+)'

            def search_product(barcode_field, barcode_value):
                """Helper function to search in product.product and product.template"""
                product = self.env['product.product'].search([(barcode_field, '=', barcode_value)], limit=1)
                if not product:
                    # Search in product.template if not found in product.product
                    template = self.env['product.template'].search([(barcode_field, '=', barcode_value)], limit=1)
                    if template:
                        # Return the first product variant linked to the template
                        product = template.product_variant_id
                return product

            if gs1_match:
                product_barcode = gs1_match.group(1)
                serial_number = gs1_match.group(2)
                # Search for the product in product.product first, then in product.template
                product = search_product('barcode', product_barcode)
                if product:
                    # Check if the serial number is already assigned to any line in the current order
                    for line in self.order_line:
                        if serial_number in line.lot_ids.mapped('name'):
                            raise ValidationError(
                                f'Serial number {serial_number} is already assigned to a product line in the current order.')
                    # Check if the serial number is already assigned in stock.picking with 'internal' or 'outgoing' type
                    pickings_with_serial = self.env['stock.picking'].search([
                        ('picking_type_code', 'in', ['internal', 'outgoing']),
                        ('state', '!=', 'cancel'),
                        ('move_line_ids_without_package.lot_id.name', '=', serial_number),
                    ])
                    if pickings_with_serial:
                        raise ValidationError(
                            f'Serial number {serial_number} is already assigned in {pickings_with_serial.name}.')

                    # Check if the product already exists in the order lines
                    existing_line = self.order_line.filtered(lambda l: l.product_id == product)
                    if existing_line:
                        # Update the serial number (stock.lot) in the existing line
                        lot = self.env['stock.lot'].search(
                            [('product_id', '=', product.id), ('name', '=', serial_number)], limit=1)
                        if lot:
                            existing_line.lot_ids = [(4, lot.id)]
                            # Update product_uom_qty to the total number of serial numbers
                            existing_line.product_uom_qty = len(existing_line.lot_ids)
                        else:
                            raise ValidationError(f'No serial number found: {serial_number}')
                    else:
                        # Fetch or create the stock.lot records
                        lot = self.env['stock.lot'].search([
                            ('product_id', '=', product.id),
                            ('name', '=', serial_number)], limit=1)
                        if lot:
                            # Add a new line with the product and set product_uom_qty to 1
                            self.order_line = [(0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': 1,
                                'lot_ids': [(4, lot.id)],
                                'type_product': lot.type_product,

                            })]
                        else:
                            raise ValidationError(f'No serial number found: {serial_number}')
                else:
                    raise ValidationError(f'No product found with barcode {product_barcode}')
            elif ean13_match:
                ean13_barcode = ean13_match.group(1)
                # Search for all lots that match the EAN-13 barcode in the ref field
                lots = self.env['stock.lot'].search([('ref', '=', ean13_barcode), ('product_qty', '>', 0)])

                if lots:
                    product = lots[0].product_id
                    if not product:
                        raise ValidationError(f'No product associated with lots for barcode {ean13_barcode}')
                    # Get serial numbers used in stock.picking with 'internal' or 'delivery' types
                    used_serials = self.env['stock.picking'].search([
                        ('picking_type_code', 'in', ['internal', 'outgoing']),
                        ('state', '!=', 'cancel'),
                        ('move_ids_without_package.dummy_lot_ids', 'in', lots.ids)
                    ]).mapped('move_ids_without_package.dummy_lot_ids.name')

                    # Filter out assigned or used serial numbers
                    assigned_serial_numbers = self.order_line.mapped('lot_ids.name')
                    available_lots = lots.filtered(
                        lambda l: l.name not in assigned_serial_numbers and l.name not in used_serials
                    )

                    if not available_lots:
                        raise ValidationError(
                            f'All serial numbers for barcode {ean13_barcode} have been assigned or used in stock.picking')

                    # Take the next available lot
                    next_lot = available_lots[0]

                    # Check if the product already exists in the order lines
                    existing_line = self.order_line.filtered(lambda l: l.product_id == product)
                    if existing_line:
                        # Avoid duplicate entries in the branded_barcode field
                        current_barcodes = existing_line.branded_barcode.split(
                            ', ') if existing_line.branded_barcode else []
                        if next_lot.ref not in current_barcodes:
                            # Add the new barcode only if it doesn't already exist
                            current_barcodes.append(next_lot.ref)
                            existing_line.branded_barcode = ', '.join(current_barcodes)

                        # Update the lot and quantity
                        existing_line.lot_ids = [(4, next_lot.id)]
                        existing_line.product_uom_qty = len(existing_line.lot_ids)
                    else:
                        # Add a new line with the product and set product_uom_qty to 1
                        self.order_line = [(0, 0, {
                            'product_id': product.id,
                            'product_uom_qty': 1,
                            'lot_ids': [(4, next_lot.id)],
                            'branded_barcode': next_lot.ref,
                            'type_product': next_lot.type_product,

                        })]
                else:
                    raise ValidationError(
                        f'No lots found with EAN-13 barcode {ean13_barcode} or insufficient quantity')
            elif re.match(custom_serial_pattern, barcode):
                # Handle custom serial numbers that start with R1, R2, R3, etc.
                prefix = re.match(custom_serial_pattern, barcode).group(1)
                # Search for a lot with this prefix in the stock.lot model
                lot = self.env['stock.lot'].search([('name', '=like', f'{prefix}%')], limit=1)
                if lot:
                    product = lot.product_id
                    # **Branded product validation:**
                    if lot.type_product == 'brand':
                        raise ValidationError(
                            f'Serial number {lot.name} is for a branded product and cannot be used here.')
                    # Validation: Check if the serial number is already used in the current order
                    for line in self.order_line:
                        if lot.name in line.lot_ids.mapped('name'):
                            raise ValidationError(
                                f'Serial number {lot.name} is already assigned to a product line in the current order.')
                    # Validation: Check if the serial number is used in a 'stock.picking' with type 'internal' or 'outgoing'
                    pickings_with_serial = self.env['stock.picking'].search([
                        ('picking_type_id.code', 'in', ['internal', 'outgoing']), ('state', '!=', 'cancel'),
                        ('move_line_ids.lot_id.name', '=', lot.name), ])
                    if pickings_with_serial:
                        picking_names = ', '.join(pickings_with_serial.mapped('name'))
                        raise ValidationError(
                            f'Serial number {lot.name} is already assigned in the following pickings: {picking_names}.')
                    if product:
                        # Check if the product already exists in the order lines
                        existing_line = self.order_line.filtered(lambda l: l.product_id == product)
                        if existing_line:
                            # Add the new lot to the existing line
                            existing_line.lot_ids = [(4, lot.id)]
                            # Update product_uom_qty based on the number of lots
                            existing_line.product_uom_qty = len(existing_line.lot_ids)
                        else:
                            # Add a new line with the product and set product_uom_qty to 1
                            self.order_line = [(0, 0, {
                                'product_id': product.id,
                                'product_uom_qty': 1,
                                'lot_ids': [(4, lot.id)],
                                'type_product': lot.type_product,

                            })]
                    else:
                        raise ValidationError(f'No product found for the lot with serial number prefix {prefix}')
                else:
                    raise ValidationError(f'No lot found with serial number prefix {prefix}')
            else:
                raise ValidationError('Invalid barcode format')
            # Clear the barcode field after processing
            self.barcode_scanned = False

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
        for move in self.order_id.picking_ids.move_ids_without_package:
            sale_line = self.filtered(lambda l: l.product_id == move.product_id)
            if sale_line and sale_line.lot_ids:
                move.write({
                    'lot_ids': sale_line.lot_ids.ids
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
                    'cost_price': move_line.lot_id.cost_price,
                    'mr_price': move_line.lot_id.mr_price,
                    'rs_price': move_line.lot_id.rs_price,

                })
        return moves
