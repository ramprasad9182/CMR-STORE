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


class NhclPOSHourReport(models.Model):
    _name = 'nhcl.pos.hour.report'
    _description = "nhcl pos hour report"

    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')
    nhcl_pos_hour_report_ids = fields.One2many('nhcl.pos.hour.report.line', 'nhcl_pos_hour_report_id')

    def get_pos_order_hour_report(self):
        # Remove existing lines
        self.nhcl_pos_hour_report_ids.unlink()

        user_tz = self.env.user.tz or 'UTC'
        local_tz = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        for store in self:

            # 🔹 Fetch POS order lines from local DB
            pos_lines = self.env['pos.order.line'].search([
                ('order_id.date_order', '>=', from_date),
                ('order_id.date_order', '<=', to_date),
                # 👉 IMPORTANT: filter by store
                ('order_id.company_id', '=', store.nhcl_company_id.id)
                # OR use below if store is POS config-based
                # ('order_id.config_id', '=', store.pos_config_id.id)
            ])

            grouped_data = {}

            for line in pos_lines:

                order = line.order_id
                order_ref = order.name
                receipt_ref = order.pos_reference
                if not order_ref:
                    continue

                # Convert date to user timezone
                date_order = fields.Datetime.context_timestamp(self, order.date_order)

                qty = line.qty
                subtotal = line.price_subtotal
                tax_inc_total = line.price_subtotal_incl
                is_reward = getattr(line, 'is_reward_line', False)

                # ❌ Ignore refunds
                if qty < 0:
                    continue

                # Initialize group
                if order_ref not in grouped_data:
                    grouped_data[order_ref] = {
                        'qty': 0,
                        'amount_excl': 0.0,
                        'amount_incl': 0.0,
                        'payment': 0.0,
                        'date': date_order.strftime("%Y-%m-%d %H:%M:%S"),
                    }

                # ✅ SALES lines
                if subtotal > 0:
                    grouped_data[order_ref]['qty'] += qty
                    grouped_data[order_ref]['amount_excl'] += subtotal
                    grouped_data[order_ref]['amount_incl'] += tax_inc_total
                    grouped_data[order_ref]['payment'] += tax_inc_total

                # ✅ DISCOUNT / PROMOTION lines
                elif is_reward or subtotal < 0:
                    grouped_data[order_ref]['payment'] += tax_inc_total

            # 🔹 Bulk create
            vals_list = []
            for order_ref, values in grouped_data.items():
                vals_list.append({
                    'nhcl_order_ref': order_ref,
                    'nhcl_bill_receipt_no': order.pos_reference,
                    'nhcl_order_quantity': values['qty'],
                    'nhcl_amount_total': values['amount_excl'],
                    'nhcl_in_amount_total': values['amount_incl'],
                    'nhcl_amount_payment': values['payment'],
                    'nhcl_date_order': values['date'],
                    'nhcl_company_id': store.nhcl_company_id.id,
                    'nhcl_pos_hour_report_id': self.id,
                })

            if vals_list:
                self.env['nhcl.pos.hour.report.line'].create(vals_list)

    def action_to_reset(self):
        self.write({
            'nhcl_company_id': False,
            'from_date': False,
            'to_date': False
        })
        self.nhcl_pos_hour_report_ids.unlink()

    def get_excel_sheet(self):
        # Create a file-like buffer to receive the data
        buffer = io.BytesIO()

        # Create an Excel workbook and add a worksheet
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet()

        # Add a bold format to use to highlight cells
        bold = workbook.add_format({'bold': True})

        # Write data headers
        headers = ['Company','Shop Name', 'POS Date','Quantity','Total Amount ']
        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        # Write data rows
        for row_num, line in enumerate(self.nhcl_pos_hour_report_ids, start=1):
            worksheet.write(row_num, 0, line.nhcl_store_id.nhcl_store_name.name)
            worksheet.write(row_num, 1, line.nhcl_order_ref)
            worksheet.write(row_num, 2, line.nhcl_date_order and format_date(self.env, line.nhcl_date_order, date_format='dd-MM-yyyy'))
            worksheet.write(row_num, 3, line.nhcl_order_quantity)
            worksheet.write(row_num, 4, line.nhcl_amount_total)

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
            'name': f'POS_Order_Hourly_Based_Report_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': f'POS_Order_Hourly_Based_Report_{fields.Date.today()}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        # Return the action to download the file
        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }


class NhclPOSHourReportLine(models.Model):
    _name = 'nhcl.pos.hour.report.line'
    _description = "nhcl pos hour report line"

    nhcl_pos_hour_report_id = fields.Many2one('nhcl.pos.hour.report', string="Pos Hour Report")
    nhcl_order_ref = fields.Char(string="Order Ref No")
    nhcl_date_order = fields.Datetime(string="Order Date")
    nhcl_order_quantity = fields.Integer(string="Quantity")
    nhcl_amount_total = fields.Float(string="Amount Total Exc Tax")
    nhcl_in_amount_total = fields.Float(string="Amount Total Inc Tax")
    nhcl_amount_paid = fields.Datetime(string="Amount Paid Time")
    nhcl_amount_payment = fields.Float(string="Amount Paid")
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')
    nhcl_bill_receipt_no = fields.Char(string="Bill Receipt No")