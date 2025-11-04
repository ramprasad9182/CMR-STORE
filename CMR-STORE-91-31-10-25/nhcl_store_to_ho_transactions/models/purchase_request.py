from odoo import models, _, fields, api
import requests
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    nhcl_replication_status = fields.Boolean('Replication Status', default=False, copy=False)
    warning_message = fields.Char(compute='_compute_warning_message')
    update_warning_message = fields.Char(compute='_compute_update_warning_message')
    nhcl_update_status = fields.Boolean('Update Status', default=False, copy=False)

    invoice_number = fields.Char(string="PO Number")
    upload_type = fields.Selection([
        ('normal', 'Normal'),
        ('pt_upload', 'PT Upload'),
    ], string="Upload Type", default='normal')

    def action_open_upload_wizard(self):
        """Open the wizard for PT upload"""
        return {
            'name': "Upload PT Excel",
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.pt.upload.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_order_id': self.id},
        }

    @api.depends('name')
    def _compute_update_warning_message(self):
        self.warning_message = ''
        if self.nhcl_update_status == False:
            self.update_warning_message = 'Update Only Once'
        else:
            self.update_warning_message = 'Successfully Updated!'

    @api.depends('name')
    def _compute_warning_message(self):
        self.warning_message = ''
        if self.nhcl_replication_status == False:
            self.warning_message = 'Oops! Integration has not been completed.'
        else:
            self.warning_message = 'Integration is Complete!'

    # def send_purchase_request_to_ho(self):
    #     ho_id = self.env['nhcl.ho.store.master'].search([('nhcl_store_type','=', 'ho'),('nhcl_active','=',True)])
    #     for ho in ho_id:
    #         try:
    #             ho_ip = ho.nhcl_terminal_ip
    #             ho_port = ho.nhcl_port_no
    #             api_key = ho.nhcl_api_key
    #             headers_source = {'api_key':f"{api_key}",'Content_Type':'application/json'}
    #             order_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/search"
    #             order_domain = [('origin', '=', self.name)]
    #             order_url = f"{order_search}?domain={order_domain}"
    #             order_data = requests.get(order_url, headers=headers_source).json()
    #             order_id = order_data.get("data")
    #             if not order_id:
    #                 self.ensure_one()
    #                 company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
    #                 company_domain = [('name', '=', self.company_id.name)]
    #                 company_url = f"{company_search}?domain={company_domain}"
    #                 company_data = requests.get(company_url, headers=headers_source).json()
    #                 company_id = company_data.get("data")
    #                 partner_search = f"http://{ho_ip}:{ho_port}/api/res.partner/search"
    #                 partner_domain = [('name', '=', self.partner_id.name),('phone','=',self.partner_id.phone)]
    #                 partner_url = f"{partner_search}?domain={partner_domain}"
    #                 partner_data = requests.get(partner_url, headers=headers_source).json()
    #                 partner_id = partner_data.get("data")
    #                 if not partner_id:
    #                     raise UserError(_('Partner not found in HO'))
    #                 ho_stock_picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
    #                 picking_type_domain = [('name', '=', self.picking_type_id.name),('company_id', '=', company_id[0]['id'])]
    #                 picking_type_url = f"{ho_stock_picking_type_url}?domain={picking_type_domain}"
    #                 picking_type_data = requests.get(picking_type_url,headers=headers_source).json()
    #                 picking_type = picking_type_data.get("data")
    #                 order_lines = []
    #                 for line in self.order_line:
    #                     product_url_data = f"http://{ho_ip}:{ho_port}/api/product.product/search"
    #                     product_domain = [('name', '=', line.product_id.name), ('nhcl_id', '=', line.product_id.nhcl_id)]
    #                     product_id_url = f"{product_url_data}?domain={product_domain}"
    #                     product_data = requests.get(product_id_url, headers=headers_source).json()
    #                     product_id = product_data.get("data")
    #                     if not product_id:
    #                         raise UserError(_('Product %s not found in HO')%line.product_id.display_name)
    #                     order_lines.append((0, 0, {
    #                         "name": line.name,
    #                         "product_id": product_id[0]['id'],
    #                         "product_qty": line.product_qty,
    #                         "price_unit": line.price_unit,
    #                     }))
    #                 purchase_vals_data = {
    #                     'origin': self.name,
    #                     'partner_id': partner_id[0]['id'],
    #                     'nhcl_po_type': self.nhcl_po_type,
    #                     'picking_type_id': picking_type[0]['id'],
    #                     'date_order': self.date_order.strftime("%Y-%m-%d"),
    #                     'company_id': company_id[0]['id'],
    #                     'payment_term_id': self.payment_term_id.id,
    #                     'partner_ref': self.name,
    #                     'currency_id': self.currency_id.id,
    #                     'order_line': order_lines,
    #                 }
    #                 purchase_request_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/create"
    #                 purchase_request_data = requests.post(purchase_request_search,
    #                                                            headers=headers_source, json=[purchase_vals_data])
    #                 purchase_request_data.raise_for_status()
    #                 # Access the JSON content from the response
    #                 purchase_request = purchase_request_data.json()
    #                 message = purchase_request.get("message", "No message provided")
    #                 print(purchase_request)
    #                 if purchase_request.get("success") == False:
    #                     _logger.info(
    #                     f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
    #                     logging.error(
    #                     f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error:")
    #                     ho.create_cmr_transaction_server_replication_log('success', message)
    #                     ho.create_cmr_transaction_replication_log(purchase_request['object_name'],
    #                                                       self.id,
    #                                                       200,
    #                                                       'add', 'failure', message)
    #                 else:
    #                     _logger.info(
    #                        f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
    #                     logging.info(
    #                          f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
    #                     ho.create_cmr_transaction_server_replication_log('success', message)
    #                     ho.create_cmr_transaction_replication_log(purchase_request['object_name'], self.id,
    #                                                       200,
    #                                                       'add', 'success',
    #                                                       f"Successfully created Delivery Order {self.name}")
    #                     self.nhcl_replication_status = True
    #         except Exception as e:
    #             ho.create_cmr_transaction_server_replication_log("failure", e)

    def send_purchase_request_to_ho(self):
        if not self.order_line:
            raise ValidationError ("Add atleast one line")

        ho_id = self.env['nhcl.ho.store.master'].search([('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True)])
        for ho in ho_id:
            ho_ip = ho.nhcl_terminal_ip
            ho_port = ho.nhcl_port_no
            api_key = ho.nhcl_api_key
            headers_source = {'api_key': f"{api_key}", 'Content_Type': 'application/json'}
            order_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/search"
            company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
            company_domain = [('name', '=', self.company_id.name)]
            company_url = f"{company_search}?domain={company_domain}"
            company_data = requests.get(company_url, headers=headers_source).json()
            company_id = company_data.get("data")
            order_domain = [('origin', '=', self.name), ('company_id', '=', company_id[0]['id'])]
            order_url = f"{order_search}?domain={order_domain}"
            order_data = requests.get(order_url, headers=headers_source).json()
            order_id = order_data.get("data")
            if not order_id:
                self.ensure_one()
                partner_search = f"http://{ho_ip}:{ho_port}/api/res.partner/search"
                partner_domain = [('name', '=', self.partner_id.name)]
                partner_url = f"{partner_search}?domain={partner_domain}"
                partner_data = requests.get(partner_url, headers=headers_source).json()
                partner_id = partner_data.get("data")
                if not partner_id:
                    raise UserError(_('Partner not found in HO'))
                ho_stock_picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
                picking_type_domain = [('name', '=', self.picking_type_id.name),
                                       ('company_id', '=', company_id[0]['id'])]
                picking_type_url = f"{ho_stock_picking_type_url}?domain={picking_type_domain}"
                picking_type_data = requests.get(picking_type_url, headers=headers_source).json()
                picking_type = picking_type_data.get("data")
                order_lines = []
                for line in self.order_line:
                    product_url_data = f"http://{ho_ip}:{ho_port}/api/product.product/search"
                    product_domain = [('default_code', '=', line.product_id.default_code), ('nhcl_id', '=', line.product_id.nhcl_id)]
                    product_id_url = f"{product_url_data}?domain={product_domain}"
                    product_data = requests.get(product_id_url, headers=headers_source).json()
                    product_id = product_data.get("data")
                    if not product_id:
                        raise UserError(_('Product %s not found in HO') % line.product_id.display_name)
                    order_lines.append((0, 0, {
                        "name": line.name,
                        "product_id": product_id[0]['id'],
                        "product_qty": line.product_qty,
                        "price_unit": line.price_unit,
                        "icode_barcode": line.icode_barcode,
                        "brand": line.brand,
                        "size": line.size,
                        "design": line.design,
                        "fit": line.fit,
                        "colour": line.color,
                        "product_excel": line.product_excel,
                        "standard_rate": line.standard_rate,
                        "mrp": line.mrp,
                        "rsp": line.rsp,
                        "item_vendor_id": line.item_vendor_id,
                        "hsn_sac_code": line.hsn_sac_code,
                        "des5": line.des5,
                        "des6": line.des6,
                    }))
                purchase_vals_data = {
                    'origin': self.name,
                    'partner_id': partner_id[0]['id'],
                    'nhcl_po_type': self.nhcl_po_type,
                    'picking_type_id': picking_type[0]['id'],
                    'date_order': self.date_order.strftime("%Y-%m-%d"),
                    'company_id': company_id[0]['id'],
                    'payment_term_id': self.payment_term_id.id,
                    'partner_ref': self.name,
                    'currency_id': self.currency_id.id,
                    'invoice_number':self.invoice_number,
                    'upload_type':self.upload_type,
                    'order_line': order_lines,
                }
                purchase_request_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/create"
                purchase_request_data = requests.post(purchase_request_search,
                                                      headers=headers_source, json=[purchase_vals_data])
                purchase_request_data.raise_for_status()
                # Access the JSON content from the response
                purchase_request = purchase_request_data.json()
                message = purchase_request.get("message", "No message provided")
                if purchase_request.get("success") == False:
                    _logger.info(
                        f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                    logging.error(
                        f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                    ho.create_cmr_transaction_server_replication_log('success', message)
                    ho.create_cmr_transaction_replication_log(purchase_request['object_name'],
                                                              self.id,
                                                              200,
                                                              'add', 'failure', message)
                else:
                    _logger.info(
                        f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                    logging.info(
                        f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                    ho.create_cmr_transaction_server_replication_log('success', message)
                    ho.create_cmr_transaction_replication_log(purchase_request['object_name'], self.id,
                                                              200,
                                                              'add', 'success',
                                                              f"Successfully created Delivery Order {self.name}")
                    self.nhcl_replication_status = True

    def update_purchase_request_to_ho(self):
        ho_id = self.env['nhcl.ho.store.master'].search([('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True)])
        for ho in ho_id:
            ho_ip = ho.nhcl_terminal_ip
            ho_port = ho.nhcl_port_no
            api_key = ho.nhcl_api_key
            headers_source = {'api_key': f"{api_key}", 'Content_Type': 'application/json'}
            order_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/search"
            company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
            company_domain = [('name', '=', self.company_id.name)]
            company_url = f"{company_search}?domain={company_domain}"
            company_data = requests.get(company_url, headers=headers_source).json()
            company_id = company_data.get("data")
            order_domain = [('origin', '=', self.name), ('company_id', '=', company_id[0]['id'])]
            order_url = f"{order_search}?domain={order_domain}"
            order_data = requests.get(order_url, headers=headers_source).json()
            order_id = order_data.get("data")
            print("order_id", order_id[0]['id'])
            order = order_id[0]['id']
            if order_id:
                self.ensure_one()
                partner_search = f"http://{ho_ip}:{ho_port}/api/res.partner/search"
                partner_domain = [('name', '=', self.partner_id.name)]
                partner_url = f"{partner_search}?domain={partner_domain}"
                partner_data = requests.get(partner_url, headers=headers_source).json()
                partner_id = partner_data.get("data")
                if not partner_id:
                    raise UserError(_('Partner not found in HO'))
                ho_stock_picking_type_url = f"http://{ho_ip}:{ho_port}/api/stock.picking.type/search"
                picking_type_domain = [('name', '=', self.picking_type_id.name),
                                       ('company_id', '=', company_id[0]['id'])]
                picking_type_url = f"{ho_stock_picking_type_url}?domain={picking_type_domain}"
                picking_type_data = requests.get(picking_type_url, headers=headers_source).json()
                picking_type = picking_type_data.get("data")
                order_lines = []
                for line in self.order_line:
                    product_url_data = f"http://{ho_ip}:{ho_port}/api/product.product/search"
                    product_domain = [('default_code', '=', line.product_id.default_code), ('nhcl_id', '=', line.product_id.nhcl_id)]
                    product_id_url = f"{product_url_data}?domain={product_domain}"
                    product_data = requests.get(product_id_url, headers=headers_source).json()
                    product_id = product_data.get("data")
                    if not product_id:
                        raise UserError(_('Product %s not found in HO') % line.product_id.display_name)
                    purchase_line_domain = [('product_id', '=', product_id[0]['id']),
                                            ('order_id', '=', order)]
                    po_line_url = f"http://{ho_ip}:{ho_port}/api/purchase.order.line/search"
                    purchase_order_line_url = f"{po_line_url}?domain={purchase_line_domain}"
                    purchase_order_line_data = requests.get(purchase_order_line_url, headers=headers_source).json()
                    purchase_order_line_id = purchase_order_line_data.get("data")
                    if purchase_order_line_id and line.name == purchase_order_line_id[0]['name']:
                        purchase_line_id = purchase_order_line_id[0]['id']
                        order_lines.append([1, purchase_line_id, {
                            "name": line.name,
                            "product_id": product_id[0]['id'],
                            "product_qty": line.product_qty,
                            "price_unit": line.price_unit,
                        }])
                    else:
                        order_lines.append((0, 0, {
                            "name": line.name,
                            "product_id": product_id[0]['id'],
                            "product_qty": line.product_qty,
                            "price_unit": line.price_unit,
                        }))
                purchase_vals_data = {
                    'id': order_id[0]['id'],
                    'order_line': order_lines
                }
                purchase_indent_domain = [('purchase_indent_id', '=', order_id[0]['id']), ]
                po_indent_url = f"http://{ho_ip}:{ho_port}/api/internal.purchase.indent.orderline/search"
                purchase_indent_line_url = f"{po_indent_url}?domain={purchase_indent_domain}"
                purchase_indent_line_data = requests.get(purchase_indent_line_url, headers=headers_source).json()
                purchase_indent_line_id = purchase_indent_line_data.get("data")
                if purchase_indent_line_id:
                    raise UserError(_('You are not allowed to update po data in HO, because PO added '
                                      'in Internal Purchase Indent in HO'))
                purchase_request_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/{order}"
                purchase_request_data = requests.put(purchase_request_search,
                                                     headers=headers_source, json=purchase_vals_data)
                purchase_request_data.raise_for_status()
                # Access the JSON content from the response
                purchase_request = purchase_request_data.json()
                message = purchase_request.get("message", "No message provided")
                if purchase_request.get("success") == False:
                    _logger.info(
                        f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                    logging.error(
                        f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                    ho.create_cmr_transaction_server_replication_log('success', message)
                    ho.create_cmr_transaction_replication_log(purchase_request['object_name'],
                                                              self.id,
                                                              200,
                                                              'add', 'failure', message)
                    return {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'message': "Failed to Sync",
                            'type': 'danger',
                            'sticky': False
                        }
                    }
                else:
                    self.nhcl_update_status = True
                    _logger.info(
                        f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                    logging.info(
                        f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                    ho.create_cmr_transaction_server_replication_log('success', message)
                    ho.create_cmr_transaction_replication_log(purchase_request['object_name'], self.id,
                                                              200,
                                                              'add', 'success',
                                                              f"Successfully created Delivery Order {self.name}")
                    # return {
                    #     'type': 'ir.actions.client',
                    #     'tag': 'display_notification',
                    #     'params': {
                    #         'message': "Successfully Synced",
                    #         'type': 'success',
                    #         'sticky': False
                    #     }
                    # }

    # def button_cancel(self):
    #     res= super(PurchaseOrder, self).button_cancel()
    #     if self.state == 'cancel' and self.nhcl_replication_status == True:

    def cancel_purchase_request_to_ho(self):
        ho_id = self.env['nhcl.ho.store.master'].search([('nhcl_store_type', '=', 'ho'), ('nhcl_active', '=', True)])
        if self.state == 'cancel':
            for ho in ho_id:
                ho_ip = ho.nhcl_terminal_ip
                ho_port = ho.nhcl_port_no
                api_key = ho.nhcl_api_key
                headers_source = {'api_key': f"{api_key}", 'Content_Type': 'application/json'}
                order_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/search"
                company_search = f"http://{ho_ip}:{ho_port}/api/res.company/search"
                company_domain = [('name', '=', self.company_id.name)]
                company_url = f"{company_search}?domain={company_domain}"
                company_data = requests.get(company_url, headers=headers_source).json()
                company_id = company_data.get("data")
                order_domain = [('origin', '=', self.name), ('company_id', '=', company_id[0]['id'])]
                order_url = f"{order_search}?domain={order_domain}"
                order_data = requests.get(order_url, headers=headers_source).json()
                order_id = order_data.get("data")
                order = order_id[0]['id']
                if order_id:
                    self.ensure_one()
                    partner_search = f"http://{ho_ip}:{ho_port}/api/res.partner/search"
                    partner_domain = [('name', '=', self.partner_id.name)]
                    partner_url = f"{partner_search}?domain={partner_domain}"
                    partner_data = requests.get(partner_url, headers=headers_source).json()
                    partner_id = partner_data.get("data")
                    if not partner_id:
                        raise UserError(_('Partner not found in HO'))
                    purchase_vals_data = {
                        'id': order_id[0]['id'],
                        'state': self.state
                    }
                    purchase_indent_domain = [('purchase_indent_id', '=', order_id[0]['id']), ]
                    po_indent_url = f"http://{ho_ip}:{ho_port}/api/internal.purchase.indent.orderline/search"
                    purchase_indent_line_url = f"{po_indent_url}?domain={purchase_indent_domain}"
                    purchase_indent_line_data = requests.get(purchase_indent_line_url, headers=headers_source).json()
                    purchase_indent_line_id = purchase_indent_line_data.get("data")
                    if purchase_indent_line_id:
                        raise UserError(_('You are not allowed to Cancel po data in HO, because PO added '
                                          'in Internal Purchase Indent in HO'))
                    purchase_request_search = f"http://{ho_ip}:{ho_port}/api/purchase.order/{order}"
                    purchase_request_data = requests.put(purchase_request_search,
                                                         headers=headers_source, json=purchase_vals_data)
                    purchase_request_data.raise_for_status()
                    # Access the JSON content from the response
                    purchase_request = purchase_request_data.json()
                    message = purchase_request.get("message", "No message provided")
                    if purchase_request.get("success") == False:
                        _logger.info(
                            f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error: ")
                        logging.error(
                            f"Failed to create Purchase Request {message} '{ho_ip}' with partner '{ho_port}'. Error:")
                        ho.create_cmr_transaction_server_replication_log('success', message)
                        ho.create_cmr_transaction_replication_log(purchase_request['object_name'],
                                                                  self.id,
                                                                  200,
                                                                  'add', 'failure', message)
                        return {
                            'type': 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': "Failed to Sync",
                                'type':'danger',
                                'sticky': False
                            }
                        }
                    else:
                        _logger.info(
                            f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                        logging.info(
                            f"Successfully created Purchase Request {self.name} {message} '{ho_ip}' with partner '{ho_port}'.")
                        ho.create_cmr_transaction_server_replication_log('success', message)
                        ho.create_cmr_transaction_replication_log(purchase_request['object_name'], self.id,
                                                                  200,
                                                                  'add', 'success',
                                                                  f"Successfully created Delivery Order {self.name}")
                        return {
                            'type' : 'ir.actions.client',
                            'tag': 'display_notification',
                            'params': {
                                'message': "Successfully Synced",
                                'type': 'success',
                                'sticky': False
                            }
                        }



class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    icode_barcode = fields.Char("Barcode")
    # article_name = fields.Char("Article Name")
    brand = fields.Char("Brand")
    size = fields.Char("Size")
    design = fields.Char("Design")
    fit = fields.Char("Fit")
    color = fields.Char("Colour")
    product_excel = fields.Char("Product (Excel)")
    standard_rate = fields.Float("Standard Rate")
    mrp = fields.Float("MRP")
    rsp = fields.Float("RSP")
    item_vendor_id = fields.Char("Item Vendor ID")
    hsn_sac_code = fields.Char("HSN/SAC Code")
    des5 = fields.Char("Aging")
    des6 = fields.Char("DES6")




