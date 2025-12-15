from odoo import fields, models, api
from collections import defaultdict


class LoyaltyCard(models.Model):
    _inherit = "loyalty.card"

    nhcl_used_card = fields.Boolean(string="Used Card", copy=False)


class PosOrderLine(models.Model):
    """ The class PosOrder is used to inherit pos.order.line """
    _inherit = 'pos.order.line'

    employe_no = fields.Char(string="Sale Person")
    badge_id = fields.Char(string="Badge Id")
    employ_id = fields.Many2one("hr.employee", string='Employee Id')
    gdiscount =fields.Float("Global discount")
    disc_lines = fields.Char(string="Disc Lines")
    vendor_return_disc_price = fields.Float('Vendor Return Price', copy=False)
    discount_reward = fields.Integer('Discount', copy=False)
    nhcl_cost_price = fields.Float(string="Cost Price", copy=False)

    @api.model
    def create(self, vals_list):
        res = super().create(vals_list)
        if res:
            for line in res:
                if line.pack_lot_ids:
                    lot = self.env['stock.lot'].search([('name', '=', line.pack_lot_ids[0].lot_name),
                                                        ('product_id', '=', line.pack_lot_ids[0].product_id.id)])
                    if lot.rs_price > 0:
                        line.price_unit = lot.rs_price
                    if lot.cost_price:
                        line.nhcl_cost_price = lot.cost_price
                if line.reward_id:
                    if line.reward_id.reward_type == 'discount' and line.reward_id.buy_with_reward_price == 'yes':
                        line.price_unit = line.reward_id.reward_price / line.reward_id.required_points
                    elif line.reward_id.reward_type == 'discount_on_product':
                        line.price_unit = line.reward_id.product_price
                    if line.price_unit < 0:
                        price_unit = -(line.price_unit)
                    else:
                        price_unit = line.price_unit
                    tax_ids = self.env['account.tax'].search(
                        [('min_amount', '<=', price_unit), ('max_amount', '>=', price_unit)])
                    for tax in tax_ids:
                        if line.reward_id.reward_product_id:
                            product_id = line.reward_id.reward_product_id
                            tax_id = product_id.taxes_id.filtered(lambda x: x.id == tax.id)
                            if tax_id:
                                line.tax_ids = tax_id
                                break
                        elif line.reward_id.discount_max_amount > 0 and line.reward_id.buy_with_reward_price == 'no':
                            line.tax_ids = False
                        if line.reward_id and not line.reward_id.reward_product_id:
                            product_id = line.order_id.lines[0].product_id
                            tax_id = product_id.taxes_id.filtered(lambda x: x.id == tax.id)
                            if line.reward_id.program_type!='gift_card' and tax_id:
                                line.tax_ids = tax_id
                                break

        return res

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['gdiscount'] = orderline.gdiscount
        result['discount_reward'] = orderline.discount_reward
        return result


