from odoo import models,api,fields,_
import requests
import logging

from odoo.exceptions import ValidationError

_logger = logging.getLogger(__name__)
from datetime import datetime

class PosOrder(models.Model):
    _inherit = 'pos.order'

    nhcl_status = fields.Boolean('Replication Status', default=False, copy=False)

    def pos_orders_invoice(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])

        for ho in ho_id:
            try:
                ho_ip = ho.nhcl_terminal_ip
                ho_port = ho.nhcl_port_no
                store_api_key = ho.nhcl_api_key
                headers_source = {'api-key': f"{store_api_key}", 'Content-Type': 'application/json'}
                ho_pick_validate_url = f"http://{ho_ip}:{ho_port}/api/pos.order/call_action"
                ho_pick_data = requests.post(ho_pick_validate_url, json={}, headers=headers_source)
                ho_pick_data.raise_for_status()
                print("ho_pick_data",ho_pick_data)
                # Access the JSON content from the response
                ho_pick_vals = ho_pick_data.json()
            except Exception as e:
                ho.create_cmr_transaction_server_replication_log("failure", e)

    def send_pos_order_data_to_ho(self):
        ho_id = self.env['nhcl.ho.store.master'].search([('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True)])
        if ho_id:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            api_key = ho_id.nhcl_api_key
            headers_source = {'api-key': f"{api_key}", 'Content_Type': 'application/json'}
            pending_pos_orders = self.env['pos.order'].search([('nhcl_status', '=', False), ('state','=','invoiced')])
            for pos_order in pending_pos_orders:
                try:
                    # -------------------- Company --------------------
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', pos_order.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")

                    if not company_id:
                        msg = f"Company not found for POS Order {pos_order.name}"
                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)

                    # -------------------- Session --------------------
                    session_search = f"http://{ho_ip}:{ho_port}/api/pos.session/search"
                    session_domain = [('company_id', '=', company_id[0]['id'])]
                    session_url = f"{session_search}?domain={session_domain}"
                    session_data = requests.get(session_url, headers=headers_source).json()
                    session_id = session_data.get("data")

                    if not session_id:
                        msg = f"Company not found for Session {pos_order.name}"
                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)

                    # -------------------- Cashier --------------------

                    ho_cashier_url = f"http://{ho_ip}:{ho_port}/api/hr.employee/search"
                    ho_cashier_domain = [
                        ('nhcl_id', '=', pos_order.employee_id.nhcl_id),
                        ('company_id', '=', company_id[0]['id'])
                    ]
                    cashier_url = f"{ho_cashier_url}?domain={ho_cashier_domain}"
                    ho_cashier_data = requests.get(cashier_url, headers=headers_source).json()
                    cashier_data = ho_cashier_data.get('data')
                    cashier_id = False
                    if cashier_data:
                        cashier_id = cashier_data[0]['id']
                    if not cashier_data:
                        msg = f"Company not found for Cashier {pos_order.name}"
                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)

                    # Fetch or create the partner in HO
                    partner_url = f"http://{ho_ip}:{ho_port}/api/res.partner/search?domain=[('name','=', '{pos_order.partner_id.name}'),('phone','=', '{pos_order.partner_id.phone}')]"
                    partner_data = requests.get(partner_url, headers=headers_source).json()
                    partner = partner_data.get("data", [])
                    new_partner = False
                    if not partner:
                        partner_data = {
                            'name': pos_order.partner_id.name,
                            'phone': pos_order.partner_id.phone,
                        }
                        partner_create_url = f"http://{ho_ip}:{ho_port}/api/res.partner/create"
                        partner_create_response = requests.post(partner_create_url, headers=headers_source,
                                                                json=[partner_data])
                        partner_create_response.raise_for_status()
                        new_partner = partner_create_response.json().get("create_id")

                    partner_id = partner[0]['id'] if partner else new_partner
                    branch_pos_order_search = f"http://{ho_ip}:{ho_port}/api/pos.order/search"
                    branch_pos_order_domain = [('name', '=', pos_order.name), ('company_id', '=', company_id[0]['id'])]
                    branch_pos_order_url = f"{branch_pos_order_search}?domain={branch_pos_order_domain}"
                    branch_pos_order_data = requests.get(branch_pos_order_url, headers=headers_source).json()
                    branch_pos_order = branch_pos_order_data.get("data")
                    pos_line = []

                    for line in pos_order.lines:
                        ho_product_url = f"http://{ho_ip}:{ho_port}/api/product.product/search"
                        if line.product_id.detailed_type == 'service':
                            ho_product_domain = [('name', 'ilike', line.product_id.name)]
                        else:
                            ho_product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                        product_url = f"{ho_product_url}?domain={ho_product_domain}"
                        ho_product_data = requests.get(product_url, headers=headers_source).json()
                        product_data = ho_product_data.get('data')
                        product_id = False
                        if product_data:
                            product_id = product_data[0]["id"]
                        if not product_id:
                            msg = f"Product not found for {line.product_id.name} In {pos_order.name}"
                            ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                        if line.product_id.detailed_type != 'service':
                            ho_employee_url = f"http://{ho_ip}:{ho_port}/api/hr.employee/search"
                            ho_employee_domain = [
                                ('nhcl_id', '=', line.employ_id.nhcl_id),
                                ('company_id', '=', company_id[0]['id'])
                            ]
                            employee_url = f"{ho_employee_url}?domain={ho_employee_domain}"
                            ho_employee_data = requests.get(employee_url, headers=headers_source).json()
                            employee_data = ho_employee_data.get('data')
                            employee_id = False
                            if employee_data:
                                employee_id = employee_data[0]['id']

                            tax_ids = []
                            for tax in line.tax_ids:
                                tax_url_data = f"http://{ho_ip}:{ho_port}/api/account.tax/search"
                                tax_domain = [('name', '=', f"{tax.name}-CREDIT"),
                                              ('company_id', '=', company_id[0]['id']),
                                              ('nhcl_creadit_note_tax', '=', True)]
                                tax_id_url = f"{tax_url_data}?domain={tax_domain}"
                                ho_tax_data = requests.get(tax_id_url, headers=headers_source).json()
                                tax_data = ho_tax_data.get("data")
                                tax_id = False
                                if tax_data:
                                    tax_id = tax_data[0]
                                if not tax_id and company_id:
                                    # Fetch parent account if not found
                                    parent_tax_url_data = f"http://{ho_ip}:{ho_port}/api/account.tax/search"
                                    parent_tax_domain = [('name', '=', f"{tax.name}-CREDIT"),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id']),
                                                         ('nhcl_creadit_note_tax', '=', True)]
                                    parent_tax_id_url = f"{parent_tax_url_data}?domain={parent_tax_domain}"
                                    parent_tax_data = requests.get(parent_tax_id_url, headers=headers_source).json()
                                    tax_data = parent_tax_data.get("data")
                                    tax_id = tax_data[0]
                                tax_ids.append(tax_id['id'])
                            lot_ids = []
                            for lot in line.pack_lot_ids:
                                pack_operation = self.env['pos.pack.operation.lot'].search([('id', '=', lot.id)], limit=1)
                                lot_url_data = f"http://{ho_ip}:{ho_port}/api/stock.lot/search"
                                lot_domain = [('name', '=', pack_operation.lot_name),
                                              ('company_id', '=', company_id[0]['id'])]
                                lot_id_url = f"{lot_url_data}?domain={lot_domain}"
                                lot_data = requests.get(lot_id_url, headers=headers_source).json()

                                if lot_data.get("data"):
                                    lot_ids.append(lot_data["data"][0]['id'])

                                pos_order_line = {
                                    "full_product_name": line.full_product_name,
                                    "product_id": product_id,
                                    "qty": line.qty,
                                    "price_unit": line.price_unit,
                                    "price_subtotal": line.price_subtotal,
                                    "price_subtotal_incl": line.price_subtotal_incl,
                                    "tax_ids": tax_ids if line.tax_ids else False,
                                    "lot_ids": lot_ids if line.pack_lot_ids else False,
                                    "employ_id": employee_id,
                                    "gdiscount": line.gdiscount,
                                    "nhcl_cost_price": line.nhcl_cost_price,
                                    "nhcl_rs_price": line.nhcl_rs_price,
                                    "nhcl_mr_price": line.nhcl_mr_price,
                                    "discount": line.discount,
                                }

                                pos_line.append((0, 0, pos_order_line))

                        # ---------------- Product Line Creation ----------------
                        if line.product_id.detailed_type == 'service':
                            pos_order_line = {
                                "full_product_name": line.full_product_name,
                                "product_id": product_id,
                                "qty": line.qty,
                                "price_unit": line.price_unit,
                                "price_subtotal": line.price_subtotal,
                                "price_subtotal_incl": line.price_subtotal_incl,
                            }
                            pos_line.append((0, 0, pos_order_line))

                    payment_data = []
                    for payment in pos_order.payment_ids:
                        ho_payment_method_url = f"http://{ho_ip}:{ho_port}/api/pos.payment.method/search"
                        ho_payment_method_domain = [('name', '=', payment.payment_method_id.name), ('company_id', '=', company_id[0]['id'])]
                        payment_method_url = f"{ho_payment_method_url}?domain={ho_payment_method_domain}"
                        ho_payment_method_data = requests.get(payment_method_url, headers=headers_source).json()
                        payment_method_data = ho_payment_method_data.get('data')
                        pos_payment_vals = {
                            "payment_date" : payment.payment_date.strftime('%Y-%m-%d %H:%M:%S'),
                            "payment_method_id": payment_method_data[0]['id'],
                            "amount": payment.amount,

                        }
                        payment_data.append((0,0,pos_payment_vals))
                    if not branch_pos_order:
                        pos_order_vals = {
                            "partner_id": partner_id,
                            "name": pos_order.name,
                            "pos_reference": pos_order.pos_reference,
                            "tracking_number": pos_order.tracking_number,
                            "session_id" : session_id[0]['id'],
                            "amount_tax" : pos_order.amount_tax,
                            "amount_total" : pos_order.amount_total,
                            "amount_paid" : pos_order.amount_paid,
                            "amount_return" : pos_order.amount_return,
                            "company_id": company_id[0]['id'],
                            "lines": pos_line,
                            "payment_ids" : payment_data,
                            "state" : "paid",
                            "nhcl_store_je" : True,
                            "date_order": pos_order.date_order.strftime('%Y-%m-%d %H:%M:%S'),
                            "employee_id": cashier_id,
                        }
                        branch_pos_order_create_url = f"http://{ho_ip}:{ho_port}/api/pos.order/create"
                        try:
                            branch_pos_data = requests.post(branch_pos_order_create_url, headers=headers_source, json=[pos_order_vals])
                            branch_pos_data.raise_for_status()
                            pos_responsc = branch_pos_data.json()
                            if pos_responsc and pos_responsc['success']:
                                pos_order.nhcl_status = True
                                pos_order_id = pos_responsc.get("create_id")
                                for picking in pos_order.picking_ids:
                                    # -------------------- Picking Type --------------------
                                    picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
                                    picking_type_domain = [('stock_picking_type', '=', picking.picking_type_id.stock_picking_type),
                                                           ('company_id', '=', company_id[0]['id'])]
                                    picking_type_data = requests.get(
                                        f"{picking_type_url}?domain={picking_type_domain}", headers=headers_source
                                    ).json()
                                    picking_type = picking_type_data.get("data")
                                    if not picking_type:
                                        msg = f"Picking Type not found for company {pos_order.company_id.name}"
                                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                                        continue
                                    # -------------------- Source Location --------------------
                                    location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                                    location_domain = [
                                        ('name', '=', picking.location_id.name),
                                        ('active', '!=', False),
                                        ('usage', '=', 'internal'),
                                        ('company_id', '=', company_id[0]['id'])
                                    ]
                                    location_data = requests.get(
                                        f"{location_url}?domain={location_domain}&fields=['name','id']", headers=headers_source
                                    ).json()
                                    location_id = location_data.get("data")
                                    if not location_id:
                                        msg = f"Source Location not found for order: {picking.name}"
                                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                                        continue

                                    # -------------------- Destination Location --------------------
                                    dest_location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                                    dest_domain = [
                                        ('complete_name', '=', picking.location_dest_id.complete_name),
                                        ('active', '!=', False),
                                        ('usage', '=', 'customer')
                                    ]
                                    dest_data = requests.get(
                                        f"{dest_location_url}?domain={dest_domain}&fields=['name','id']", headers=headers_source
                                    ).json()
                                    dest_location = dest_data.get("data")
                                    if not dest_location:
                                        msg = f"Destination Location not found for order: {picking.name}"
                                        ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                                        continue
                                    move_line = []
                                    for line in picking.move_line_ids_without_package:
                                        try:
                                            product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                                            product_data = requests.get(
                                                f"http://{ho_ip}:{ho_port}/api/product.product/search?domain={product_domain}",
                                                headers=headers_source
                                            ).json()
                                            product_id = product_data.get("data")
                                            if not product_id:
                                                msg = f"Product not found for {line.product_id.display_name} in order {picking.name}"
                                                ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                                                continue

                                            lot_name = line.lot_id.name if line.lot_id else None
                                            move_line_vals = {
                                                "product_id": product_id[0]['id'],
                                                "quantity": line.quantity,
                                                "location_id": location_id[0]['id'],
                                                "location_dest_id": dest_location[0]["id"],
                                                "lot_name": lot_name,
                                            }
                                            move_line.append((0,0,move_line_vals))
                                        except requests.exceptions.RequestException as e:
                                            logging.error(f"Error while creating Pos Order for {picking.name}: {str(e)}")
                                            ho_id.create_cmr_transaction_server_replication_log("failure", str(e))
                                    branch_picking_order_search = f"http://{ho_ip}:{ho_port}/api/stock.picking/search"
                                    branch_picking_order_domain = [('origin', '=', picking.name),
                                                               ('company_id', '=', company_id[0]['id'])]
                                    branch_picking_order_url = f"{branch_picking_order_search}?domain={branch_picking_order_domain}"
                                    branch_picking_order_data = requests.get(branch_picking_order_url,
                                                                         headers=headers_source).json()
                                    branch_picking_order = branch_picking_order_data.get("data")
                                    if not branch_picking_order:
                                        # -------------------- Create Picking --------------------
                                        stock_picking_vals = {
                                            'picking_type_id': picking_type[0]['id'],
                                            'origin': picking.name,
                                            "partner_id": partner_id,
                                            'location_id': location_id[0]['id'],
                                            'location_dest_id': dest_location[0]['id'],
                                            'company_id': company_id[0]['id'],
                                            'move_type': 'direct',
                                            'state': 'done',
                                            'nhcl_store_delivery': True,
                                            'move_line_ids_without_package': move_line,
                                            'pos_order_id': pos_order_id,
                                            'scheduled_date': picking.scheduled_date.strftime('%Y-%m-%d %H:%M:%S'),
                                        }
                                        try:
                                            picking_response = requests.post(
                                                f"http://{ho_ip}:{ho_port}/api/stock.picking/create",
                                                headers=headers_source, json=[stock_picking_vals]
                                            )
                                            picking_response.raise_for_status()
                                            stock_picking = picking_response.json()
                                            if stock_picking and stock_picking['success']:
                                                # -------------------- Success Marking --------------------
                                                picking.nhcl_replication_status = True
                                                picking.validate_orders(deliver_order='pos_order')
                                                msg = f"Delivery Order successfully created for {picking.name}"
                                                ho_id.create_cmr_transaction_server_replication_log("success", msg)
                                        except Exception as req_err:
                                            msg = f"Error creating picking for {picking.name}: {req_err}"
                                            ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                                            continue
                                try:
                                    pos_order.pos_orders_invoice()
                                except Exception as req_err:
                                    msg = f"Error creating Invoice for {pos_order.name}: {req_err}"
                                    ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                            else:
                                logging.error(f"Failed to create Pos Order {pos_order.name}. Response: {pos_responsc}")
                                ho_id.create_cmr_transaction_server_replication_log("failure", str(pos_responsc))

                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error while creating Pos Order for {pos_order.name}: {str(e)}")
                            ho_id.create_cmr_transaction_server_replication_log("failure", str(e))

                except Exception as e:
                    msg = f"Unexpected error while processing {pos_order.name}: {e}"
                    ho_id.create_cmr_transaction_server_replication_log("failure", msg)
                    continue

        return True

    def get_pos_journal_entry(self):
        ho_ids = self.env['nhcl.ho.store.master'].search([
            ('nhcl_store_type', '=', 'ho'),
            ('nhcl_active', '=', True)
        ])

        for ho in ho_ids:
            ho_ip = ho.nhcl_terminal_ip
            ho_port = ho.nhcl_port_no
            ho_api_key = ho.nhcl_api_key
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}

            store_journal_entries = self.env['account.move'].search([
                ('nhcl_replication_status', '=', False)
            ])

            if not store_journal_entries:
                continue

            for entry in store_journal_entries:
                if entry.journal_id.name != "Credit Note Issue":
                    try:
                        # -------------------- Company --------------------
                        company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                        company_domain = [('name', '=', entry.company_id.name)]
                        company_url = f"{company_search}?domain={company_domain}"
                        company_data = requests.get(company_url, headers=headers_source).json()
                        company_id = company_data.get("data")

                        if not company_id:
                            msg = f"Company not found for Journal Entry {entry.name}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        # -------------------- Journal --------------------
                        journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        journal_domain = [('name', '=', entry.journal_id.name), ('company_id', '=', company_id[0]['id'])]
                        journal_url = f"{journal_search}?domain={journal_domain}"
                        journal_data = requests.get(journal_url, headers=headers_source).json()
                        account_journal = journal_data.get("data")

                        # Fallback: try parent company
                        if not account_journal and company_id and company_id[0].get('parent_id'):
                            parent_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                            parent_journal_domain = [
                                ('name', '=', entry.journal_id.name),
                                ('company_id.name', '=', company_id[0]['parent_id'][0]['name'])
                            ]
                            parent_journal_url = f"{parent_journal_search}?domain={parent_journal_domain}"
                            parent_journal_data = requests.get(parent_journal_url, headers=headers_source).json()
                            account_journal = parent_journal_data.get("data")

                        if not account_journal:
                            msg = f"Journal not found for entry {entry.name}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        # -------------------- Prepare Move Lines --------------------
                        invoice_lines = []
                        for line in entry.line_ids:
                            try:
                                account_search = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                                account_domain = [
                                    ('name', '=', line.account_id.name),
                                    ('company_id', '=', company_id[0]['id'])
                                ]
                                account_url = f"{account_search}?domain={account_domain}"
                                account_data = requests.get(account_url, headers=headers_source).json()
                                account_id = account_data.get("data")

                                # Fallback: try parent company
                                if not account_id and company_id and company_id[0].get('parent_id'):
                                    parent_account_search = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                                    parent_account_domain = [
                                        ('name', '=', line.account_id.name),
                                        ('company_id', '=', company_id[0]['parent_id'][0]['id'])
                                    ]
                                    parent_account_url = f"{parent_account_search}?domain={parent_account_domain}"
                                    parent_account_data = requests.get(parent_account_url, headers=headers_source).json()
                                    account_id = parent_account_data.get("data")

                                if not account_id:
                                    msg = f"Account not found for line '{line.name}' in entry {entry.name}"
                                    ho.create_cmr_transaction_server_replication_log("failure", msg)
                                    continue

                                invoice_lines.append((0, 0, {
                                    "name": line.name or '',
                                    "account_id": account_id[0]['id'],
                                    "debit": line.debit,
                                    "credit": line.credit,
                                }))
                            except Exception as line_err:
                                msg = f"Error processing line in entry {entry.name}: {line_err}"
                                ho.create_cmr_transaction_server_replication_log("failure", msg)
                                continue

                        if not invoice_lines:
                            msg = f"No valid account lines found for entry {entry.name}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        # -------------------- Check if already exists --------------------
                        if entry.journal_id.name == "Cash":
                            move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                            move_domain = [('name', '=', entry.name), ('company_id', '=', company_id[0]['id'])]
                            move_url = f"{move_search}?domain={move_domain}"
                            move_data = requests.get(move_url, headers=headers_source).json()
                            existing_move = move_data.get("data")
                        else:
                            move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                            move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                            move_url = f"{move_search}?domain={move_domain}"
                            move_data = requests.get(move_url, headers=headers_source).json()
                            existing_move = move_data.get("data")
                        if existing_move:
                            msg = f"Journal Entry {entry.name} already exists in HO"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        # -------------------- Create Journal Entry --------------------
                        move_vals = {
                            "name": entry.name,
                            "ref": entry.ref,
                            "date": entry.date.strftime("%Y-%m-%d"),
                            "move_type": entry.move_type,
                            "journal_id": account_journal[0]['id'],
                            "amount_total": entry.amount_total,
                            "company_id": company_id[0]['id'],
                            'nhcl_store_je': True,
                            'line_ids': invoice_lines
                        }

                        try:
                            ho_move_url = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            move_response = requests.post(ho_move_url, headers=headers_source, json=[move_vals])
                            move_response.raise_for_status()
                            response_json = move_response.json()

                            if response_json.get("success"):
                                entry.nhcl_replication_status = True
                                msg = f"Successfully created Journal Entry {entry.name}"
                                ho.create_cmr_transaction_server_replication_log("success", msg)
                                ho.create_cmr_transaction_replication_log(
                                    response_json['object_name'], entry.id, 200, 'add', 'success', msg
                                )
                            else:
                                msg = f"Failed to create Journal Entry {entry.name}: {response_json.get('message', '')}"
                                ho.create_cmr_transaction_server_replication_log("failure", msg)
                                ho.create_cmr_transaction_replication_log(
                                    response_json.get('object_name', 'account.move'), entry.id, 200, 'add', 'failure', msg
                                )

                        except Exception as api_err:
                            msg = f"API Error creating entry {entry.name}: {api_err}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                    except Exception as entry_err:
                        msg = f"Unexpected error while processing {entry.name}: {entry_err}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue
        return True

    def get_pos_crediet_note_issue_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])

        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Credit Note Issue")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])

            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}

            if store_journal_entry:
                for entry in store_journal_entry:
                    print("Processing entry:", entry)

                    # Fetch company details
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    print('entry',entry.name)
                    # Fetch the corresponding journal entry
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Credit Note Issue'),
                                              ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")

                    if not account_journal and company_id and company_id[0]['parent_id']:
                        # Fetch parent journal entry if not found
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Credit Note Issue'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")

                    # Fetch or create the partner in HO
                    partner_url = f"http://{ho_ip}:{ho_port}/api/res.partner/search?domain=[('name','=', '{entry.partner_id.name}'),('phone','=', '{entry.partner_id.phone}')]"
                    partner_data = requests.get(partner_url, headers=headers_source).json()
                    partner = partner_data.get("data", [])
                    new_partner = False
                    if not partner:
                        partner_data = {
                            'name': entry.partner_id.name,
                            'phone': entry.partner_id.phone,
                            # 'company_id': company_id
                        }
                        partner_create_url = f"http://{ho_ip}:{ho_port}/api/res.partner/create"
                        partner_create_response = requests.post(partner_create_url, headers=headers_source,
                                                                json=[partner_data])
                        partner_create_response.raise_for_status()
                        new_partner = partner_create_response.json().get("create_id")

                    partner_id = partner[0]['id'] if partner else new_partner

                    # Prepare invoice lines
                    invoice_lines = []
                    service = entry.invoice_line_ids.filtered_domain(
                        [('product_id.detailed_type', '=', 'service')])

                    for line in entry.invoice_line_ids:
                        if service:
                            product_domain = [('name', '=', line.product_id.name)]
                        else:
                            product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                        product_url = f"http://{ho_ip}:{ho_port}/api/product.product/search?domain={product_domain}"
                        product_data = requests.get(product_url, headers=headers_source).json()
                        product_id = product_data.get("data", [])

                        if not product_id:
                            logging.warning(
                                f"Product {line.product_id.name} not found in HO. Skipping move line for order {entry.name}.")
                            continue

                        product_id = product_id[0]['id']
                        tax_ids = False
                        if not service:
                            # Handle tax IDs
                            tax_url_data = f"http://{ho_ip}:{ho_port}/api/account.tax/search"
                            tax_domain = [('name', '=', f"{line.tax_ids.name}-CREDIT"), ('company_id', '=', company_id[0]['id']), ('nhcl_creadit_note_tax','=',True)]
                            tax_id_url = f"{tax_url_data}?domain={tax_domain}"
                            account_data = requests.get(tax_id_url, headers=headers_source).json()
                            tax_id = account_data.get("data")
                            if not tax_id and company_id:
                                # Fetch parent account if not found
                                parent_tax_url_data = f"http://{ho_ip}:{ho_port}/api/account.tax/search"
                                parent_tax_domain = [('name', '=', f"{line.tax_ids.name}-CREDIT"),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id']), ('nhcl_creadit_note_tax','=',True)]
                                parent_tax_id_url = f"{parent_tax_url_data}?domain={parent_tax_domain}"
                                parent_tax_data = requests.get(parent_tax_id_url, headers=headers_source).json()
                                tax_id = parent_tax_data.get("data")
                            tax_ids = [(6, 0, [tax['id'] for tax in tax_id])] if tax_id else []

                        # Handle account ID
                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url, headers=headers_source).json()
                        account_id = account_data.get("data")

                        if not account_id and company_id:
                            # Fetch parent account if not found
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url, headers=headers_source).json()
                            account_id = parent_account_data.get("data")

                        # Add invoice line to the list
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "product_id": product_id,
                            "account_id": account_id[0]['id'],
                            "tax_ids": tax_ids if tax_ids else False,
                            "price_unit": line.price_unit,
                            "quantity": line.quantity,
                            # "price_subtotal": line.price_subtotal,
                        }))

                    # Search for existing move
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('name', '=', entry.name), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url, headers=headers_source).json()
                    move_id = account_move_data.get("data")

                    if not move_id:
                        # If no move found, create a new one
                        move_vals = {
                            "partner_id": partner_id,
                            "name": entry.name,
                            "ref": entry.name,
                            "date": entry.date.strftime("%Y-%m-%d"),
                            "move_type": entry.move_type,
                            "journal_id": account_journal[0]['id'],
                            "amount_total": entry.amount_total,
                            "company_id": company_id[0]['id'],
                            'nhcl_store_je': True,
                            'invoice_line_ids': invoice_lines
                        }
                        print("Sending journal entry data:", move_vals)
                        ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                        try:
                            move_data = requests.post(ho_move_url_data, headers=headers_source, json=[move_vals])
                            move_data.raise_for_status()

                            response_json = move_data.json()
                            print('Journal entry creation response:', response_json)

                            if response_json and response_json['success']:
                                entry.nhcl_replication_status = True

                            else:
                                logging.error(f"Failed to create Journal Entry {entry.name}. Response: {response_json}")

                        except requests.exceptions.RequestException as e:
                            logging.error(f"Error while creating journal entry for {entry.name}: {str(e)}")
                            ho_id.create_cmr_transaction_server_replication_log("failure", str(e))

            else:
                logging.info("No journal entries found for replication.")

        except Exception as e:
            logging.error(f"General error during journal entry processing: {str(e)}")
            ho_id.create_cmr_transaction_server_replication_log("failure", str(e))
        return True

    def merge_pos_delivery_orders(self):
        ho_ids = self.env['nhcl.ho.store.master'].search([
            ('nhcl_store_type', '=', 'ho'),
            ('nhcl_active', '=', True)
        ])

        for ho in ho_ids:
            ho_ip = ho.nhcl_terminal_ip
            ho_port = ho.nhcl_port_no
            store_api_key = ho.nhcl_api_key
            headers_source = {'api-key': f"{store_api_key}", 'Content-Type': 'application/json'}

            picking_type_id = self.env['stock.picking.type'].search([('stock_picking_type', '=', "pos_order")])
            store_pos_delivery_orders = self.env['stock.picking'].search([
                ('picking_type_id', '=', picking_type_id.id),
                ('nhcl_replication_status', '=', False),
                ('state', '=', 'done')
            ],limit=5)
            # store_pos_delivery_orders = self.env['stock.picking'].search([
            #     ('name', '=', 'CMR-J/POS-JC/00453'),
            #     ('nhcl_replication_status', '=', False),
            #     ('state', '=', 'done')
            # ])

            for order in store_pos_delivery_orders:
                try:
                    if order.location_dest_id.name != "Customers":
                        continue

                    # -------------------- Company --------------------
                    company_url = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', order.company_id.name)]
                    company_data = requests.get(
                        f"{company_url}?domain={company_domain}", headers=headers_source
                    ).json()
                    company_id = company_data.get("data")
                    if not company_id:
                        msg = f"Company not found for order: {order.name}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue

                    # -------------------- POS Order --------------------
                    pos_order_url = f"http://{ho_ip}:{ho_port}/api/pos.order/search"
                    pos_order_domain = [('name', '=', order.origin)]
                    pos_order_data = requests.get(
                        f"{pos_order_url}?domain={pos_order_domain}", headers=headers_source
                    ).json()
                    pos_id = pos_order_data.get("data")
                    if not pos_id:
                        msg = f"Company not found for POS order: {order.name}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue

                    # -------------------- Picking Type --------------------
                    picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
                    picking_type_domain = [('stock_picking_type', '=', "pos_order"), ('company_id', '=', company_id[0]['id'])]
                    picking_type_data = requests.get(
                        f"{picking_type_url}?domain={picking_type_domain}", headers=headers_source
                    ).json()
                    picking_type = picking_type_data.get("data")
                    if not picking_type:
                        msg = f"Picking Type not found for company {order.company_id.name}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue

                    # -------------------- Source Location --------------------
                    location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                    location_domain = [
                        ('name', '=', order.location_id.name),
                        ('active', '!=', False),
                        ('usage', '=', 'internal'),
                        ('company_id', '=', company_id[0]['id'])
                    ]

                    location_data = requests.get(
                        f"{location_url}?domain={location_domain}&fields=['name','id']", headers=headers_source
                    ).json()
                    location_id = location_data.get("data")
                    if not location_id:
                        msg = f"Source Location not found for order: {order.name}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue

                    # -------------------- Destination Location --------------------
                    dest_location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                    dest_domain = [
                        ('complete_name', '=', order.location_dest_id.complete_name),
                        ('active', '!=', False),
                        ('usage', '=', 'customer')
                    ]
                    dest_data = requests.get(
                        f"{dest_location_url}?domain={dest_domain}&fields=['name','id']", headers=headers_source
                    ).json()
                    dest_location = dest_data.get("data")
                    if not dest_location:
                        msg = f"Destination Location not found for order: {order.name}"
                        ho.create_cmr_transaction_server_replication_log("failure", msg)
                        continue

                    branch_pos_picking_search = f"http://{ho_ip}:{ho_port}/api/stock.picking/search"
                    branch_pos_picking_domain = [('origin', '=', order.name), ('company_id', '=', company_id[0]['id'])]
                    branch_pos_picking_url = f"{branch_pos_picking_search}?domain={branch_pos_picking_domain}"
                    branch_pos_picking_data = requests.get(branch_pos_picking_url, headers=headers_source).json()
                    branch_pos_picking = branch_pos_picking_data.get("data")
                    if branch_pos_picking:
                        order.nhcl_replication_status = True
                    # -------------------- Create Picking --------------------
                    stock_picking_vals = {
                        'picking_type_id': picking_type[0]['id'],
                        'origin': order.name,
                        'location_id': location_id[0]['id'],
                        'location_dest_id': dest_location[0]['id'],
                        'company_id': company_id[0]['id'],
                        'move_type': 'direct',
                        'state': 'done',
                        'pos_order_id': pos_id[0]['id'],
                        'nhcl_store_delivery': True
                    }
                    if not branch_pos_picking:
                        try:
                            picking_response = requests.post(
                                f"http://{ho_ip}:{ho_port}/api/stock.picking/create",
                                headers=headers_source, json=[stock_picking_vals]
                            )
                            picking_response.raise_for_status()
                            stock_picking = picking_response.json()
                        except Exception as req_err:
                            msg = f"Error creating picking for {order.name}: {req_err}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        if not stock_picking.get("success"):
                            msg = f"Picking creation failed for order {order.name}: {stock_picking.get('message')}"
                            ho.create_cmr_transaction_server_replication_log("failure", msg)
                            continue

                        picking_id = stock_picking.get("create_id")

                        # -------------------- Create Move Lines --------------------
                        for line in order.move_line_ids_without_package:
                            try:
                                product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                                product_data = requests.get(
                                    f"http://{ho_ip}:{ho_port}/api/product.product/search?domain={product_domain}",
                                    headers=headers_source
                                ).json()
                                product_id = product_data.get("data")
                                if not product_id:
                                    msg = f"Product not found for {line.product_id.display_name} in order {order.name}"
                                    ho.create_cmr_transaction_server_replication_log("failure", msg)
                                    continue

                                lot_name = line.lot_id.name if line.lot_id else None
                                move_line_vals = {
                                    "picking_id": picking_id,
                                    "product_id": product_id[0]['id'],
                                    "quantity": line.quantity,
                                    'location_id': location_id[0]['id'],
                                    'location_dest_id': dest_location[0]['id'],
                                    "lot_name": lot_name,
                                }

                                move_resp = requests.post(
                                    f"http://{ho_ip}:{ho_port}/api/stock.move.line/create",
                                    headers=headers_source, json=[move_line_vals]
                                )
                                move_resp.raise_for_status()

                            except Exception as line_err:
                                msg = f"Move line creation failed for {order.name}: {line_err}"
                                ho.create_cmr_transaction_server_replication_log("failure", msg)
                                continue

                        # -------------------- Success Marking --------------------
                        order.nhcl_replication_status = True
                        order.validate_orders(deliver_order='pos_order')
                        msg = f"Delivery Order successfully created for {order.name}"
                        ho.create_cmr_transaction_server_replication_log("success", msg)

                except Exception as order_err:
                    # Any unexpected error per order
                    ho.create_cmr_transaction_server_replication_log("failure", str(order_err))
                    continue
        return True

    def call_pos_orders(self):
        self.send_pos_order_data_to_ho()
        self.get_pos_journal_entry()
        self.get_pos_crediet_note_issue_journal_entry()
        self.merge_pos_delivery_orders()
        self.pos_orders_invoice()
        return True