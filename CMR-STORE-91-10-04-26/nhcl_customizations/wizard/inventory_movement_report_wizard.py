from odoo import models, fields
from odoo.exceptions import ValidationError
from datetime import datetime, time


class InventoryMovementReportWizard(models.TransientModel):
    _name = "inventory.movement.report.wizard"
    _description = "inventory movement report wizard"

    from_date = fields.Date(string="From Date")
    to_date = fields.Date(string="To Date")

    # works on from and to date filtration
    # def action_generate(self):
    #     # Validate dates
    #     if self.from_date and self.to_date:
    #         if self.from_date > self.to_date:
    #             raise ValidationError("From Date cannot be greater than To Date.")
    #
    #     # Remove old report data
    #     self.env['inventory.movement.report'].search([]).unlink()
    #
    #     # Get all moves in date range
    #     moves = self.env['stock.move'].search([
    #         ('state', '=', 'done'),
    #         ('picking_id.date_done', '>=', self.from_date),
    #         ('picking_id.date_done', '<=', self.to_date),
    #         ('product_id.detailed_type', '=', 'product'),
    #     ])
    #
    #     # Dictionary to store product wise data
    #     product_data = {}
    #
    #     for move in moves:
    #
    #         product = move.product_id
    #         picking_type = move.picking_id.stock_picking_type
    #         qty = move.quantity
    #         rs_total = sum(line.rs_price for line in move.move_line_ids)
    #
    #         # If product not in dictionary, create empty values
    #         if product.id not in product_data:
    #             product_data[product.id] = {
    #                 # 'receipt_qty': 0.0,
    #                 # 'delivery_qty': 0.0,
    #                 # 'maintodamage_qty': 0.0,
    #                 # 'goodsreturn_damage_qty': 0.0,
    #                 # 'damagetomain_qty': 0.0,
    #                 # 'pos_order_qty': 0.0,
    #                 # 'pos_exchange_qty': 0.0,
    #                 # 'pos_return_qty': 0.0,
    #                 'receipt_qty': 0.0,
    #                 'receipt_rs_total': 0.0,
    #                 'delivery_qty': 0.0,
    #                 'delivery_rs_total': 0.0,
    #                 'maintodamage_qty': 0.0,
    #                 'maintodamage_rs_total': 0.0,
    #                 'goodsreturn_damage_qty': 0.0,
    #                 'goodsreturn_damage_rs_total': 0.0,
    #                 'damagetomain_qty': 0.0,
    #                 'damagetomain_rs_total': 0.0,
    #                 'pos_order_qty': 0.0,
    #                 'pos_order_rs_total': 0.0,
    #                 'pos_exchange_qty': 0.0,
    #                 'pos_exchange_rs_total': 0.0,
    #                 'pos_return_qty': 0.0,
    #                 'pos_return_rs_total': 0.0,
    #             }
    #
    #         # Now check picking type and add quantity
    #
    #         if picking_type == 'receipt':
    #             product_data[product.id]['receipt_qty'] += qty
    #             product_data[product.id]['receipt_rs_total'] += rs_total
    #
    #         elif picking_type == 'return':
    #             product_data[product.id]['delivery_qty'] += qty
    #             product_data[product.id]['delivery_rs_total'] += rs_total
    #
    #         elif picking_type == 'main_damage':
    #             product_data[product.id]['maintodamage_qty'] += qty
    #             product_data[product.id]['maintodamage_rs_total'] += rs_total
    #
    #         elif picking_type == 'damage':
    #             product_data[product.id]['goodsreturn_damage_qty'] += qty
    #             product_data[product.id]['goodsreturn_damage_rs_total'] += rs_total
    #
    #         elif picking_type == 'damage_main':
    #             product_data[product.id]['damagetomain_qty'] += qty
    #             product_data[product.id]['damagetomain_rs_total'] += rs_total
    #
    #         elif picking_type == 'pos_order':
    #             product_data[product.id]['pos_order_qty'] += qty
    #             product_data[product.id]['pos_order_rs_total'] += rs_total
    #
    #         elif picking_type == 'exchange':
    #             product_data[product.id]['pos_exchange_qty'] += qty
    #             product_data[product.id]['pos_exchange_rs_total'] += rs_total
    #
    #         elif picking_type == 'return_main':
    #             product_data[product.id]['pos_return_qty'] += qty
    #             product_data[product.id]['pos_return_rs_total'] += rs_total
    #
    #     # Create report records
    #     for product_id, values in product_data.items():
    #         product = self.env['product.product'].browse(product_id)
    #         category = product.categ_id
    #
    #         division_name = False
    #         section_name = False
    #         department_name = False
    #         category_name = False
    #
    #         if category and category.display_name:
    #             # Split hierarchy
    #             parts = [p.strip() for p in category.display_name.split("/")]
    #
    #             division_name = " / ".join(parts[:1]) if len(parts) >= 1 else False
    #             section_name = " / ".join(parts[:2]) if len(parts) >= 2 else False
    #             department_name = " / ".join(parts[:3]) if len(parts) >= 3 else False
    #             category_name = " / ".join(parts[:4]) if len(parts) >= 4 else False
    #
    #         self.env['inventory.movement.report'].create({
    #             'product_id': product_id,
    #             'receipt_qty': values['receipt_qty'],
    #             'receipt_rs_total': values['receipt_rs_total'],
    #
    #             'delivery_qty': values['delivery_qty'],
    #             'delivery_rs_total': values['delivery_rs_total'],
    #
    #             'maintodamage_qty': values['maintodamage_qty'],
    #             'maintodamage_rs_total': values['maintodamage_rs_total'],
    #
    #             'goodsreturn_damage_qty': values['goodsreturn_damage_qty'],
    #             'goodsreturn_damage_rs_total': values['goodsreturn_damage_rs_total'],
    #
    #             'damagetomain_qty': values['damagetomain_qty'],
    #             'damagetomain_rs_total': values['damagetomain_rs_total'],
    #
    #             'pos_order_qty': values['pos_order_qty'],
    #             'pos_order_rs_total': values['pos_order_rs_total'],
    #
    #             'pos_exchange_qty': values['pos_exchange_qty'],
    #             'pos_exchange_rs_total': values['pos_exchange_rs_total'],
    #
    #             'pos_return_qty': values['pos_return_qty'],
    #             'pos_return_rs_total': values['pos_return_rs_total'],
    #             # 'receipt_qty': values['receipt_qty'],
    #             # 'delivery_qty': values['delivery_qty'],
    #             # 'maintodamage_qty': values['maintodamage_qty'],
    #             # 'goodsreturn_damage_qty': values['goodsreturn_damage_qty'],
    #             # 'damagetomain_qty': values['damagetomain_qty'],
    #             # 'pos_order_qty': values['pos_order_qty'],
    #             # 'pos_exchange_qty': values['pos_exchange_qty'],
    #             # 'pos_return_qty': values['pos_return_qty'],
    #             'division_name': division_name,
    #             'section_name': section_name,
    #             'department_name': department_name,
    #             'category_name': category_name,
    #             'from_date': self.from_date,
    #             'to_date': self.to_date,
    #         })
    #
    #     return self.env.ref('nhcl_customizations.action_inventory_movement_report').read()[0]