class PosOrder(models.Model):
    _inherit = 'pos.order'

    _rec_name = 'pos_reference'

    credit_id = fields.Integer("Credit Id")
    credit_ids = fields.One2many('used.credits', 'used_credit_id', string='Credits', copy=False)

    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        credit_ids = ui_order.get('credit_ids', [])
        credit_amounts = ui_order.get('credit_note_amounts', [])
        credit_lines = []
        existing_credit_notes = []
        for credit_id, amount in zip(credit_ids, credit_amounts):
            if credit_id not in existing_credit_notes:
                credit_lines.append((0, 0, {
                    'credit_id': int(credit_id),
                    'amount': amount,
                }))
                existing_credit_notes.append(credit_id)
        order_fields['credit_ids'] = credit_lines
        return order_fields

    @api.model
    def create(self, vals):
        order = super(PosOrder, self).create(vals)
        for credit in order.credit_ids:
            credit.used_credit_id = order.id
        reward_order_lines = order.lines.filtered(lambda x: x.reward_id)
        discount_reward_order_lines = order.lines.filtered(lambda x: x.discount_reward > 0)
        remaining_order_lines = order.lines.filtered(lambda x: not x.reward_id)
        for reward_order_line in reward_order_lines:
            if reward_order_line.reward_id.program_id.is_vendor_return == True:
                if (
                        reward_order_line.reward_id.reward_type == 'product' and
                        reward_order_line.reward_id.reward_product_id in reward_order_line.reward_id.program_id.rule_ids.ref_product_ids
                ):

                    free_qty_to_assign = reward_order_line.reward_id.reward_product_qty
                    count = 0
                    for remaining_order_line in remaining_order_lines:
                        if reward_order_line.reward_id.reward_product_id == remaining_order_line.product_id:
                            if count < free_qty_to_assign:
                                remaining_order_line.vendor_return_disc_price = remaining_order_line.price_unit
                                count += 1
                elif reward_order_line.reward_id.discount_applicability == 'order':
                    total_qty = sum(remaining_order_lines.mapped('qty'))
                    price = 0
                    if reward_order_line.price_unit>0 and total_qty>0:
                        price = reward_order_line.price_unit / total_qty
                    for remaining_order_line in remaining_order_lines:
                        remaining_order_line.vendor_return_disc_price += remaining_order_line.qty * -(price)

                else:
                    total_rewards = reward_order_line.reward_id.program_id.reward_ids.mapped('id')
                    reward_index = total_rewards.index(reward_order_line.reward_id.id)
                    if reward_order_line.reward_id.program_id.rule_ids:
                        serial_number_lines = remaining_order_lines.pack_lot_ids.filtered(
                            lambda x: x.lot_name in reward_order_line.reward_id.program_id.rule_ids[
                                reward_index].serial_ids.mapped('name'))
                        total_qty = len(serial_number_lines)
                        price = 0
                        if reward_order_line.price_unit > 0 and total_qty > 0:
                            price = reward_order_line.price_unit / total_qty
                        for remaining_order_line in remaining_order_lines:
                            for lot_id in remaining_order_line.pack_lot_ids:
                                if lot_id.lot_name in reward_order_line.reward_id.program_id.rule_ids[
                                    reward_index].serial_ids.mapped('name'):
                                    remaining_order_line.vendor_return_disc_price += remaining_order_line.qty * -(price)
        for discount_reward_order_line in discount_reward_order_lines:
            reward_id = self.env['loyalty.reward'].search([('id','=',discount_reward_order_line.discount_reward)])
            if reward_id.program_id.is_vendor_return == True:
                if reward_id.discount_applicability == 'specific' and reward_id.discount>0:
                    discount = reward_id.discount/100
                    price = discount_reward_order_line.price_unit*discount
                    discount_reward_order_line.vendor_return_disc_price = price
        return order


    def _serial_pos_post(self):
        stock_lot = self.env['stock.lot']
        lot_names = set()  # Use a set to collect lot names

        for order in self:
            for line in order.lines:
                for lot in line.pack_lot_ids:
                    lot_names.add(lot.lot_name)

        # Retrieve all stock.lot records that match the lot names in a single search
        stock_lots = stock_lot.search([('name', 'in', list(lot_names))])

        # Create a dictionary of lot names to stock lot records
        lot_dict = {lot.name: lot for lot in stock_lots}

        # Now, loop through the orders and lines and update the stock lots in batch
        for order in self:
            for line in order.lines:
                for lot in line.pack_lot_ids:

                    lot_name = lot.lot_name
                    lot = lot_dict.get(lot_name)
                    if lot and lot.product_qty == 1:
                        lot.write({'is_used': True})

    def _process_saved_order(self, draft):
        res = super(PosOrder, self)._process_saved_order(draft)
        if self.state == 'paid':
            self._serial_pos_post()
            existing_credit_notes = []
            for credit_id in self.credit_ids:
                credit = self.partner_id.credit_note_ids.filtered(lambda x: x.id == credit_id.credit_id)
                if credit and credit.id not in existing_credit_notes:
                    credit.write({'deducted_amount': credit.deducted_amount + credit_id.amount})
                    existing_credit_notes.append(credit.id)
        return res

    def confirm_coupon_programs(self, coupon_data):
        """
        This is called after the order is created.

        This will create all necessary coupons and link them to their line orders etc..

        It will also return the points of all concerned coupons to be updated in the cache.
        """
        get_partner_id = lambda partner_id: partner_id and self.env['res.partner'].browse(
            partner_id).exists() and partner_id or False
        # Keys are stringified when using rpc
        coupon_data = {int(k): v for k, v in coupon_data.items()}

        self._check_existing_loyalty_cards(coupon_data)
        # Map negative id to newly created ids.
        coupon_new_id_map = {k: k for k in coupon_data.keys() if k > 0}

        # Create the coupons that were awarded by the order.
        coupons_to_create = {k: v for k, v in coupon_data.items() if k < 0 and not v.get('giftCardId')}
        coupon_create_vals = [{
            'program_id': p['program_id'],
            'partner_id': get_partner_id(p.get('partner_id', False)),
            'code': p.get('barcode') or self.env['loyalty.card']._generate_code(),
            'points': 0,
            'source_pos_order_id': self.id,
        } for p in coupons_to_create.values()]

        # Pos users don't have the create permission
        new_coupons = self.env['loyalty.card'].with_context(action_no_send_mail=True).sudo().create(coupon_create_vals)

        # We update the gift card that we sold when the gift_card_settings = 'scan_use'.
        gift_cards_to_update = [v for v in coupon_data.values() if v.get('giftCardId')]
        updated_gift_cards = self.env['loyalty.card']
        for coupon_vals in gift_cards_to_update:
            gift_card = self.env['loyalty.card'].browse(coupon_vals.get('giftCardId'))
            print("1",gift_card)
            gift_card.write({
                'points': coupon_vals['points'],
                'source_pos_order_id': self.id,
                'partner_id': get_partner_id(coupon_vals.get('partner_id', False)),
            })
            updated_gift_cards |= gift_card

        # Map the newly created coupons
        for old_id, new_id in zip(coupons_to_create.keys(), new_coupons):
            coupon_new_id_map[new_id.id] = old_id

        all_coupons = self.env['loyalty.card'].browse(coupon_new_id_map.keys()).exists()
        lines_per_reward_code = defaultdict(lambda: self.env['pos.order.line'])
        for line in self.lines:
            if not line.reward_identifier_code:
                continue
            lines_per_reward_code[line.reward_identifier_code] |= line
        for coupon in all_coupons:
            if coupon.id in coupon_new_id_map:
                # Coupon existed previously, update amount of points.
                coupon.points += coupon_data[coupon_new_id_map[coupon.id]]['points']
                coupon.nhcl_used_card = True
            for reward_code in coupon_data[coupon_new_id_map[coupon.id]].get('line_codes', []):
                lines_per_reward_code[reward_code].coupon_id = coupon
        # Send creation email
        new_coupons.with_context(action_no_send_mail=False)._send_creation_communication()
        # Reports per program
        report_per_program = {}
        coupon_per_report = defaultdict(list)
        # Important to include the updated gift cards so that it can be printed. Check coupon_report.
        for coupon in new_coupons | updated_gift_cards:
            if coupon.program_id not in report_per_program:
                report_per_program[coupon.program_id] = coupon.program_id.communication_plan_ids. \
                    filtered(lambda c: c.trigger == 'create').pos_report_print_id
            for report in report_per_program[coupon.program_id]:
                coupon_per_report[report.id].append(coupon.id)
        return {
            'coupon_updates': [{
                'old_id': coupon_new_id_map[coupon.id],
                'id': coupon.id,
                'points': coupon.points,
                'code': coupon.code,
                'program_id': coupon.program_id.id,
                'partner_id': coupon.partner_id.id,
            } for coupon in all_coupons if coupon.program_id.is_nominative],
            'program_updates': [{
                'program_id': program.id,
                'usages': program.total_order_count,
            } for program in all_coupons.program_id],
            'new_coupon_info': [{
                'program_name': coupon.program_id.name,
                'expiration_date': coupon.expiration_date,
                'code': coupon.code,
            } for coupon in new_coupons if (
                    coupon.program_id.applies_on == 'future'
                    # Don't send the coupon code for the gift card and ewallet programs.
                    # It should not be printed in the ticket.
                    and coupon.program_id.program_type not in ['gift_card', 'ewallet']
            )],
            'coupon_report': coupon_per_report,
        }



class UsedCredits(models.Model):
    _name = 'used.credits'

    used_credit_id = fields.Many2one('pos.order', string="Used Credit")
    credit_id = fields.Integer("Credit Id")
    amount = fields.Float('Amount')

