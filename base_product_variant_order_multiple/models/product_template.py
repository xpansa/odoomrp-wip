# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    @api.multi
    def _current_attributes(self):
        for rec in self:
            rec.attrs = [(6, 0, [at.attribute_id.id for at in rec.attribute_line_ids])]
    
    attrs = fields.Many2many(comodel_name='product.attribute', 
        relation='template_attributes', column1='t_id', column2='at_id',
        string='Available attributes', readonly=True,
        compute='_current_attributes')

    variable_attribute = fields.Many2one(comodel_name='product.attribute', 
        string='Variable Attribute', domain="[('id', 'in', attrs[0][2])]")

    def _get_product_attributes_dict(self):
        product_attributes = []
        for attribute in self.attribute_line_ids:
            if attribute.attribute_id.id == self.variable_attribute.id \
                    and self.env.context.get('on_variable_wizard', False):
                continue
            product_attributes.append({'attribute': attribute.attribute_id.id})
        return product_attributes
