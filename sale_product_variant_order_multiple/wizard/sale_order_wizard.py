# -*- encoding: utf-8 -*-

import collections

from openerp import models, fields, exceptions, api, _
from openerp.addons import decimal_precision as dp


class ProductAttributeValueSaleLine(models.TransientModel):
    _name = 'sale.order.line.attribute.wizard'

    @api.one
    @api.depends('value', 'sale_line.product_template')
    def _get_price_extra(self):
        price_extra = 0.0
        for price in self.value.price_ids:
            if price.product_tmpl_id.id == self.sale_line.product_template.id:
                price_extra = price.price_extra
        self.price_extra = price_extra

    @api.one
    @api.depends('attribute', 'sale_line.product_template',
                 'sale_line.product_template.attribute_line_ids')
    def _get_possible_attribute_values(self):
        attr_values = self.env['product.attribute.value']
        for attr_line in self.sale_line.product_template.attribute_line_ids:
            if attr_line.attribute_id.id == self.attribute.id:
                attr_values |= attr_line.value_ids
        self.possible_values = attr_values.sorted()

    sale_line = fields.Many2one(
        comodel_name='sale.order.line.wizard', string='Order line')
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
    _name = 'variable.attribute.quantity'

    attribute = fields.Many2one(
        comodel_name='product.attribute', string='Attribute')
    value = fields.Many2one(
        comodel_name='product.attribute.value', string='Value')
    qty = fields.Integer(string='Quantity')

    line_id = fields.Many2one(comodel_name='sale.order.line.wizard', string='Sale Order Line')


