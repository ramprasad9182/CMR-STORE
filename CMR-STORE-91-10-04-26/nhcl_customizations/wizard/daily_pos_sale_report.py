from odoo import models,fields,api,_
import requests
from datetime import datetime
import pytz

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import base64
import io

import xlsxwriter
from odoo.tools import format_date
from collections import defaultdict


class NhclDailySaleReport(models.Model):
    _name = 'nhcl.daily.sale.report'
    _description = "Daily Sale Report"


    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    nhcl_daily_sale_report_ids = fields.One2many('nhcl.daily.sale.report.line', 'nhcl_daily_sale_report_id')
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')

    def daily_sale_dsd_report(self):
        self.nhcl_daily_sale_report_ids.unlink()

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        for store in self:

            # Search POS Order Lines directly from Odoo
            pos_lines = self.env['pos.order.line'].search([
                ('order_id.date_order', '>=', from_date),
                ('order_id.date_order', '<=', to_date),
                ('order_id.company_id', '=', store.nhcl_company_id.id)
            ])

            for line in pos_lines:

                product = line.product_id
                barcode = product.barcode

                if not barcode:
                    continue

                categ = product.categ_id

                family = categ.parent_id.parent_id.parent_id.complete_name if categ.parent_id and categ.parent_id.parent_id and categ.parent_id.parent_id.parent_id else ''
                category = categ.parent_id.parent_id.complete_name if categ.parent_id and categ.parent_id.parent_id else ''
                class_name = categ.parent_id.complete_name if categ.parent_id else ''
                brick = categ.complete_name

                existing_line = self.nhcl_daily_sale_report_ids.filtered(
                    lambda x:
                    x.nhcl_company_id.id == store.nhcl_company_id.id and
                    x.family_name == family and
                    x.category_name == category and
                    x.class_name == class_name and
                    x.brick_name == brick
                )

                if existing_line:
                    existing_line.write({
                        'bill_qty': existing_line.bill_qty + line.qty,
                        'net_amount': existing_line.net_amount + line.price_subtotal_incl,
                    })
                else:
                    self.env['nhcl.daily.sale.report.line'].create({
                        'family_name': family,
                        'category_name': category,
                        'class_name': class_name,
                        'brick_name': brick,
                        'bill_qty': line.qty,
                        'net_amount': line.price_subtotal_incl,
                        'nhcl_company_id': store.nhcl_company_id.id,
                        'nhcl_daily_sale_report_id': self.id
                    })

    def action_to_reset(self):
        self.write({
            'nhcl_company_id': False,
            'from_date': False,
            'to_date': False
        })
        self.nhcl_daily_sale_report_ids.unlink()

    def get_excel_sheet(self):
        # Create a file-like buffer to receive the data
        buffer = io.BytesIO()

        # Create an Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Add a bold format to use to highlight cells
        bold = workbook.add_format({'bold': True})

        # Write data headers
        headers = ['Store Name','Family', 'Category','Class','Brick','BillQty','NetAmt']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        # Write data rows
        for row_num, line in enumerate(self.nhcl_daily_sale_report_ids, start=1):
            worksheet.write(row_num, 0, line.nhcl_store_id.nhcl_store_name.name)
            worksheet.write(row_num, 1, line.family_name)
            worksheet.write(row_num, 2, line.category_name)
            worksheet.write(row_num, 3, line.class_name)
            worksheet.write(row_num, 3, line.brick_name)
            worksheet.write(row_num, 4, line.bill_qty)
            worksheet.write(row_num, 4, line.net_amount)

        # Close the workbook
        workbook.close()

        # Get the content of the buffer
        buffer.seek(0)
        excel_data = buffer.getvalue()
        buffer.close()

        # Encode the data in base64
        encoded_data = base64.b64encode(excel_data)

        # Create an attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'Sale_order_Daily_Based_Report{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': f'Sale_order_Daily_Based_Report_{fields.Date.today()}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Return the action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class NhclDailySaleReportLine(models.Model):
    _name = 'nhcl.daily.sale.report.line'
    _description = "nhcl daily sale report line"

    nhcl_daily_sale_report_id = fields.Many2one('nhcl.daily.sale.report', string="Daily Sale Report")
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')
    family_name = fields.Char(string="Family")
    category_name = fields.Char(string="Category")
    class_name = fields.Char(string="Class")
    brick_name = fields.Char(string="Brick")
    bill_qty = fields.Float(string="BillQty")
    net_amount = fields.Float(string="NetAmt")