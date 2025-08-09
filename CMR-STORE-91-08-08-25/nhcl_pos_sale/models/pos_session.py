from odoo import models,fields,api,_
from odoo.exceptions import UserError,ValidationError

from odoo.tools import float_is_zero, float_compare



class PosSession(models.Model):
    _inherit = 'pos.session'

    tracking_ids = fields.One2many('location.tracking', 'session_id', string='Location Trackings')


    """Inherited model POS Session for loading field in hr.employee into
           pos session.

           Methods:
               _pos_ui_models_to_load(self):
                  to load model hr employee to pos session.

               _loader_params_hr_employee(self):
                  loads field limited_discount to pos session.

           """

    def _pos_ui_models_to_load(self):
        res = super()._pos_ui_models_to_load()
        models = ["stock.lot", "hr.employee"]
        res += [model for model in models if model not in res]
        return res

    def _loader_params_stock_lot(self):
        return {
            'search_params': {
                'domain': [],
                'fields': ['id', 'name', 'product_id', 'product_qty', 'ref', 'location_id', 'rs_price'],
            },
        }

    # def _loader_params_pos_order_line(self):
    #     return {
    #         'search_params': {
    #             'domain': [],
    #             'fields': ['id', 'global_discount'],
    #         },
    #     }

    def _get_pos_ui_stock_lot(self, params):
        return self.env['stock.lot'].search_read(**params['search_params'])

    def _loader_params_hr_employee(self):
        """load hr.employee parameters"""
        result = super()._loader_params_hr_employee()
        result['search_params']['fields'].extend(
            ['limited_discount'])
        return result

    def _loader_params_res_company(self):
        """load hr.employee parameters"""
        result = super()._loader_params_res_company()
        result['search_params']['fields'].extend(
            ['company_short_code'])
        return result


    def _prepare_line(self, order_line):
        """ Derive from order_line the order date, income account, amount and taxes information.

        These information will be used in accumulating the amounts for sales and tax lines.
        """
        def get_income_account(order_line):
            product = order_line.product_id
            income_account = product.with_company(order_line.company_id)._get_product_accounts()['income'] or self.config_id.journal_id.default_account_id
            if not income_account:
                raise UserError(_('Please define income account for this product: "%s" (id:%d).',
                                  product.name, product.id))
            return order_line.order_id.fiscal_position_id.map_account(income_account)

        company_domain = self.env['account.tax']._check_company_domain(order_line.order_id.company_id)
        tax_ids = order_line.tax_ids_after_fiscal_position.filtered_domain(company_domain)
        sign = -1 if order_line.qty >= 0 else 1
        price = sign * order_line.price_unit * (1 - (order_line.discount or 0.0) / 100.0)
        price = price * (1 - (order_line.gdiscount or 0.0) / 100.0)
        # The 'is_refund' parameter is used to compute the tax tags. Ultimately, the tags are part
        # of the key used for summing taxes. Since the POS UI doesn't support the tags, inconsistencies
        # may arise in 'Round Globally'.
        check_refund = lambda x: x.qty * x.price_unit < 0
        is_refund = check_refund(order_line)
        tax_data = tax_ids.compute_all(price_unit=price, quantity=abs(order_line.qty), currency=self.currency_id, is_refund=is_refund, fixed_multiplicator=sign)
        taxes = tax_data['taxes']
        # For Cash based taxes, use the account from the repartition line immediately as it has been paid already
        for tax in taxes:
            tax_rep = self.env['account.tax.repartition.line'].browse(tax['tax_repartition_line_id'])
            tax['account_id'] = tax_rep.account_id.id
        date_order = order_line.order_id.date_order
        taxes = [{'date_order': date_order, **tax} for tax in taxes]
        return {
            'date_order': order_line.order_id.date_order,
            'income_account_id': get_income_account(order_line).id,
            'amount': order_line.price_subtotal,
            'taxes': taxes,
            'base_tags': tuple(tax_data['base_tags']),
        }

    def get_wallet_amount(self, partner_id):
        partner = self.env['res.partner'].browse(partner_id)

        if not partner.exists():
            return []

        credit_data = []
        for credit_note in partner.credit_note_ids:
            if credit_note.remaining_amount > 0:
                credit_data.append({
                    'id': credit_note.id,
                    'voucher_number': credit_note.voucher_number,
                    'remaining_amount': credit_note.remaining_amount,
                })

        return credit_data


    def check_the_lots_in_respective_location(self, lines):
        StockLot = self.env['stock.lot']
        StockQuant = self.env['stock.quant']
        LocationTracking = self.env['location.tracking']

        default_location = self.config_id.warehouse_id.lot_stock_id.id

        # Filter only tracked products with qty > 0
        stockable_lines = lines.filtered(
            lambda l: (
                    l.product_id.type == 'product' and
                    l.product_id.tracking in ['lot', 'serial'] and
                    not float_is_zero(l.qty, precision_rounding=l.product_id.uom_id.rounding)
            )
        )

        # Build a map of lot_name -> total consumed qty
        lot_qty_map = {}

        for line in stockable_lines:
            for lot_line in line.pack_lot_ids.filtered(lambda l: l.lot_name):
                lot_name = lot_line.lot_name
                lot_qty_map[lot_name] = lot_qty_map.get(lot_name, 0.0) + line.qty

        lot_names = list(lot_qty_map.keys())

        # Find stock.lot records
        existing_lots = StockLot.search([
            ('name', 'in', lot_names),
            ('product_id', 'in', stockable_lines.mapped('product_id').ids),
        ])

        existing_tracked_lot_ids = LocationTracking.search([
            ('stock_lot', 'in', existing_lots.ids),
            ('session_id', '=', self.id),
        ]).mapped('stock_lot.id')

        missing_lot_names = []
        tracking_vals = []

        for lot in existing_lots:
            # Sum of available quantity in stock.quant at expected location
            available_qty = sum(StockQuant.search([
                ('lot_id', '=', lot.id),
                ('location_id', '=', default_location),
            ]).mapped('quantity'))

            required_qty = lot_qty_map.get(lot.name, 0.0)

            if required_qty > available_qty:
                if lot.id not in existing_tracked_lot_ids:
                    tracking_vals.append({
                        'date': fields.Datetime.now(),
                        'stock_lot': lot.id,
                        'location_id': lot.location_id.id or default_location,
                        'session_id': self.id,
                    })
                missing_lot_names.append(f"{lot.name} (required: {required_qty}, available: {available_qty})")

        if tracking_vals:
            LocationTracking.create(tracking_vals)
            self.env.cr.commit()

        if missing_lot_names:
            raise UserError(
                "⚠ The following lots/serial numbers are over-consumed or not in the expected location:\n%s\n"
                "Please review and correct before EOD." %
                "\n".join(missing_lot_names)
            )

        return True

    def action_pos_session_closing_control(self,balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None):
        lines = self._get_closed_orders().lines
        self.check_the_lots_in_respective_location(lines)

        return super(PosSession,self).action_pos_session_closing_control(balancing_account=False, amount_to_balance=0, bank_payment_method_diffs=None)






class LocationTracking(models.Model):
    _name = 'location.tracking'

    _rec_name = "stock_lot"

    date = fields.Datetime(string='date',readonly=True)
    stock_lot = fields.Many2one("stock.lot",string="Serail Number",readonly=True)
    qty = fields.Float(string="Quantity",related="stock_lot.product_qty",readonly=True)
    location_id = fields.Many2one("stock.location",string="Orginal Location",readonly=True)
    location_real_id = fields.Many2one("stock.location",string="Real Time Location",related='stock_lot.location_id',readonly=True)
    session_id = fields.Many2one('pos.session', string="POS Session",readonly=True)