####### from and to date filtration and without also get from first to last data moves
    # def action_generate(self):
    #
    #     # 1️ Validate dates
    #     if self.from_date and self.to_date:
    #         if self.from_date > self.to_date:
    #             raise ValidationError("From Date cannot be greater than To Date.")
    #
    #     # 2️ Remove old report data
    #     self.env['inventory.movement.report'].search([]).unlink()
    #
    #     # 3️ Build domain dynamically
    #     domain = [
    #         ('state', '=', 'done'),
    #         ('product_id.detailed_type', '=', 'product'),
    #     ]
    #
    #     if self.from_date:
    #         domain.append(('picking_id.date_done', '>=', self.from_date))
    #
    #     if self.to_date:
    #         domain.append(('picking_id.date_done', '<=', self.to_date))
    #
    #     moves = self.env['stock.move'].search(domain)
    #
    #     product_data = {}
    #
    #     # 4️ Loop moves
    #     for move in moves:
    #
    #         product = move.product_id
    #         picking_type = move.picking_id.stock_picking_type
    #         qty = move.quantity
    #
    #         # Sum rs_price from move lines
    #         rs_total = sum(line.rs_price for line in move.move_line_ids)
    #
    #         if product.id not in product_data:
    #             product_data[product.id] = {
    #                 'receipt_qty': 0.0, 'receipt_rs_total': 0.0,
    #                 'delivery_qty': 0.0, 'delivery_rs_total': 0.0,
    #                 'maintodamage_qty': 0.0, 'maintodamage_rs_total': 0.0,
    #                 'goodsreturn_damage_qty': 0.0, 'goodsreturn_damage_rs_total': 0.0,
    #                 'damagetomain_qty': 0.0, 'damagetomain_rs_total': 0.0,
    #                 'pos_order_qty': 0.0, 'pos_order_rs_total': 0.0,
    #                 'pos_exchange_qty': 0.0, 'pos_exchange_rs_total': 0.0,
    #                 'pos_return_qty': 0.0, 'pos_return_rs_total': 0.0,
    #             }
    #
    #         if picking_type == 'receipt':
    #             product_data[product.id]['receipt_qty'] += qty
    #             product_data[product.id]['receipt_rs_total'] += rs_total
    #
    #         elif picking_type == 'return':
    #             product_data[product.id]['delivery_qty'] += qty
    #             product_data[product.id]['delivery_rs_total'] += rs_total
    #
    #         elif picking_type == 'main_damage':
    #             product_data[product.id]['maintodamage_qty'] += qty
    #             product_data[product.id]['maintodamage_rs_total'] += rs_total
    #
    #         elif picking_type == 'damage':
    #             product_data[product.id]['goodsreturn_damage_qty'] += qty
    #             product_data[product.id]['goodsreturn_damage_rs_total'] += rs_total
    #
    #         elif picking_type == 'damage_main':
    #             product_data[product.id]['damagetomain_qty'] += qty
    #             product_data[product.id]['damagetomain_rs_total'] += rs_total
    #
    #         elif picking_type == 'pos_order':
    #             product_data[product.id]['pos_order_qty'] += qty
    #             product_data[product.id]['pos_order_rs_total'] += rs_total
    #
    #         elif picking_type == 'exchange':
    #             product_data[product.id]['pos_exchange_qty'] += qty
    #             product_data[product.id]['pos_exchange_rs_total'] += rs_total
    #
    #         elif picking_type == 'return_main':
    #             product_data[product.id]['pos_return_qty'] += qty
    #             product_data[product.id]['pos_return_rs_total'] += rs_total
    #
    #     # 5️ Create report records
    #     for product_id, values in product_data.items():
    #
    #         product = self.env['product.product'].browse(product_id)
    #         category = product.categ_id
    #
    #         division_name = False
    #         section_name = False
    #         department_name = False
    #         category_name = False
    #
    #         if category and category.display_name:
    #             parts = [p.strip() for p in category.display_name.split("/")]
    #
    #             division_name = " / ".join(parts[:1]) if len(parts) >= 1 else False
    #             section_name = " / ".join(parts[:2]) if len(parts) >= 2 else False
    #             department_name = " / ".join(parts[:3]) if len(parts) >= 3 else False
    #             category_name = " / ".join(parts[:4]) if len(parts) >= 4 else False
    #
    #         self.env['inventory.movement.report'].create({
    #             'product_id': product_id,
    #             'from_date': self.from_date,
    #             'to_date': self.to_date,
    #
    #             'receipt_qty': values['receipt_qty'],
    #             'receipt_rs_total': values['receipt_rs_total'],
    #
    #             'delivery_qty': values['delivery_qty'],
    #             'delivery_rs_total': values['delivery_rs_total'],
    #
    #             'maintodamage_qty': values['maintodamage_qty'],
    #             'maintodamage_rs_total': values['maintodamage_rs_total'],
    #
    #             'goodsreturn_damage_qty': values['goodsreturn_damage_qty'],
    #             'goodsreturn_damage_rs_total': values['goodsreturn_damage_rs_total'],
    #
    #             'damagetomain_qty': values['damagetomain_qty'],
    #             'damagetomain_rs_total': values['damagetomain_rs_total'],
    #
    #             'pos_order_qty': values['pos_order_qty'],
    #             'pos_order_rs_total': values['pos_order_rs_total'],
    #
    #             'pos_exchange_qty': values['pos_exchange_qty'],
    #             'pos_exchange_rs_total': values['pos_exchange_rs_total'],
    #
    #             'pos_return_qty': values['pos_return_qty'],
    #             'pos_return_rs_total': values['pos_return_rs_total'],
    #
    #             'division_name': division_name,
    #             'section_name': section_name,
    #             'department_name': department_name,
    #             'category_name': category_name,
    #         })
    #
    #     # 6️ Return main action (keeps search filters)
    #     return self.env.ref(
    #         'nhcl_customizations.action_inventory_movement_report'
    #     ).read()[0]



    def action_generate(self):

        # Validate
        if self.from_date and self.to_date:
            if self.from_date > self.to_date:
                raise ValidationError("From Date cannot be greater than To Date.")

        self.env['inventory.movement.report'].search([]).unlink()

        # Base domain
        base_domain = [
            ('state', '=', 'done'),
            ('product_id.detailed_type', '=', 'product'),
        ]

        if self.from_date:
            from_dt = datetime.combine(self.from_date, time.min)
            base_domain.append(('picking_id.date_done', '>=', from_dt))

        if self.to_date:
            to_dt = datetime.combine(self.to_date, time.max)
            base_domain.append(('picking_id.date_done', '<=', to_dt))

        # All picking types
        picking_types = [
            'receipt',
            'return',
            'main_damage',
            'damage',
            'damage_main',
            'pos_order',
            'exchange',
            'return_main',
        ]

        product_data = {}

        for ptype in picking_types:

            domain = base_domain + [
                ('picking_id.stock_picking_type', '=', ptype)
            ]

            qty_data = self.env['stock.move'].read_group(
                domain,
                ['quantity:sum'],
                ['product_id'],
                lazy=False
            )

            rsp_domain = [
                ('move_id.state', '=', 'done'),
                ('move_id.product_id.detailed_type', '=', 'product'),
                ('move_id.picking_id.stock_picking_type', '=', ptype),
            ]

            if self.from_date:
                rsp_domain.append(('move_id.picking_id.date_done', '>=', from_dt))

            if self.to_date:
                rsp_domain.append(('move_id.picking_id.date_done', '<=', to_dt))

            rsp_data = self.env['stock.move.line'].read_group(
                rsp_domain,
                ['rs_price:sum'],
                ['product_id'],
                lazy=False
            )

            # Convert rsp to dict
            rsp_dict = {
                data['product_id'][0]: data['rs_price']
                for data in rsp_data if data.get('product_id')
            }

            for data in qty_data:

                product_id = data['product_id'][0]
                qty = data['quantity']
                rs_total = rsp_dict.get(product_id, 0.0)

                if product_id not in product_data:
                    product_data[product_id] = {
                        'receipt_qty': 0.0, 'receipt_rs_total': 0.0,
                        'delivery_qty': 0.0, 'delivery_rs_total': 0.0,
                        'maintodamage_qty': 0.0, 'maintodamage_rs_total': 0.0,
                        'goodsreturn_damage_qty': 0.0, 'goodsreturn_damage_rs_total': 0.0,
                        'damagetomain_qty': 0.0, 'damagetomain_rs_total': 0.0,
                        'pos_order_qty': 0.0, 'pos_order_rs_total': 0.0,
                        'pos_exchange_qty': 0.0, 'pos_exchange_rs_total': 0.0,
                        'pos_return_qty': 0.0, 'pos_return_rs_total': 0.0,
                    }

                if ptype == 'receipt':
                    product_data[product_id]['receipt_qty'] = qty
                    product_data[product_id]['receipt_rs_total'] = rs_total

                elif ptype == 'return':
                    product_data[product_id]['delivery_qty'] = qty
                    product_data[product_id]['delivery_rs_total'] = rs_total

                elif ptype == 'main_damage':
                    product_data[product_id]['maintodamage_qty'] = qty
                    product_data[product_id]['maintodamage_rs_total'] = rs_total

                elif ptype == 'damage':
                    product_data[product_id]['goodsreturn_damage_qty'] = qty
                    product_data[product_id]['goodsreturn_damage_rs_total'] = rs_total

                elif ptype == 'damage_main':
                    product_data[product_id]['damagetomain_qty'] = qty
                    product_data[product_id]['damagetomain_rs_total'] = rs_total

                elif ptype == 'pos_order':
                    product_data[product_id]['pos_order_qty'] = qty
                    product_data[product_id]['pos_order_rs_total'] = rs_total

                elif ptype == 'exchange':
                    product_data[product_id]['pos_exchange_qty'] = qty
                    product_data[product_id]['pos_exchange_rs_total'] = rs_total

                elif ptype == 'return_main':
                    product_data[product_id]['pos_return_qty'] = qty
                    product_data[product_id]['pos_return_rs_total'] = rs_total

        # Create records
        for product_id, values in product_data.items():
            product = self.env['product.product'].browse(product_id)
            category = product.categ_id

            parts = category.display_name.split("/") if category else []

            division_name = parts[0].strip() if len(parts) >= 1 else False
            section_name = " / ".join(parts[:2]) if len(parts) >= 2 else False
            department_name = " / ".join(parts[:3]) if len(parts) >= 3 else False
            category_name = " / ".join(parts[:4]) if len(parts) >= 4 else False

            self.env['inventory.movement.report'].create({
                'product_id': product_id,
                'from_date': self.from_date,
                'to_date': self.to_date,

                'receipt_qty': values['receipt_qty'],
                'receipt_rs_total': values['receipt_rs_total'],

                'delivery_qty': values['delivery_qty'],
                'delivery_rs_total': values['delivery_rs_total'],

                'maintodamage_qty': values['maintodamage_qty'],
                'maintodamage_rs_total': values['maintodamage_rs_total'],

                'goodsreturn_damage_qty': values['goodsreturn_damage_qty'],
                'goodsreturn_damage_rs_total': values['goodsreturn_damage_rs_total'],

                'damagetomain_qty': values['damagetomain_qty'],
                'damagetomain_rs_total': values['damagetomain_rs_total'],

                'pos_order_qty': values['pos_order_qty'],
                'pos_order_rs_total': values['pos_order_rs_total'],

                'pos_exchange_qty': values['pos_exchange_qty'],
                'pos_exchange_rs_total': values['pos_exchange_rs_total'],

                'pos_return_qty': values['pos_return_qty'],
                'pos_return_rs_total': values['pos_return_rs_total'],

                'division_name': division_name,
                'section_name': section_name,
                'department_name': department_name,
                'category_name': category_name,
            })

        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }