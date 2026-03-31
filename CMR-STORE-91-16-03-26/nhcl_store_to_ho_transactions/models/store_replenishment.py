from odoo import models, fields, api, _
import logging
import io
import base64
import xlsxwriter
_logger = logging.getLogger(__name__)


class StoreReplenishment(models.Model):
    _name = 'store.replenishment'
    _description = 'Store Replenishment'

    name = fields.Char(string="Reference",required=True,copy=False,readonly=True,default='New')
    store_id = fields.Many2one('res.company', default=lambda self:self.env.company.id)
    repl_type = fields.Selection([('regular', 'Regular'),('fashion', 'Fashions')], default='regular', string="Type")
    product_tmpl_id = fields.Many2one('product.template', string='Product', required=True)
    line_ids = fields.One2many('store.replenishment.line','repl_id',
        string="Replenishment Lines")


class StoreReplenishmentLine(models.Model):
    _name = 'store.replenishment.line'
    _description = 'Store Replenishment Line'

    repl_id = fields.Many2one('store.replenishment',required=True,ondelete='cascade')
    product_tmpl_id = fields.Many2one('product.template', related='repl_id.product_tmpl_id', store=True)
    repl_type = fields.Selection(related='repl_id.repl_type', store=True, string="Type")
    division = fields.Many2one('product.category' ,string="Division", compute='_compute_division', store=True)
    price_from = fields.Float(required=True)
    price_to = fields.Float(required=True)
    min_qty = fields.Float()
    max_qty = fields.Float()
    onhand_qty = fields.Float(compute='_compute_onhand')
    differ_qty = fields.Float(compute='_compute_differ')
    indent_qty = fields.Float(compute='compute_indent_qty')

    def action_export_mbq_excel(self):

        lines = self.env['store.replenishment.line'].search([])

        division_map = {}
        for line in lines:
            div = line.division.name or 'Undefined'
            if div not in division_map:
                division_map[div] = {
                    'onhand_qty': 0.0,
                    'differ_qty': 0.0,
                    'indent_qty': 0.0,
                }
            division_map[div]['onhand_qty'] += line.onhand_qty
            division_map[div]['differ_qty'] += line.differ_qty
            division_map[div]['indent_qty'] += line.indent_qty
        # ---------- CREATE EXCEL ----------
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('MBQ Division')
        sheet.write(0, 0, 'Division')
        sheet.write(0, 1, 'Onhand Qty')
        sheet.write(0, 2, 'Differ Qty')
        sheet.write(0, 3, 'Indent Qty')
        row = 1
        for div, vals in division_map.items():
            sheet.write(row, 0, div)
            sheet.write(row, 1, vals['onhand_qty'])
            sheet.write(row, 2, vals['differ_qty'])
            sheet.write(row, 3, vals['indent_qty'])
            row += 1
        workbook.close()
        output.seek(0)
        file_data = base64.b64encode(output.read())
        wizard = self.env['mbq.excel.download'].create({
            'file_name': 'MBQ_Division.xlsx',
            'file_data': file_data
        })
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'mbq.excel.download',
            'view_mode': 'form',
            'res_id': wizard.id,
            'target': 'new'
        }

    @api.depends('product_tmpl_id')
    def _compute_division(self):
        for rec in self:
            categ = rec.product_tmpl_id.categ_id
            if not categ:
                rec.division = False
                continue
            while categ.parent_id:
                categ = categ.parent_id
            rec.division = categ

    @api.depends('product_tmpl_id')
    def _compute_onhand(self):
        Quant = self.env['stock.quant']
        for rec in self:
            warehouse = rec.repl_id.store_id
            if not warehouse or not rec.repl_id.product_tmpl_id:
                rec.onhand_qty = 0
                continue
            locations = self.env['stock.location'].search([('company_id', '=', warehouse.id),('usage', '=', 'internal')])
            quants = Quant.search([
                ('location_id', 'in', locations.ids),
                ('product_id.product_tmpl_id', '=', rec.repl_id.product_tmpl_id.id),
                ('lot_id.rs_price', '>=', rec.price_from),
                ('lot_id.rs_price', '<=', rec.price_to)])
            rec.onhand_qty = sum(quants.mapped('quantity'))

    @api.depends('product_tmpl_id','max_qty')
    def compute_indent_qty(self):
        Lot = self.env['stock.lot']
        POL = self.env['purchase.order.line']
        for rec in self:
            rec.indent_qty = 0.0
            tmpl = rec.repl_id.product_tmpl_id
            if not tmpl:
                continue
            po_lines = POL.search([('product_template_id', '=', tmpl.id),('order_id.upload_type','=','normal'),('order_id.state','!=','cancel')])
            if not po_lines:
                continue
            po_names = po_lines.mapped('order_id.name')
            lots = Lot.search([('nhcl_purchase_indent_reference', 'in', po_names),('product_id.product_tmpl_id', '=', tmpl.id),])
            rec.indent_qty = sum(po_lines.mapped('product_uom_qty')) - sum(lots.mapped('product_qty'))
            print("fukdabfubdaubdi")

    @api.depends('onhand_qty', 'max_qty','indent_qty')
    def _compute_differ(self):
        for rec in self:
            rec.differ_qty = rec.max_qty - (rec.onhand_qty + rec.indent_qty)


