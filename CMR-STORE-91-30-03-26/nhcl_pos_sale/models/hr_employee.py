import re

from odoo import fields, models, api,_
from odoo.exceptions import ValidationError


class HrEmployee(models.Model):
    """Add field into hr employee"""
    _inherit = 'hr.employee'

    limited_discount = fields.Integer(string="Discount Limit",
                                      help="Provide discount limit to each "
                                           "employee")


class ResPartner(models.Model):
    _inherit = 'res.partner'


    @api.constrains('phone', 'mobile')
    def _check_phone_mobile_length(self):
        for rec in self:
            for field in ['phone', 'mobile']:
                number = rec[field]

                if number:
                    digits = re.sub(r'\D', '', number)  # keep digits only

                    if len(digits) != 10:
                        raise ValidationError(_(
                            "Phone No must contain exactly 10 digits."
                        ))