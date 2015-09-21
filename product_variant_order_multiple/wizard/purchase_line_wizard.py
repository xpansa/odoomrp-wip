# -*- encoding: utf-8 -*-

from openerp import models, fields, exceptions, api, _
from openerp.addons import decimal_precision as dp


class ProductAttributeValueSaleLine(models.TransientModel):
    _name = 'purchase.order.line.attribute.wizard'

    @api.one
    @api.depends('value', 'purchase_line.product_template')
    def _get_price_extra(self):
        price_extra = 0.0
        for price in self.value.price_ids:
            if price.product_tmpl_id.id == self.purchase_line.product_template.id:
                price_extra = price.price_extra
        self.price_extra = price_extra

    @api.one
    @api.depends('attribute', 'purchase_line.product_template',
                 'purchase_line.product_template.attribute_line_ids')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        for attr_line in self.purchase_line.product_template.attribute_line_ids:	
            if attr_line.attribute_id.id == self.attribute.id:
                attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()

    purchase_line = fields.Many2one(
        comodel_name='purchase.order.line.wizard', string='Order line')
    attribute = fields.Many2one(
        comodel_name='product.attribute', string='Attribute')
    value = fields.Many2one(
        comodel_name='product.attribute.value', string='Value', required=True,
        domain="[('id', 'in', possible_values[0][2])]")
    possible_values = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_get_possible_attribute_values')
    price_extra = fields.Float(
        compute='_get_price_extra', string='Attribute Price Extra',
        digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute"
        " value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")


class VariableAttributeQuantity(models.TransientModel):
    _name = 'purchase.variable.attribute.quantity'

    attribute = fields.Many2one(
        comodel_name='product.attribute', string='Attribute')
    value = fields.Many2one(
        comodel_name='product.attribute.value', string='Value')
    qty = fields.Integer(string='Quantity')

    line_id = fields.Many2one(comodel_name='purchase.order.line.wizard', string='Purchase Order Line')


class OrderLineWizard(models.TransientModel):
    _inherit = 'purchase.order.line'
    _name = 'purchase.order.line.wizard'
    _table = 'purchase_order_line_wizard'

    product_template = fields.Many2one(comodel_name='product.template',
        string='Product Template', domain="[('variable_attribute', '!=', False)]")

    partner_id = fields.Many2one('res.partner', string='Partner helper field')
    date_order = fields.Date('Date Order from Sale Order')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist helper field')
    fiscal_position = fields.Many2one('account.fiscal.position', string='Fiscal position helper field')

    product_attributes = fields.One2many(
        comodel_name='purchase.order.line.attribute.wizard', inverse_name='purchase_line',
        string='Product attributes', copy=True)

    variable_attribute_qty = fields.One2many(comodel_name='purchase.variable.attribute.quantity', 
        inverse_name='line_id', copy=True, string='Variable Quantity')

    taxes_id = fields.Many2many(comodel_name='account.tax', relation='purchase_line_wizard_tax_rel',
        column1='sl_id', column2='tax_id', string='Taxes')

    @api.multi
    @api.onchange('product_template')
    def onchange_product_template(self):
        self.ensure_one()
        self.name = self.product_template.name
        
        if not self.product_template.attribute_line_ids:
            self.product_id = (
                self.product_template.product_variant_ids and
                self.product_template.product_variant_ids[0])
        else:
            self.product_id = False
            self.price_unit = self.order_id.pricelist_id.with_context(
                {
                    'uom': self.product_uom.id,
                    'date': self.order_id.date_order,
                }).template_price_get(
                self.product_template.id, self.product_qty or 1.0,
                self.order_id.partner_id.id)[self.order_id.pricelist_id.id]

            if self.product_template.variable_attribute:
                var_att = self.product_template.variable_attribute
                att_values = None

                attribute_line_ids = self.product_template.attribute_line_ids
                for atr in attribute_line_ids:
                    if atr.attribute_id.id == var_att.id:
                        att_values = atr.value_ids
                if att_values:
                    var_att_qty_lines = [{'attribute': var_att.id, 'value': a.id, 'qty': 0} for a in att_values]
                    self.variable_attribute_qty = (var_att_qty_lines)

        self.product_attributes = (
            self.product_template._get_product_attributes_dict())

        return {'domain': {'product_id': [('product_tmpl_id', '=',
                                           self.product_template.id)]}}

    @api.multi
    def wizard_view(self):
        view = self.env.ref('product_variant_order_multiple.purchase_order_line_variable_attribute_form')

        return {
            'name': _('Variable Attribute Order Line'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'purchase.order.line.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }

    def prepare_values(self, line, sequence):
        # read values from variable.attribute.quantity
        # construct new sale order line for each of variable.attribute.quantity lines
        # where qty is not zero
        values = []
        for att_qty in line.variable_attribute_qty:
            
            res = {}
            product_attributes = [att_qty.value.id]
            if att_qty.qty == 0:
                continue
            sequence += 1

            product_attributes = [(0, 0, {
                'attribute': a.attribute.id, 
                'value': a.value.id, 
                'price_unit': 0
                }) for a in line.product_attributes
            ]
            product_attributes.append((0, 0, {
                'attribute': att_qty.attribute.id, 
                'value': att_qty.value.id, 
                'price_unit': 0
            }))
            name = "\n".join(line.product_attributes.mapped(
                lambda x: "%s: %s" % (x.attribute.name, x.value.name)))
            name = '%s\n%s: %s' % (name, att_qty.attribute.name, att_qty.value.name)

            res = {
                'product_qty': att_qty.qty,
                #'product_uom': line.product_uom.id,
                'price_unit': line.price_unit,
                
                'company_id': line.company_id.id,
                'name': name,
                'state': 'draft',
                
                'order_id': line.order_id.id,
                'taxes_id': [( 6, 0, [t.id for t in line.taxes_id])],
                'product_template': line.product_template.id,
                'product_attributes': product_attributes,
                'date_planned': line.date_planned,
	        }
            values.append(res)
        return values, sequence

    @api.multi
    def generate_order_lines(self):
        n = 0
        order_line = self.env['purchase.order.line']
        for rec in self:
            
            values, n = self.prepare_values(rec, n)
            if not values:
                continue
            
            for value in values:
                order_line.create(value)
        if n == 0:
            raise exceptions.except_orm(
                _('No Order Lines Generated!'),
                _('Please set at least one line of variable attributes with more than zero quantity!'))
        return True