class MbqDivisionWizard(models.TransientModel):
    _name = 'mbq.division.wizard'
    _description = 'MBQ Division Wizard'

    file_data = fields.Binary()
    file_name = fields.Char()
    line_ids = fields.One2many('mbq.division.wizard.line','wizard_id')

    def action_generate(self):

        self.line_ids.unlink()

        Quant = self.env['stock.quant']
        POL = self.env['purchase.order.line']
        Lot = self.env['stock.lot']
        Location = self.env['stock.location']

        company = self.env.company

        repl_lines = self.env['store.replenishment.line'].search([])

        division_map = {}

        def get_root_division(categ):
            while categ.parent_id:
                categ = categ.parent_id
            return categ

        for line in repl_lines:

            if not line.product_tmpl_id:
                continue

            division = get_root_division(line.product_tmpl_id.categ_id)

            if division.id not in division_map:
                division_map[division.id] = {
                    'division': division.name,
                    'products': set(),
                    'max_qty': 0.0
                }

            division_map[division.id]['products'].add(line.product_tmpl_id.id)
            division_map[division.id]['max_qty'] += line.max_qty

        # STORE LOCATIONS
        locations = Location.search([
            ('company_id', '=', company.id),
            ('usage', '=', 'internal')
        ])

        vals = []

        for div_id, data in division_map.items():
            product_ids = list(data['products'])

            # ---------- ONHAND ----------
            quants = Quant.search([
                ('product_id.product_tmpl_id', 'in', product_ids),
                ('location_id', 'in', locations.ids)
            ])
            onhand_qty = sum(quants.mapped('quantity'))
            # ---------- PO ----------
            po_lines = POL.search([
                ('product_id.product_tmpl_id', 'in', product_ids),
                ('order_id.state', '!=', 'cancel'),
                ('order_id.upload_type', '=', 'normal')
            ])

            po_qty = sum(po_lines.mapped('product_uom_qty'))

            po_names = po_lines.mapped('order_id.name')

            # ---------- LOT ----------
            lots = Lot.search([
                ('nhcl_purchase_indent_reference', 'in', po_names),
                ('product_id.product_tmpl_id', 'in', product_ids)
            ])

            lot_qty = sum(lots.mapped('product_qty'))

            indent_qty = po_qty - lot_qty

            differ_qty = (onhand_qty + indent_qty)

            vals.append((0, 0, {
                'division': data['division'],
                'onhand_qty': onhand_qty,
                'indent_qty': indent_qty,
                'differ_qty': differ_qty,
            }))

        self.line_ids = vals


    def action_reset(self):
        self.line_ids.unlink()

    def action_export_excel(self):
        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output, {'in_memory': True})
        sheet = workbook.add_worksheet('MBQ')
        sheet.write(0, 0, 'Division')
        sheet.write(0, 1, 'Onhand')
        sheet.write(0, 2, 'Differ')
        sheet.write(0, 3, 'Indent')
        row = 1
        for line in self.line_ids:
            sheet.write(row, 0, line.division)
            sheet.write(row, 1, line.onhand_qty)
            sheet.write(row, 2, line.differ_qty)
            sheet.write(row, 3, line.indent_qty)
            row += 1
        workbook.close()
        output.seek(0)
        self.file_data = base64.b64encode(output.read())
        self.file_name = 'MBQ.xlsx'
        return {
            'type': 'ir.actions.act_url',
            'url': (
                       '/web/content/?model=mbq.division.wizard'
                       '&id=%s'
                       '&field=file_data'
                       '&filename_field=file_name'
                       '&download=true'
                   ) % self.id,
            'target': 'self',
        }


class MbqDivisionWizardLine(models.TransientModel):
    _name = 'mbq.division.wizard.line'

    wizard_id = fields.Many2one('mbq.division.wizard')
    division = fields.Char()
    onhand_qty = fields.Float()
    differ_qty = fields.Float()
    indent_qty = fields.Float()