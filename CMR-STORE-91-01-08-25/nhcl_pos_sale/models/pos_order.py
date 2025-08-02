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
        return res

    def _export_for_ui(self, orderline):
        result = super()._export_for_ui(orderline)
        result['gdiscount'] = orderline.gdiscount
        return result


class PosOrder(models.Model):
    _inherit = 'pos.order'

    _rec_name = 'pos_reference'

    credit_id = fields.Integer("Credit Id")


    @api.model
    def _order_fields(self, ui_order):
        order_fields = super(PosOrder, self)._order_fields(ui_order)
        order_fields['credit_id'] = ui_order.get('credit_id')
        return order_fields


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

        if  self.state == 'paid':
            self._serial_pos_post()
            redeem_amount = self.payment_ids.filtered(lambda x: x.payment_method_id.is_credit_settlement).amount
            print(redeem_amount)
            credit = self.env['res.partner.credit.note'].browse(self.credit_id)

            credit.write({'deducted_amount' : credit.deducted_amount + redeem_amount})

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





