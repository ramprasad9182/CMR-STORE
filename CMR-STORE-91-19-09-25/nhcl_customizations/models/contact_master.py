from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'

    group_contact = fields.Many2one('res.partner.category', string='Group', tracking=True)
    contact_sequence = fields.Char(string="Sequence", copy=False,required=True,default=lambda self: _("New"), tracking=True)
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)
    wallet_amount =fields.Float('Wallet Amount')

    credit_note_ids = fields.One2many("res.partner.credit.note",inverse_name="partner_id")


    @api.constrains('phone')
    def avoid_duplicate_contact(self):
        for record in self:
            if not record.phone:
                raise ValidationError(_("phone number is required for all customers."))
            if record.mobile:
                existing = self.env['res.partner'].search([
                    ('phone', '=', record.phone),
                    ('id', '!=', record.id)
                ], limit=1)
                if existing:
                    raise ValidationError(_("A customer with this phone number already exists."))



class PartnerCategory(models.Model):
    _description = 'Partner Tags'
    _inherit = 'res.partner.category'

    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)





class Hr(models.Model):
    _inherit = 'hr.employee'

    employee_sequence = fields.Char(string="Sequence", copy=False, default=lambda self: _("New"),
                                   tracking=True)
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)

class Company(models.Model):
    _inherit = "res.company"

    nhcl_company_bool = fields.Boolean(string="Is Main Company")
    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)
    company_short_code = fields.Char(string="Company Code")



class Users(models.Model):
    _inherit = 'res.users'

    nhcl_id = fields.Integer(string="Nhcl Id", copy=False, index=True, tracking=True)




class ResPartnerCreditNote(models.Model):
    _name = 'res.partner.credit.note'
    _description = 'Partner Credit Note'

    partner_id = fields.Many2one('res.partner', string="Partner", ondelete="cascade", required=True)
    voucher_number = fields.Char(string="Voucher Number")
    pos_bill_number = fields.Char(string="POS Bill Number")
    pos_bill_date = fields.Date(string="POS Bill Date")
    total_amount = fields.Float(string="Total Amount")
    deducted_amount = fields.Float(string="Deducted Amount")
    remaining_amount = fields.Float(string="Remaining Amount", compute="_compute_remaining_amount",store=True)

    @api.depends('total_amount','deducted_amount')
    def _compute_remaining_amount(self):
        for rec in self:
            rec.remaining_amount = rec.total_amount - rec.deducted_amount