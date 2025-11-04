from odoo import models,fields,api

class LastScannedSerialNumber(models.Model):
    _name = "last.scanned.serial.number"

    Receipt_number = fields.Char(string="Receipt Number")
    document_number = fields.Char(sting="HO Delivery Doc")
    stock_product_id = fields.Many2one('product.product', string='Product', copy=False)
    stock_serial = fields.Char(string="Serial's", copy=False)
    stock_product_barcode = fields.Char(string="Barcode", copy=False)
    stock_qty = fields.Float(string='Qty', copy=False)
    store_name = fields.Char(String="Store Name")
    date = fields.Date(string="Date")
    state = fields.Boolean(string="Matched")