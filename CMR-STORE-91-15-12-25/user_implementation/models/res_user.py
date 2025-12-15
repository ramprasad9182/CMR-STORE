from odoo import models,fields,api
from datetime import date

class Users(models.Model):
    _inherit = 'res.users'

    expiry_date = fields.Date(string="License Expiry Date", store= True)
    user_license_id = fields.Many2one("license.key.line",string="User License Id")

    @api.model
    def cron_deactivate_expired_users(self):
        today = date.today()
        expired_users = self.search([
            ('expiry_date', '<', today),
            ('active', '=', True)
        ])
        for user in expired_users:
            user.active = False


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    expiry_date = fields.Date(string="License Expiry Date")
    employee_license_id = fields.Many2one("license.key.line", string="User License Id")

    @api.model
    def cron_deactivate_expired_employee(self):
        today = date.today()
        expired_employees = self.search([
            ('expiry_date', '<', today),
            ('active', '=', True)
        ])
        for employee in expired_employees:
            employee.active = False