from odoo import models, fields, api, _
import requests
from datetime import datetime, time
import pytz

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import base64
import io

import xlsxwriter
from odoo.tools import format_date
from collections import defaultdict


class NhclHSNTaxReport(models.Model):
    _name = 'nhcl.hsn.tax.report'
    _description = "hsn tax report main"

    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')
    nhcl_pos_hsn_tax_ids = fields.One2many('nhcl.hsn.tax.report.line', 'nhcl_pos_hsn_tax_id')

    def get_hsn_with_tax_wise_report(self):
        self.nhcl_pos_hsn_tax_ids.unlink()

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        for store in self:

            # 🔹 Fetch POS lines from local DB
            pos_lines = self.env['pos.order.line'].search([
                ('order_id.date_order', '>=', from_date),
                ('order_id.date_order', '<=', to_date),

                # 👉 IMPORTANT: filter store properly
                ('order_id.company_id', '=', store.nhcl_company_id.id)
                # OR:
                # ('order_id.config_id', '=', store.pos_config_id.id)
            ])

            grouped_data = {}

            for line in pos_lines:

                product = line.product_id
                if not product:
                    continue

                hsn_code = product.l10n_in_hsn_code or 'N/A'

                # Take first tax (same as your API logic)
                tax = line.tax_ids[:1]
                tax_name = tax.name if tax else 'No Tax'

                qty = line.qty
                subtotal = line.price_subtotal
                subtotal_incl = line.price_subtotal_incl

                tax_amount = subtotal_incl - subtotal

                key = (store.id, hsn_code, tax_name)

                if key not in grouped_data:
                    grouped_data[key] = {
                        'qty': 0,
                        'taxable': 0.0,
                        'total': 0.0,
                        'tax': 0.0,
                        'cgst': 0.0,
                        'sgst': 0.0,
                    }

                grouped_data[key]['qty'] += qty
                grouped_data[key]['taxable'] += subtotal
                grouped_data[key]['total'] += subtotal_incl
                grouped_data[key]['tax'] += tax_amount
                grouped_data[key]['cgst'] += tax_amount / 2
                grouped_data[key]['sgst'] += tax_amount / 2

            # 🔹 Create records
            vals_list = []
            for (store_id, hsn, tax_name), vals in grouped_data.items():
                vals_list.append({
                    'nhcl_hsn': hsn,
                    'nhcl_tax': tax_name,
                    'nhcl_order_quantity': vals['qty'],
                    'nhcl_amount_total': vals['total'],
                    'nhcl_taxable_amount': vals['taxable'],
                    'nhcl_tax_amount': vals['tax'],
                    'nhcl_cgst_amount': vals['cgst'],
                    'nhcl_sgst_amount': vals['sgst'],
                    'nhcl_company_id': store.nhcl_company_id.id,
                    'nhcl_pos_hsn_tax_id': self.id
                })

            if vals_list:
                self.env['nhcl.hsn.tax.report.line'].create(vals_list)

    def action_to_reset(self):
        self.write({
            'nhcl_company_id': False,
            'from_date': False,
            'to_date': False
        })
        self.nhcl_pos_hsn_tax_ids.unlink()


    def get_excel_sheet(self):
        # Create a file-like buffer to receive the data
        buffer = io.BytesIO()

        # Create an Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Add a bold format to use to highlight cells
        bold = workbook.add_format({'bold': True})

        # Write data headers
        headers = ['HSN', 'TAX%', 'BILLQTY', 'NETAMT', 'TAXABLEAMT', 'CGSTAMT', 'SGSTAMT']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        # Write data rows
        for row_num, line in enumerate(self.nhcl_pos_hsn_tax_ids, start=1):
            worksheet.write(row_num, 0, line.nhcl_hsn)
            worksheet.write(row_num, 1, line.nhcl_tax)
            worksheet.write(row_num, 2, line.nhcl_order_quantity)
            worksheet.write(row_num, 3, line.nhcl_amount_total)
            worksheet.write(row_num, 4, line.nhcl_taxable_amount)
            worksheet.write(row_num, 5, line.nhcl_cgst_amount)
            worksheet.write(row_num, 6, line.nhcl_sgst_amount)

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
            'name': f'POS_HSN_Wise_Tax_Report_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': f'POS_HSN_Wise_Report_{fields.Date.today()}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Return the action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class NhclHSNTaxReportLine(models.Model):
    _name = 'nhcl.hsn.tax.report.line'
    _description = "hsn tax report"

    nhcl_pos_hsn_tax_id = fields.Many2one('nhcl.hsn.tax.report', string="HSN Tax Report")
    nhcl_hsn = fields.Char(string="HSN")
    nhcl_tax = fields.Char(string="Tax%")
    nhcl_order_quantity = fields.Integer(string="BillQty")
    nhcl_amount_total = fields.Float(string="Gross AMT")
    nhcl_taxable_amount = fields.Float(string="NET AMT")
    nhcl_tax_amount = fields.Float(string="TAX AMT")
    nhcl_cgst_amount = fields.Float(string="CGST AMT")
    nhcl_sgst_amount = fields.Float(string="SGST AMT")
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')
