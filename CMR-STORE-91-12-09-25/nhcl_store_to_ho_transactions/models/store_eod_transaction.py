from odoo import models
import requests
import logging

_logger = logging.getLogger(__name__)
from datetime import datetime
from odoo.exceptions import ValidationError, UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def get_pos_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Point of Sale")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Point of Sale'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Point of Sale'),
                                                         ('company_id.name', '=', company_id[0]['parent_id'][0]['name'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True

                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_delivery_orders(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])

        for ho in ho_id:
            try:
                ho_ip = ho.nhcl_terminal_ip
                ho_port = ho.nhcl_port_no
                store_api_key = ho.nhcl_api_key
                headers_source = {'api-key': f"{store_api_key}", 'Content-Type': 'application/json'}
                picking_type_id = self.env['stock.picking.type'].search([('name', '=', "PoS Orders")])
                store_pos_delivery_orders = self.env['stock.picking'].search(
                    [('picking_type_id', '=', picking_type_id.id), ('nhcl_replication_status', '=', False),
                     ('state', '=', 'done')])
                # Fetching delivery orders
                if store_pos_delivery_orders:
                    for order in store_pos_delivery_orders:
                        if order.location_id.name != "Customers":
                            company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                            company_domain = [('name', '=', order.company_id.name)]
                            company_url = f"{company_search}?domain={company_domain}"
                            company_data = requests.get(company_url, headers=headers_source).json()
                            company_id = company_data.get("data")
                            ho_stock_picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
                            picking_type_domain = [('name', '=', "PoS Orders"),
                                                   ('company_id', '=', company_id[0]['id'])]
                            picking_type_url = f"{ho_stock_picking_type_url}?domain={picking_type_domain}"
                            picking_type_data = requests.get(picking_type_url,
                                                             headers=headers_source).json()
                            picking_type = picking_type_data.get("data")
                            ho_location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                            location_domain = [('name', '=', order.location_id.name), ("active", "!=", False),
                                               ('usage', '=', 'internal'), ('company_id', '=', company_id[0]['id'])]
                            location_url = f"{ho_location_url}?domain={location_domain}"
                            location_data = requests.get(location_url,
                                                         headers=headers_source).json()
                            location_id = location_data.get("data")
                            print('source', location_id)
                            store_location_dest_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search"
                            dest_location_domain = [('complete_name', '=', order.location_dest_id.complete_name),
                                                    ("active", "!=", False),
                                                    ('usage', '=', 'customer'),
                                                    ]
                            dest_location_url = f"{store_location_dest_url}?domain={dest_location_domain}"
                            dest_location_data = requests.get(dest_location_url,
                                                              headers=headers_source).json()
                            dest_location = dest_location_data.get("data")
                            stock_picking_data = {
                                'picking_type_id': picking_type[0]['id'],
                                'origin': order.name,
                                'location_id': location_id[0]['id'] if location_id else False,
                                'location_dest_id': dest_location[0]['id'] if dest_location else False,
                                'company_id': location_id[0]['company_id'][0]['id'] if company_id else False,
                                'move_type': 'direct',
                                'state': 'done',
                                'nhcl_store_delivery': True
                            }
                            stock_picking_search = f"http://{ho_ip}:{ho_port}/api/stock.picking/create"
                            stock_picking_data = requests.post(stock_picking_search,
                                                               headers=headers_source, json=[stock_picking_data])
                            stock_picking_data.raise_for_status()
                            # Access the JSON content from the response
                            stock_picking = stock_picking_data.json()
                            print(stock_picking)
                            # picking_id = stock_picking.get("data")
                            # Creating stock move lines
                            for line in order.move_line_ids_without_package:
                                product = line.product_id
                                product_domain = [('nhcl_id', '=', product.nhcl_id)]
                                ho_product_url = f"http://{ho_ip}:{ho_port}/api/product.product/search"
                                product_url = f"{ho_product_url}?domain={product_domain}"
                                product_data = requests.get(product_url,
                                                            headers=headers_source).json()
                                product_id = product_data.get("data")
                                if line and line.lot_id:
                                    lot_name = line.lot_id.name
                                else:
                                    lot_name = None
                                print(stock_picking.get("create_id"))
                                if line:
                                    move_line_vals = {
                                        "picking_id": stock_picking.get("create_id"),
                                        "product_id": product_id[0]['id'],
                                        # "product_uom_id": product_id[0]["uom_id"][0]["id"],
                                        "quantity": line.quantity,
                                        # "location_id": store_account_move_line_data1[0]["location_id"][0]["id"],
                                        "location_id": location_id[0]['id'],
                                        "location_dest_id": dest_location[0]["id"],
                                        "lot_name": lot_name,
                                    }
                                    print(move_line_vals)
                                    stock_move_line_search = f"http://{ho_ip}:{ho_port}/api/stock.move.line/create"
                                    stock_move_line_data = requests.post(stock_move_line_search,
                                                                         headers=headers_source,
                                                                         json=[move_line_vals])
                                    stock_move_line_data.raise_for_status()
                                    # Access the JSON content from the response
                                    stock_move_line = stock_move_line_data.json()
                                    move_line = stock_move_line.get("data")
                            print('stock_picking', stock_picking)
                            message = stock_picking.get("message", "No message provided")
                            if stock_picking.get("success") == False:
                                _logger.info(
                                    f"Failed to create Delivery Order {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                logging.error(
                                    f"Failed to create Delivery Order {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                ho.create_cmr_transaction_server_replication_log('success', message)
                                ho.create_cmr_transaction_replication_log(stock_picking['object_name'],
                                                                          order.id,
                                                                          200,
                                                                          'add', 'failure', message)
                            else:
                                _logger.info(
                                    f"Successfully created Delivery Order {order.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                logging.info(
                                    f"Successfully created Delivery Order {order.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                ho.create_cmr_transaction_server_replication_log('success', message)
                                ho.create_cmr_transaction_replication_log(stock_picking['object_name'], order.id,
                                                                          200,
                                                                          'add', 'success',
                                                                          f"Successfully created Delivery Order {order.name}")
                                # stock_picking.button_validate()
                                order.nhcl_replication_status = True
                                order.validate_orders(deliver_order = 'pos_order')



            except Exception as e:
                ho.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_bank_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Bank")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Bank'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Bank'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)

                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_cash_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Cash")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Cash'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Cash'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id'] :
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('name', '=', entry.name), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_hdfc_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "HDFC")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'HDFC'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'HDFC'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_bajaj_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "BAJAJ")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'BAJAJ'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'BAJAJ'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_mobikwik_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Mobikwik")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Mobikwik'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Mobikwik'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_sbi_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "SBI")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'SBI'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'SBI'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_paytm_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Paytm")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Paytm'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Paytm'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_axis_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Axis")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Axis'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Axis'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_cheque_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Cheque")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Cheque'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Cheque'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_credit_note_settlement_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Credit Note Settlement")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Credit Note Settlement'),
                                              ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Credit Note Settlement'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_gift_voucher_journal_entry(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            account_journal_id = self.env['account.journal'].search([('name', '=', "Gift Voucher")], limit=1)
            store_journal_entry = self.env['account.move'].search(
                [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
            headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
            if store_journal_entry:
                for entry in store_journal_entry:
                    company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                    company_domain = [('name', '=', entry.company_id.name)]
                    company_url = f"{company_search}?domain={company_domain}"
                    company_data = requests.get(company_url, headers=headers_source).json()
                    company_id = company_data.get("data")
                    account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                    account_journal_domain = [('name', '=', 'Gift Voucher'), ('company_id', '=', company_id[0]['id'])]
                    account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
                    account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
                    account_journal = account_journal_data.get("data")
                    if not account_journal and company_id and company_id[0]['parent_id']:
                        parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
                        parent_account_journal_domain = [('name', '=', 'Gift Voucher'),
                                                         ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                        parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
                        parent_account_journal_data = requests.get(parent_account_journal_url,
                                                                   headers=headers_source).json()
                        account_journal = parent_account_journal_data.get("data")
                    tax_id_var = False
                    invoice_lines = []
                    for line in entry.line_ids:
                        # if line.tax_line_id and tax_id_var == False:
                        #     tax_id_var = True
                        # if tax_id_var == True:

                        account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                        account_domain = [('name', '=', line.account_id.name), ('company_id', '=', company_id[0]['id'])]
                        account_id_url = f"{account_url_data}?domain={account_domain}"
                        account_data = requests.get(account_id_url,
                                                    headers=headers_source).json()
                        account_id = account_data.get("data")
                        if not account_id and company_id and company_id[0]['parent_id']:
                            parent_account_url_data = f"http://{ho_ip}:{ho_port}/api/account.account/search"
                            parent_account_domain = [('name', '=', line.account_id.name),
                                                     ('company_id', '=', company_id[0]['parent_id'][0]['id'])]
                            parent_account_id_url = f"{parent_account_url_data}?domain={parent_account_domain}"
                            parent_account_data = requests.get(parent_account_id_url,
                                                               headers=headers_source).json()
                            account_id = parent_account_data.get("data")
                        invoice_lines.append((0, 0, {
                            "name": line.name,
                            "account_id": account_id[0]['id'],
                            "debit": line.debit,
                            "credit": line.credit,
                        }))
                    account_move_search = f"http://{ho_ip}:{ho_port}/api/account.move/search"
                    account_move_domain = [('ref', '=', entry.ref), ('company_id', '=', company_id[0]['id'])]
                    account_move_url = f"{account_move_search}?domain={account_move_domain}"
                    account_move_data = requests.get(account_move_url,
                                                     headers=headers_source).json()
                    move_id = account_move_data.get("data")
                    try:
                        if not move_id:
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
                            ho_move_url_data = f"http://{ho_ip}:{ho_port}/api/account.move/create"
                            try:
                                move_data = requests.post(ho_move_url_data, headers=headers_source,
                                                          json=[move_vals])
                                move_data.raise_for_status()
                                print(move_data)
                                # Access the JSON content from the response
                                response_json = move_data.json()
                                print('response_json', response_json)
                                if response_json:
                                    message = response_json.get("message", "No message provided")
                                    if response_json['success'] == True:
                                        entry.nhcl_replication_status = True
                                        _logger.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        logging.info(
                                            f"Successfully created Journal Entry {entry.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'success',
                                                                                     f"Successfully created Journal Entry {entry.name}")

                                    else:
                                        _logger.info(
                                            f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                        logging.error(
                                            f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                     entry.id,
                                                                                     200,
                                                                                     'add', 'failure', message)

                            except Exception as e:
                                ho_id.create_cmr_transaction_server_replication_log("failure", e)
                        # if move_id.line_ids:
                        #     move_id.action_post()
                    except:
                        _logger.info(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Journal Entry'{ho_ip}' with partner '{ho_port}'. Error:")
        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", e)

    def get_pos_exchange_recipts_orders(self):
        ho_id = self.env['nhcl.ho.store.master'].search(
            [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True)])

        for ho in ho_id:
            try:
                ho_ip = ho.nhcl_terminal_ip
                ho_port = ho.nhcl_port_no
                store_api_key = ho.nhcl_api_key
                headers_source = {'api-key': f"{store_api_key}", 'Content-Type': 'application/json'}

                # Fetch the correct picking type for "Product Exchange - POS"
                picking_type_id = self.env['stock.picking.type'].search([('name', '=', "Product Exchange - POS")])
                store_pos_delivery_orders = self.env['stock.picking'].search(
                    [('picking_type_id', '=', picking_type_id.id), ('nhcl_replication_status', '=', False),
                     ('state', '=', 'done')])

                if store_pos_delivery_orders:
                    try:
                        for order in store_pos_delivery_orders:
                            if order.location_id.name == "Customers":
                                # Fetch the company from HO
                                company_url = f"http://{ho_ip}:{ho_port}/api/res.company/search?domain=[('name','=', '{order.company_id.name}')]"
                                company_data = requests.get(company_url, headers=headers_source).json()
                                company_id = company_data.get("data", [])

                                if not company_id:
                                    logging.warning(
                                        f"Company {order.company_id.name} not found in HO. Skipping order {order.name}.")
                                    continue  # Skip this order and move to the next one

                                company_id = company_id[0]['id']
                                print("company_idjjhjj",company_id)
                                # Fetch the location from HO
                                location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search?domain=[('complete_name','=', '{order.location_id.complete_name}'),('active','!=',False)]"
                                location_data = requests.get(location_url, headers=headers_source).json()
                                location_id = location_data.get("data", [])

                                if not location_id:
                                    logging.warning(
                                        f"Location {order.location_id.name} not found in HO. Skipping order {order.name}.")
                                    continue  # Skip this order and move to the next one

                                location_id = location_id[0]['id']

                                # Fetch the destination location from HO
                                dest_location_url = f"http://{ho_ip}:{ho_port}/api/stock.location/search?domain=[('complete_name','=', '{order.location_dest_id.complete_name}'),('active','!=',False)]"
                                dest_location_data = requests.get(dest_location_url, headers=headers_source).json()
                                dest_location_id = dest_location_data.get("data", [])

                                if not dest_location_id:
                                    logging.warning(
                                        f"Destination Location {order.location_dest_id.complete_name} not found in HO. Skipping order {order.name}.")
                                    continue  # Skip this order and move to the next one

                                dest_location_id = dest_location_id[0]['id']

                                # Fetch or create the partner in HO
                                partner_url = f"http://{ho_ip}:{ho_port}/api/res.partner/search?domain=[('name','=', '{order.partner_id.name}'),('phone','=', '{order.partner_id.phone}'),('company_id','=', {company_id})]"
                                partner_data = requests.get(partner_url, headers=headers_source).json()
                                partner = partner_data.get("data", [])

                                if not partner:
                                    partner_data = {
                                        'name': order.partner_id.name,
                                        'phone': order.partner_id.phone,
                                        'company_id': company_id
                                    }
                                    partner_create_url = f"http://{ho_ip}:{ho_port}/api/res.partner/create"
                                    partner_create_response = requests.post(partner_create_url, headers=headers_source,
                                                                            json=[partner_data])
                                    partner_create_response.raise_for_status()
                                    partner = partner_create_response.json().get("create_id")

                                partner_id = partner[0]['id'] if partner else partner

                                # Fetch or create the Picking Type ID in HO
                                picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search?domain=[('name','=', '{order.picking_type_id.name}'),('company_id','=', {company_id})]"
                                picking_type_data = requests.get(picking_type_url, headers=headers_source).json()
                                picking_type = picking_type_data.get("data", [])
                                # Determine the stock picking data based on 'same store' or 'other store'
                                if order.company_type == 'same':
                                    stock_picking_data = {
                                        'partner_id': partner_id,
                                        'picking_type_id': picking_type[0]["id"],
                                        'origin': order.name,
                                        'location_id': location_id,
                                        'location_dest_id': dest_location_id,
                                        'company_id': company_id,
                                        'stock_type': 'pos_exchange',
                                        'company_type': order.company_type,
                                        'nhcl_store_delivery': True
                                    }
                                    print("stock_picking_data",stock_picking_data)
                                else:  # For "other store"
                                    # other_store_url = f"http://{ho_ip}:{ho_port}/api/nhcl.ho.store.master/search?domain=[('nhcl_store_name','=', '{order.store_name}')]"
                                    # other_store_data = requests.get(other_store_url, headers=headers_source).json()
                                    # other_store_id = other_store_data.get("data", [])
                                    #
                                    # if not other_store_id:
                                    #     logging.warning(
                                    #         f"Other store {order.store_name.name} not found in HO. Skipping order {order.name}.")
                                    #     continue  # Skip this order and move to the next one
                                    #
                                    # other_store_id = other_store_id[0]["id"]

                                    stock_picking_data = {
                                        'partner_id': partner_id,
                                        'picking_type_id': picking_type[0]["id"],
                                        'origin': order.name,
                                        'location_id': location_id,
                                        'location_dest_id': dest_location_id,
                                        'company_id': company_id,
                                        'store_name': 2,
                                        'stock_type': 'pos_exchange',
                                        'company_type': order.company_type,
                                        'store_pos_order': order.store_pos_order,
                                        'nhcl_store_delivery': True
                                    }

                                # Create stock picking in HO
                                stock_picking_create_url = f"http://{ho_ip}:{ho_port}/api/stock.picking/create"
                                stock_picking_create_response = requests.post(stock_picking_create_url,
                                                                              headers=headers_source,
                                                                              json=[stock_picking_data])
                                stock_picking_create_response.raise_for_status()

                                stock_picking = stock_picking_create_response.json()
                                stock_picking_id = stock_picking.get("create_id")
                                if not stock_picking_id:
                                    logging.warning(f"Failed to create stock picking for order {order.name}. Skipping.")
                                    continue  # Skip this order and move to the next one

                                # Create stock move lines
                                for line in order.move_line_ids_without_package:
                                    product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                                    product_url = f"http://{ho_ip}:{ho_port}/api/product.product/search?domain={product_domain}"
                                    product_data = requests.get(product_url, headers=headers_source).json()
                                    product_id = product_data.get("data", [])

                                    if not product_id:
                                        logging.warning(
                                            f"Product {line.product_id.name} not found in HO. Skipping move line for order {order.name}.")
                                        continue  # Skip this move line and move to the next

                                    product_id = product_id[0]['id']
                                    cost_price = line.cost_price
                                    print("cost_price",cost_price)
                                    move_line_vals = {
                                        "picking_id": stock_picking_id,
                                        "product_id": product_id,
                                        "cost_price": cost_price,
                                        # "mr_price": line.mr_price,
                                        # "rs_price": line.rs_price,
                                        # "internal_ref_lot": line.internal_ref_lot,
                                        # "type_product": line.type_product,
                                        "quantity": line.quantity,
                                        "location_id": location_id,
                                        "location_dest_id": dest_location_id,
                                        "lot_name": line.lot_id.name if line.lot_id else None
                                    }
                                    print("move_line_vals",move_line_vals)

                                    stock_move_line_url = f"http://{ho_ip}:{ho_port}/api/stock.move.line/create"
                                    stock_move_line_response = requests.post(stock_move_line_url, headers=headers_source,
                                                                             json=[move_line_vals])
                                    stock_move_line_response.raise_for_status()
                                    response_json = stock_move_line_response.json()
                                    if response_json:
                                        message = response_json.get("message", "No message provided")
                                        if response_json['success'] == True:
                                            order.nhcl_replication_status = True
                                            _logger.info(
                                                f"Successfully created Journal Entry {order.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                            logging.info(
                                                f"Successfully created Journal Entry {order.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                                            ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                                'Server Connected Successfully')
                                            ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                         order.id,
                                                                                         200,
                                                                                         'add', 'success',
                                                                                         f"Successfully created Journal Entry {order.name}")

                                        else:
                                            _logger.info(
                                                f"Failed to create Journal Entry {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                                            logging.error(
                                                f"Failed to create Journal Entry  {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                                            ho_id.create_cmr_transaction_server_replication_log('success', message)
                                            ho_id.create_cmr_transaction_replication_log(response_json['object_name'],
                                                                                         order.id,
                                                                                         200,
                                                                                         'add', 'failure', message)

                            else:
                                logging.warning(f"Skipping order {order.name}, location not 'Customers'.")
                    except Exception as e:
                        logging.error(f"Error while processing order {order.name}: {e}")
                        ho.create_cmr_transaction_server_replication_log("failure", str(e))
                        ho.create_cmr_transaction_replication_log('error', order.id, 500, 'add', 'failure', str(e))

            except Exception as e:
                logging.error(f"Error while processing order {order.name}: {e}")
                ho.create_cmr_transaction_server_replication_log("failure", str(e))
                ho.create_cmr_transaction_replication_log('error', order.id, 500, 'add', 'failure', str(e))

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
                            'company_id': company_id
                        }
                        partner_create_url = f"http://{ho_ip}:{ho_port}/api/res.partner/create"
                        partner_create_response = requests.post(partner_create_url, headers=headers_source,
                                                                json=[partner_data])
                        partner_create_response.raise_for_status()
                        new_partner = partner_create_response.json().get("create_id")

                    partner_id = partner[0]['id'] if partner else new_partner

                    # Prepare invoice lines
                    invoice_lines = []
                    for line in entry.invoice_line_ids:
                        product_domain = [('nhcl_id', '=', line.product_id.nhcl_id)]
                        product_url = f"http://{ho_ip}:{ho_port}/api/product.product/search?domain={product_domain}"
                        product_data = requests.get(product_url, headers=headers_source).json()
                        product_id = product_data.get("data", [])

                        if not product_id:
                            logging.warning(
                                f"Product {line.product_id.name} not found in HO. Skipping move line for order {entry.name}.")
                            continue

                        product_id = product_id[0]['id']

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

    # def get_pos_crediet_note_payment_entry(self):
    #     ho_id = self.env['nhcl.ho.store.master'].search(
    #         [('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True), ])
    #
    #     try:
    #         ho_ip = ho_id.nhcl_terminal_ip
    #         ho_port = ho_id.nhcl_port_no
    #         ho_api_key = ho_id.nhcl_api_key
    #         headers_source = {'api-key': f"{ho_api_key}", 'Content-Type': 'application/json'}
    #         account_journal_id = self.env['account.journal'].search([('name', '=', "Cash")], limit=1)
    #         cash_payments = self.env['account.payment'].search(
    #             [('journal_id', '=', account_journal_id.id), ('nhcl_replication_status', '=', False)])
    #         print("Found cash payment:", cash_payments.name)
    #         if cash_payments:
    #             for cash_payment in cash_payments:
    #                 company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
    #                 company_domain = [('name', '=', cash_payment.company_id.name)]
    #                 company_url = f"{company_search}?domain={company_domain}"
    #                 company_data = requests.get(company_url, headers=headers_source).json()
    #                 company_id = company_data.get("data")
    #                 # Fetch the corresponding journal entry for payment
    #                 account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
    #                 account_journal_domain = [('name', '=', cash_payment.journal_id.name),
    #                                           ('company_id', '=', company_id[0]['id'])]
    #                 account_journal_url = f"{account_journal_search}?domain={account_journal_domain}"
    #                 account_journal_data = requests.get(account_journal_url, headers=headers_source).json()
    #                 account_journal = account_journal_data.get("data")
    #
    #                 if not account_journal and company_id and company_id[0]['parent_id']:
    #                     # Fetch parent journal entry if not found
    #                     parent_account_journal_search = f"http://{ho_ip}:{ho_port}/api/account.journal/search"
    #                     parent_account_journal_domain = [('name', '=', cash_payment.journal_id.name),
    #                                                      ('company_id', '=',
    #                                                       company_id[0]['parent_id'][0]['id'])]
    #                     parent_account_journal_url = f"{parent_account_journal_search}?domain={parent_account_journal_domain}"
    #                     parent_account_journal_data = requests.get(parent_account_journal_url,
    #                                                                headers=headers_source).json()
    #                     account_journal = parent_account_journal_data.get("data")
    #
    #                 # Fetch payment method details
    #                 account_payment_methods_search = f"http://{ho_ip}:{ho_port}/api/account.payment.method.line/search"
    #                 account_payment_methods_domain = [
    #                     ('name', '=', cash_payment.payment_method_line_id.name),
    #                     ]
    #                 account_payment_methods_url = f"{account_payment_methods_search}?domain={account_payment_methods_domain}"
    #                 account_payment_methods_data = requests.get(account_payment_methods_url,
    #                                                             headers=headers_source).json()
    #                 account_payment_methods = account_payment_methods_data.get("data")
    #
    #                 # Check if the payment exists in HO, if not create it
    #                 account_payment_search = f"http://{ho_ip}:{ho_port}/api/account.payment/search"
    #                 account_payment_domain = [('name', '=', cash_payment.name),
    #                                           ('company_id', '=', company_id[0]['id'])]
    #                 account_payment_url = f"{account_payment_search}?domain={account_payment_domain}"
    #                 account_payment_data = requests.get(account_payment_url, headers=headers_source).json()
    #                 payment_id = account_payment_data.get("data")
    #
    #                 # Fetch or create the partner in HO
    #                 partner_url = f"http://{ho_ip}:{ho_port}/api/res.partner/search?domain=[('name','=', '{cash_payment.partner_id.name}'),('phone','=', '{cash_payment.partner_id.phone}')]"
    #                 partner_data = requests.get(partner_url, headers=headers_source).json()
    #                 partner = partner_data.get("data", [])
    #                 if not partner:
    #                     partner_data = {
    #                         'name': cash_payment.partner_id.name,
    #                         'phone': cash_payment.partner_id.phone,
    #                         'company_id': company_id
    #                     }
    #                     partner_create_url = f"http://{ho_ip}:{ho_port}/api/res.partner/create"
    #                     partner_create_response = requests.post(partner_create_url, headers=headers_source,
    #                                                             json=[partner_data])
    #                     partner_create_response.raise_for_status()
    #                     partner = partner_create_response.json().get("create_id")
    #
    #                 partner_id = partner[0]['id'] if partner else partner
    #
    #                 if not payment_id:
    #                     payment_vals = {
    #                         "partner_id": partner_id,
    #                         "name": cash_payment.name,
    #                         "ref": cash_payment.ref,
    #                         "payment_type": cash_payment.payment_type,
    #                         "date": cash_payment.date.strftime("%Y-%m-%d"),
    #                         "journal_id": account_journal[0]['id'],
    #                         "payment_method_line_id": account_payment_methods[0]['id'],
    #                         "amount": cash_payment.amount,
    #                         "company_id": company_id[0]['id'],
    #                         'nhcl_store_je': True,
    #
    #                     }
    #                     print("Sending payment request data:", payment_vals)
    #                     ho_payment_url_data = f"http://{ho_ip}:{ho_port}/api/account.payment/create"
    #
    #                     try:
    #                         payment_data = requests.post(ho_payment_url_data, headers=headers_source,
    #                                                      json=[payment_vals])
    #                         payment_data.raise_for_status()
    #
    #                         response_json = payment_data.json()
    #                         if response_json and response_json['success']:
    #                             cash_payment.nhcl_replication_status = True
    #
    #                         else:
    #                             logging.error(f"Failed to create Journal Entry {cash_payment.name}. Response: {response_json}")
    #
    #                         print('Payment creation response:', response_json)
    #                     except requests.exceptions.RequestException as e:
    #                         logging.error(f"Error creating payment: {str(e)}")
    #                         ho_id.create_cmr_transaction_server_replication_log("failure", str(e))
    #
    #     except Exception as e:
    #         logging.error(f"General error during journal entry processing: {str(e)}")
    #         ho_id.create_cmr_transaction_server_replication_log("failure", str(e))


    def get_pos_order_line_data(self):
        ho_id = self.env['nhcl.ho.store.master'].search([
            ('nhcl_store_type', '=', 'ho'),
            ('nhcl_active', '=', True),
        ], limit=1)

        if not ho_id:
            return

        try:
            ho_ip = ho_id.nhcl_terminal_ip
            ho_port = ho_id.nhcl_port_no
            ho_api_key = ho_id.nhcl_api_key
            headers_source = {
                'api-key': f"{ho_api_key}",
                'Content-Type': 'application/json'
            }

            # 🔍 Directly search relevant POS order lines
            pos_order_lines = self.env['pos.order.line'].search([
                ('vendor_return_disc_price', '>', 0)
            ])

            for pos_line in pos_order_lines:
                order = pos_line.order_id
                pos_reference = order.pos_reference

                order_lines = self.env['pos.order.line'].search([('order_id','=',pos_line.order_id.id)])

                # Check if already present in HO
                store_pos_order_search = f"http://{ho_ip}:{ho_port}/api/store.pos.order.line/search"
                store_pos_order_domain = [('store_pos_ref', '=', pos_reference)]
                ho_pos_order_url = f"{store_pos_order_search}?domain={store_pos_order_domain}"

                try:
                    ho_pos_data = requests.get(ho_pos_order_url, headers=headers_source).json()
                    move_id = ho_pos_data.get("data")
                except Exception as e:
                    ho_id.create_cmr_transaction_server_replication_log("failure", str(e))
                    continue

                for line in order_lines:
                    if line.pack_lot_ids:

                        for lot in line.pack_lot_ids:
                            store_data = {
                                'store_pos_ref': pos_reference,
                                'product_name': line.full_product_name,
                                'lot_name': lot.lot_name,
                                'quantity': line.qty,
                                'amount': line.price_subtotal_incl,
                                'reward_name': pos_line.reward_id.program_id.name,
                                'company_name': pos_line.company_id.name,
                                'vendor_return_disc_price': line.vendor_return_disc_price

                            }

                            if not move_id:
                                ho_store_pos_url_data = f"http://{ho_ip}:{ho_port}/api/store.pos.order.line/create"
                                try:
                                    move_data = requests.post(
                                        ho_store_pos_url_data,
                                        headers=headers_source,
                                        json=[store_data]
                                    )
                                    move_data.raise_for_status()
                                    response_json = move_data.json()
                                    message = response_json.get("message", "No message provided")

                                    if response_json.get('success'):
                                        _logger.info(f"Successfully created Journal Entry {order.name} {message}")
                                        ho_id.create_cmr_transaction_server_replication_log('success',
                                                                                            'Server Connected Successfully')
                                        ho_id.create_cmr_transaction_replication_log(
                                            response_json.get('object_name'),
                                            order.id,
                                            200,
                                            'add',
                                            'success',
                                            f"Successfully created Journal Entry {order.name}"
                                        )
                                    else:
                                        _logger.error(f"Failed to create Journal Entry: {message}")
                                        ho_id.create_cmr_transaction_server_replication_log('success', message)
                                        ho_id.create_cmr_transaction_replication_log(
                                            response_json.get('object_name'),
                                            order.id,
                                            200,
                                            'add',
                                            'failure',
                                            message
                                        )
                                except Exception as e:
                                    ho_id.create_cmr_transaction_server_replication_log("failure", str(e))

        except Exception as e:
            ho_id.create_cmr_transaction_server_replication_log("failure", str(e))


    def store_eod_transaction(self):
        pos_session_count = self.env['pos.session'].sudo().search_count([('state', '!=', 'closed')])
        if pos_session_count == 0:
            self.env['nhcl.initiated.status.log'].create(
                {'nhcl_serial_no': self.env['ir.sequence'].next_by_code("nhcl.initiated.status.log"),
                 'nhcl_date_of_log': datetime.now(), 'nhcl_job_name': 'Store EOD Transaction', 'nhcl_status': 'success',
                 'nhcl_details_status': 'Function Triggered'})
            self.get_pos_journal_entry()
            self.get_pos_delivery_orders()
            self.get_pos_bank_journal_entry()
            self.get_pos_cash_journal_entry()
            self.get_pos_hdfc_journal_entry()
            self.get_pos_bajaj_journal_entry()
            self.get_pos_mobikwik_journal_entry()
            self.get_pos_sbi_journal_entry()
            self.get_pos_paytm_journal_entry()
            self.get_pos_axis_journal_entry()
            self.get_pos_cheque_journal_entry()
            self.get_pos_gift_voucher_journal_entry()
            self.get_pos_credit_note_settlement_journal_entry()
            self.get_pos_crediet_note_issue_journal_entry()
            self.get_pos_order_line_data()
            self.env['nhcl.initiated.status.log'].create(
                {'nhcl_serial_no': self.env['ir.sequence'].next_by_code("nhcl.initiated.status.log"),
                 'nhcl_date_of_log': datetime.now(), 'nhcl_job_name': 'Store EOD Transaction', 'nhcl_status': 'success',
                 'nhcl_details_status': 'Function Completed'})

        else:
            raise ValidationError("Please Close The All Shops.")

