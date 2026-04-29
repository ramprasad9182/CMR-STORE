from odoo import models,fields,api,_
import requests
from datetime import datetime
import pytz
import re


import xmlrpc.client


from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import base64
import io

import xlsxwriter
from odoo.tools import format_date
from odoo.http import  request

from collections import defaultdict


class PosTaxReportWizard(models.TransientModel):
    _name = 'pos.tax.report.wizard'
    _description = 'POS tax Report Wizard'

    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')

    DEFAULT_SERVER_DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"

    def get_taxed_data(self):
        report_list = []

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        try:
            for store in self:

                # 🔹 Fetch POS Order Lines from local DB
                pos_lines = self.env['pos.order.line'].search([
                    ('create_date', '>=', from_date),
                    ('create_date', '<=', to_date),
                    ('order_id.state', 'in', ['paid', 'done']),

                    # 👉 IMPORTANT: filter store properly
                    ('order_id.company_id', '=', store.nhcl_company_id.id)
                    # OR:
                    # ('order_id.config_id', '=', store.pos_config_id.id)
                ])

                from collections import defaultdict
                import re

                tax_data = defaultdict(lambda: {
                    'taxable_amt': 0.0,
                    'tax_amt': 0.0,
                    'cgst_amt': 0.0,
                    'sgst_amt': 0.0,
                    'igst_amt': 0.0
                })

                for line in pos_lines:

                    taxable_amt = line.price_subtotal

                    # Loop through taxes
                    for tax in line.tax_ids:
                        tax_name = tax.name or ''

                        match = re.search(r'(\d+)%', tax_name)
                        tax_rate = int(match.group(1)) if match else 0

                        tax_amount = taxable_amt * tax_rate / 100

                        tax_data[tax_rate]['taxable_amt'] += taxable_amt
                        tax_data[tax_rate]['tax_amt'] += tax_amount

                        # GST split
                        if tax_rate in [3, 5, 12, 18, 28]:
                            tax_data[tax_rate]['cgst_amt'] += tax_amount / 2
                            tax_data[tax_rate]['sgst_amt'] += tax_amount / 2
                        else:
                            tax_data[tax_rate]['igst_amt'] += tax_amount

                # 🔹 Prepare report data
                report_data = []
                for tax_rate, data in tax_data.items():
                    report_data.append({
                        'tax_percent': tax_rate,
                        'taxable_amt': data['taxable_amt'],
                        'cgst_amt': data['cgst_amt'],
                        'sgst_amt': data['sgst_amt'],
                        'igst_amt': data['igst_amt'],
                        'tax_amt': data['tax_amt'],
                    })

                report_list.append({
                    'store_name': store.nhcl_company_id.name,
                    'report_data': report_data,
                    'start_date': from_date,
                    'end_date': to_date,
                })

        except Exception as e:
            print("Error in tax report:", e)

        final_data = {'doc': report_list}

        return self.env.ref(
            'nhcl_customizations.report_pos_tax_pdfsss'
        ).report_action(self, data=final_data)

    def get_taxed_data_in_excel(self):
        report_list = []

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        try:
            for store in self:

                # 🔹 Fetch from LOCAL DB (NO API)
                pos_lines = self.env['pos.order.line'].search([
                    ('create_date', '>=', from_date),
                    ('create_date', '<=', to_date),
                    ('order_id.state', 'in', ['paid', 'done']),

                    # 👉 Adjust based on your system
                    ('order_id.company_id', '=', store.nhcl_company_id.id)
                    # OR:
                    # ('order_id.config_id', '=', store.pos_config_id.id)
                ])

                from collections import defaultdict

                tax_data = defaultdict(lambda: {
                    'taxable_amt': 0.0,
                    'tax_amt': 0.0,
                    'cgst_amt': 0.0,
                    'sgst_amt': 0.0,
                    'igst_amt': 0.0
                })

                for line in pos_lines:
                    taxable_amt = line.price_subtotal

                    for tax in line.tax_ids:
                        tax_rate = tax.amount or 0.0  # ✅ BETTER than regex

                        tax_amount = taxable_amt * tax_rate / 100

                        tax_data[tax_rate]['taxable_amt'] += taxable_amt
                        tax_data[tax_rate]['tax_amt'] += tax_amount

                        # GST split
                        if tax_rate in [3, 5, 12, 18, 28]:
                            tax_data[tax_rate]['cgst_amt'] += tax_amount / 2
                            tax_data[tax_rate]['sgst_amt'] += tax_amount / 2
                        else:
                            tax_data[tax_rate]['igst_amt'] += tax_amount

                # Prepare report data
                report_data = []
                for tax_rate, data in tax_data.items():
                    report_data.append({
                        'tax_percent': tax_rate,
                        'taxable_amt': data['taxable_amt'],
                        'cgst_amt': data['cgst_amt'],
                        'sgst_amt': data['sgst_amt'],
                        'igst_amt': data['igst_amt'],
                        'tax_amt': data['tax_amt'],
                    })

                report_list.append({
                    'store_name': store.nhcl_company_id.name,
                    'report_data': report_data,
                })

        except Exception as e:
            print("Error in tax report:", e)

        # ================== EXCEL ==================

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet('POS Tax Report')

        bold = workbook.add_format({'bold': True})

        headers = ['Store', 'Tax %', 'Taxable Amount', 'CGST', 'SGST', 'IGST', 'Total Tax']
        worksheet.write_row(0, 0, headers, bold)

        row = 1

        grand_totals = {
            'taxable_amt': 0.0,
            'cgst_amt': 0.0,
            'sgst_amt': 0.0,
            'igst_amt': 0.0,
            'tax_amt': 0.0
        }

        for store_data in report_list:
            for line in store_data['report_data']:
                worksheet.write(row, 0, store_data['store_name'])
                worksheet.write(row, 1, line['tax_percent'])
                worksheet.write(row, 2, line['taxable_amt'])
                worksheet.write(row, 3, line['cgst_amt'])
                worksheet.write(row, 4, line['sgst_amt'])
                worksheet.write(row, 5, line['igst_amt'])
                worksheet.write(row, 6, line['tax_amt'])

                # Totals
                grand_totals['taxable_amt'] += line['taxable_amt']
                grand_totals['cgst_amt'] += line['cgst_amt']
                grand_totals['sgst_amt'] += line['sgst_amt']
                grand_totals['igst_amt'] += line['igst_amt']
                grand_totals['tax_amt'] += line['tax_amt']

                row += 1

        # Grand Total Row
        worksheet.write(row, 0, 'Grand Total', bold)
        worksheet.write(row, 2, grand_totals['taxable_amt'])
        worksheet.write(row, 3, grand_totals['cgst_amt'])
        worksheet.write(row, 4, grand_totals['sgst_amt'])
        worksheet.write(row, 5, grand_totals['igst_amt'])
        worksheet.write(row, 6, grand_totals['tax_amt'])

        workbook.close()

        buffer.seek(0)
        excel_data = buffer.getvalue()
        buffer.close()

        encoded_data = base64.b64encode(excel_data)

        attachment = self.env['ir.attachment'].create({
            'name': f'POS_Tax_Report_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': f'POS_Tax_Report_{fields.Date.today()}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }
