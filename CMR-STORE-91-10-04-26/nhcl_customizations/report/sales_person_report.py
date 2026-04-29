from odoo import models, fields, api
from odoo.exceptions import ValidationError
from datetime import datetime, time
from openpyxl import Workbook
from io import BytesIO
import base64


class PosSalesEmployeeReport(models.TransientModel):
    _name = 'pos.sales.employee.report'
    _description = 'POS Sales Employee Report'
    _rec_name = 'company_id'

    company_id = fields.Many2one(
        'res.company',
        string="Company",
        required=True, readonly=True,
        default=lambda self: self.env.company
    )
    date_from = fields.Date(string="From Date", required=True)
    date_to = fields.Date(string="To Date", required=True)
    report_line_ids = fields.One2many(
        'pos.sales.employee.report.line',
        'report_id',
        string="Category Summary"
    )
    employee_id = fields.Many2one('hr.employee', string="Employee", domain=[('sale_employee', '=', 'yes')])

    def _get_root_category(self, categ):
        while categ.parent_id:
            categ = categ.parent_id
        return categ

    def action_generate_report(self):
        for rec in self:

            if rec.date_from > rec.date_to:
                raise ValidationError("From Date cannot be greater than To Date.")

            rec.report_line_ids.unlink()

            # Convert Date → Datetime range
            start = datetime.combine(rec.date_from, time.min)
            end = datetime.combine(rec.date_to, time.max)

            start = fields.Datetime.to_string(start)
            end = fields.Datetime.to_string(end)

            domain = [
                ('order_id.date_order', '>=', start),
                ('order_id.date_order', '<=', end),
                ('order_id.state', 'in', ['paid', 'done', 'invoiced']),
            ]

            # Optional employee filter (from report form)
            if rec.employee_id:
                domain.append(('employ_id', '=', rec.employee_id.id))

            lines = self.env['pos.order.line'].search(domain)

            summary = {}

            for line in lines:
                # Top Level Category (ADIDAS)
                root_category = self._get_root_category(line.product_id.categ_id)
                root_categ_id = root_category.id if root_category else False
                employee = line.employ_id
                employee_id = employee.id if employee else False
                key = (root_categ_id, employee_id)
                if key not in summary:
                    summary[key] = {
                        'category_id': root_categ_id,
                        'employee_id': employee_id,
                        'job_position_id': employee.job_id.id,
                        'quantity': 0.0,
                        'total_amount': 0.0,
                    }

                summary[key]['quantity'] += line.qty
                summary[key]['total_amount'] += line.price_subtotal_incl
            rec.report_line_ids = [(0, 0, vals) for vals in summary.values()]

    def action_export_excel(self):
        self.ensure_one()

        if not self.report_line_ids:
            raise ValidationError("Please generate the report first.")

        wb = Workbook()
        ws = wb.active
        ws.title = "POS Sales Report"

        # Headers
        headers = ["Brand", "Sales Employee", "Quantity", "Total Amount"]
        ws.append(headers)

        for line in self.report_line_ids:
            ws.append([
                line.category_id.name or '',
                line.employee_id.name or '',
                line.quantity,
                line.total_amount,
            ])

        # Save file
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        file_data = base64.b64encode(buffer.read())

        attachment = self.env['ir.attachment'].create({
            'name': 'POS_Sales_Employee_Report.xlsx',
            'type': 'binary',
            'datas': file_data,
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        })

        return {
            'type': 'ir.actions.act_url',
            'url': f'/web/content/{attachment.id}?download=true',
            'target': 'self',
        }

    def action_print_pdf(self):
        return self.env.ref('nhcl_customizations.pos_sales_employee_report_pdf').report_action(self)


    def action_to_reset(self):
        for rec in self:
            rec.report_line_ids.unlink()



class PosSalesEmployeeReportLine(models.TransientModel):
    _name = 'pos.sales.employee.report.line'
    _description = 'POS Sales Employee Report Line'

    report_id = fields.Many2one('pos.sales.employee.report',string="Report",ondelete='cascade')
    category_id = fields.Many2one('product.category',string="Product Category")
    employee_id = fields.Many2one('hr.employee',string="Sales Employee")
    job_position_id = fields.Many2one('hr.job',string="Job Position")
    quantity = fields.Float(string="Total Quantity")
    total_amount = fields.Float(string="Total Amount")