class OrderLineWizard(models.TransientModel):
    _name = 'sale.order.line.wizard'
    _table = 'sale_order_line_wizard'

    product_template = fields.Many2one(comodel_name='product.template',
        string='Product Template', domain="[('variable_attribute', '!=', False)]")

    partner_id = fields.Many2one('res.partner', string='Partner helper field')
    date_order = fields.Date('Date Order from Sale Order')
    pricelist_id = fields.Many2one('product.pricelist', string='Pricelist helper field')
    fiscal_position = fields.Many2one('account.fiscal.position', string='Fiscal position helper field')

    product_attributes = fields.One2many(
        comodel_name='sale.order.line.attribute.wizard', inverse_name='sale_line',
        string='Product attributes', copy=True)

    variable_attribute_qty = fields.One2many(comodel_name='variable.attribute.quantity', 
        inverse_name='line_id', copy=True, string='Variable Quantity')

    tax_id = fields.Many2many(comodel_name='account.tax', relation='sale_line_wizard_tax_rel',
        column1='sl_id', column2='tax_id', string='Taxes')

    discount = fields.Float('Discount (%)', digits_compute= dp.get_precision('Discount'), readonly=True)
        
    delay = fields.Float('Delivery Lead Time', required=True, help="Number of days between the order confirmation and the shipping of the products to the customer", readonly=True)
        
    address_allotment_id = fields.Many2one('res.partner', 'Allotment Partner',help="A partner to whom the particular product needs to be allotted.")
        
    th_weight = fields.Float('Weight', readonly=True, digits_compute=dp.get_precision('Stock Weight'))

    order_id = fields.Many2one('sale.order', 'Order Reference', required=True, ondelete='cascade', select=True, readonly=True)
    product_uom_qty = fields.Float('Quantity', digits_compute= dp.get_precision('Product UoS'), readonly=True)
    product_uom = fields.Many2one('product.uom', 'Unit of Measure ',  readonly=True, related='product_template.uom_id')
    product_uos_qty = fields.Float('Quantity (UoS)' ,digits_compute= dp.get_precision('Product UoS'), readonly=True)
    product_uos = fields.Many2one('product.uom', 'Product UoS', related='product_template.uos_id')
    price_unit = fields.Float('Unit Price', digits_compute= dp.get_precision('Product Price'), readonly=True)
    name = fields.Text('Description', required=True, readonly=True)
    route_id = fields.Many2one('stock.location.route', 'Route',
            help="If route_id is False, the rule is global")
    invoice_lines = fields.Many2many('account.invoice.line', 'sale_order_line_invoice_rel', 'order_line_id', 'invoice_id', 'Invoice Lines', readonly=True)

    order_state = fields.Selection(related='order_id.state', readonly=True)
    company_id = fields.Many2one('res.company', related='order_id.company_id')
    product_id = fields.Many2one(
        domain="[('product_tmpl_id', '=', product_template)]")

    order_partner_id = fields.Many2one('res.partner', related='order_id.partner_id')
    salesman_id = fields.Many2one('res.users', related='order_id.user_id')

    @api.multi
    def wizard_view(self):
        view = self.env.ref('sale_product_variant_order_multiple.sale_order_line_variable_attribute_form')

        return {
            'name': _('Variable Attribute Order Line'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context}

    @api.one
    @api.depends('product_attributes')
    def _get_product_attributes_count(self):
        self.product_attributes_count = len(self.product_attributes)

    @api.model
    def _order_attributes(self, template, product_attribute_values):
        res = template._get_product_attributes_dict()
        res2 = []
        for val in res:
            value = product_attribute_values.filtered(
                lambda x: x.attribute_id.id == val['attribute'])
            if value:
                val['value'] = value
                res2.append(val)
        return res2

    @api.model
    def _get_product_description(self, template, product, product_attributes):
        name = product and product.name or template.name
        group = self.env.ref(
            'sale_product_variants.group_product_variant_extended_description')
        extended = group in self.env.user.groups_id
        if not product_attributes and product:
            product_attributes = product.attribute_value_ids
        values = self._order_attributes(template, product_attributes)
        if extended:
            description = "\n".join(
                "%s: %s" % (x['value'].attribute_id.name, x['value'].name)
                for x in values)
        else:
            description = ", ".join([x['value'].name for x in values])
        if not description:
            return name
        return ("%s\n%s" if extended else "%s (%s)") % (name, description)

    @api.multi
    def product_id_change(
            self, pricelist, product, qty=0, uom=False, qty_uos=0,
            uos=False, name='', partner_id=False, lang=False, update_tax=True,
            date_order=False, packaging=False, fiscal_position=False,
            flag=False):
        product_obj = self.env['product.product']
        res = super(OrderLineWizard, self).product_id_change(
            pricelist, product, qty=qty, uom=uom, qty_uos=qty_uos, uos=uos,
            name=name, partner_id=partner_id, lang=lang, update_tax=update_tax,
            date_order=date_order, packaging=packaging,
            fiscal_position=fiscal_position, flag=flag)
        if product:
            product = product_obj.browse(product)
            res['value']['product_attributes'] = (
                product._get_product_attributes_values_dict())
            res['value']['name'] = self._get_product_description(
                product.product_tmpl_id, product, product.attribute_value_ids)
        return res

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
                self.product_template.id, self.product_uom_qty or 1.0,
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
        view = self.env.ref('sale_product_variant_order_multiple.sale_order_line_variable_attribute_form')

        return {
            'name': _('Variable Attribute Order Line'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order.line.wizard',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }

    def generate_name(self, line, att_qty):
        # helper function that return a name(description) for the order line
        # based on line itself
        # current variable_attribute_qty in generating iteration

        attributes = dict()
        for at in line.product_attributes:
            attributes.update({at.attribute.id: {
                'attr_name': at.attribute.name,
                'attr_value_name': at.value.name
            }})

        attributes.update({att_qty.attribute.id: {
                'attr_name': att_qty.attribute.name,
                'attr_value_name': att_qty.value.name
        }})               
                
        name = line.product_template.name

        ordered_attrs = collections.OrderedDict(sorted(attributes.items()))

        for k, v in ordered_attrs.iteritems():
            name += _(' ; %s: %s') % (v['attr_name'], v['attr_value_name'])

        return name

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

            name = self.generate_name(line, att_qty)

            price_extra = 0

            for attr_line in line.product_attributes:
                price_extra += attr_line.price_extra

            for price in att_qty.value.price_ids:
                if price.product_tmpl_id.id == self.product_template.id:
                    price_extra += price.price_extra

            price_unit = self.order_id.pricelist_id.with_context(
                {
                    'uom': self.product_uom.id,
                    'date': self.order_id.date_order,
                    'price_extra': price_extra,
                }).template_price_get(
                self.product_template.id, self.product_uom_qty or 1.0,
                self.order_id.partner_id.id)[self.order_id.pricelist_id.id]

            res = {
                'product_uos_qty': att_qty.qty,
                'product_uom': line.product_uom.id,
                'sequence': sequence,
                'price_unit': price_unit,
                'product_uom_qty': att_qty.qty,
                'product_uos': line.product_uos.id if line.product_uos else line.product_uom.id,
                'company_id': line.company_id.id,
                'name': name,
                'delay': line.delay,
                'state': 'draft',
                'order_partner_id': line.order_partner_id.id if line.order_partner_id else False,
                'order_id': line.order_id.id,
                'discount': line.discount,
                'salesman_id': line.salesman_id.id if line.salesman_id else False,
                'th_weight': line.th_weight,
                'tax_id': [(6, 0, [t.id for t in line.tax_id])],
                'product_template': line.product_template.id,
                'product_attributes': product_attributes,
            }
            values.append(res)
        return values, sequence

    @api.multi
    def generate_order_lines(self):
        n = 0
        order_line = self.env['sale.order.line']

        for rec in self:
            values, n = self.prepare_values(rec, n)
            if not values:
                continue
            
            for value in values:
                new_line = order_line.create(value)
        if n == 0:
            raise exceptions.except_orm(
                _('No Order Lines Generated!'),
                _('Please set at least one line of variable attributes with more than zero quantity!'))
        return True
