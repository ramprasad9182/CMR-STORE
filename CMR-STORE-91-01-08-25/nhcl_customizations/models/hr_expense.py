from odoo import api, fields, Command, models, _


class HrExpense(models.Model):
    _inherit = "hr.expense"

    vehicle_id = fields.Many2one('fleet.vehicle', string='Vehicle', copy=False, tracking=True)


class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    sale_employee = fields.Selection([('yes','YES'), ('no','NO')], string="Sale Employee")