from odoo import models,fields,api,_
import requests
from datetime import datetime
import pytz
from odoo.exceptions import ValidationError
import xmlrpc.client


from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
import base64
import io

import xlsxwriter
from odoo.tools import format_date
from collections import defaultdict


class PosMOPReportWizard(models.TransientModel):
    _name = 'pos.mop.report.wizard'
    _description = 'POS MOP Report'

    from_date = fields.Datetime('From Date')
    to_date = fields.Datetime('To Date')
    nhcl_company_id = fields.Many2one('res.company', string='Store Name')

    def get_grouped_payments(self):
        report_list = []

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        for store in self:

            # 🔹 Get POS Payments from local DB
            payments = self.env['pos.payment'].search([
                ('payment_date', '>=', from_date),
                ('payment_date', '<=', to_date),

                # 👉 IMPORTANT: filter store
                ('pos_order_id.company_id', '=', store.nhcl_company_id.id)
                # OR:
                # ('pos_order_id.config_id', '=', store.pos_config_id.id)
            ])

            # 🔹 Get Credit Notes (account.move)
            credit_moves = self.env['account.move'].search([
                ('create_date', '>=', from_date),
                ('create_date', '<=', to_date),
                ('move_type', 'in', ['out_refund', 'in_refund']),
                ('company_id', '=', store.nhcl_company_id.id)
            ])

            from collections import defaultdict
            grouped_payments = defaultdict(float)

            # 🔹 Group POS Payments
            for pay in payments:
                method_name = pay.payment_method_id.name or "Unknown"
                grouped_payments[method_name] += pay.amount

            # 🔹 Add Credit Notes
            credit_total = sum(credit_moves.mapped('amount_total_signed'))
            grouped_payments["Credit Notes"] += credit_total

            # 🔹 Company Name
            company_name = store.nhcl_company_id.name if store.nhcl_company_id else "Unknown"

            report_list.append({
                'report_data': dict(grouped_payments),
                'start_date': from_date,
                'end_date': to_date,
                'company_name': company_name,
            })

        final_data = {'doc': report_list}

        return self.env.ref(
            'nhcl_customizations.report_pos_mop_pdfsss'
        ).report_action(self, data=final_data)

    @api.constrains('from_date', 'to_date')
    def _check_dates(self):
        for record in self:
            if record.from_date and record.to_date and record.to_date < record.from_date:
                raise ValidationError(
                    "The 'To Date' cannot be earlier than the 'From Date'."
                )

    def get_grouped_payments_in_excel(self):
        report_list = []
        distinct_payment_methods = set()

        user_tz = self.env.user.tz or 'UTC'
        local = pytz.timezone(user_tz)

        from_date = fields.Datetime.to_datetime(self.from_date)
        to_date = fields.Datetime.to_datetime(self.to_date)

        try:
            for store in self:

                # 🔹 Fetch POS Payments from local DB
                payments = self.env['pos.payment'].search([
                    ('payment_date', '>=', from_date),
                    ('payment_date', '<=', to_date),

                    # 👉 IMPORTANT: filter store properly
                    ('pos_order_id.company_id', '=', store.nhcl_company_id.id)
                    # OR:
                    # ('pos_order_id.config_id', '=', store.pos_config_id.id)
                ])

                from collections import defaultdict
                grouped_payments = defaultdict(float)

                for pay in payments:
                    method_name = pay.payment_method_id.name or "Unknown"

                    distinct_payment_methods.add(method_name)
                    grouped_payments[method_name] += pay.amount

                report_list.append({
                    'store_name': store.nhcl_company_id.name,
                    'bill_type': "POS BILL",
                    'grouped_payments': dict(grouped_payments),
                    'start_date': from_date,
                    'end_date': to_date,
                })

        except Exception as e:
            print("Error in payment report:", e)

        # 🔹 Create Excel
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        worksheet = workbook.add_worksheet('POS Payment Grouped Report')

        bold = workbook.add_format({'bold': True})

        # Dynamic payment methods
        payment_methods = sorted(distinct_payment_methods)

        headers = ['Site', 'Bill Type'] + payment_methods + ['Grand Total']

        for col_num, header in enumerate(headers):
            worksheet.write(0, col_num, header, bold)

        row = 1
        for line in report_list:
            worksheet.write(row, 0, line['store_name'])
            worksheet.write(row, 1, line['bill_type'])

            total_amount = 0

            for col_num, method in enumerate(payment_methods, start=2):
                amount = line['grouped_payments'].get(method, 0.0)
                worksheet.write(row, col_num, amount)
                total_amount += amount

            worksheet.write(row, len(payment_methods) + 2, total_amount)

            row += 1

        workbook.close()

        buffer.seek(0)
        excel_data = buffer.getvalue()
        buffer.close()

        encoded_data = base64.b64encode(excel_data)

        attachment = self.env['ir.attachment'].create({
            'name': f'POS_Grouped_Payments_Report_{fields.Date.today()}.xlsx',
            'type': 'binary',
            'datas': encoded_data,
            'store_fname': f'POS_Grouped_Payments_Report_{fields.Date.today()}.xlsx',
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'new',
        }