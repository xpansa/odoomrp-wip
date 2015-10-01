# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.cr_uid_ids_context
    def open_wizard_variable_attribute(self, cr, uid, order, context=None):
        if not context:
            context = {}

        context.update({
        	'active_model': self._name,
        	'active_ids': order,
        	'active_id': len(order) and order[0] or False
        })

        order_obj = self.pool['sale.order'].browse(cr, uid, len(order) and order[0] or [], context=context)
        new_wizard_id = self.pool['sale.order.line.wizard'].create(cr, uid, {
        	'order_id': len(order) and order[0] or False,
            'name': ' ',
            'state': 'draft',
            'partner_id': order_obj.partner_id.id if order_obj else False,
            'date_order': order_obj.date_order if order_obj else False,
            'pricelist_id': order_obj.pricelist_id.id if order_obj else False,
            'fiscal_position': order_obj.fiscal_position.id if order_obj else False,
        })

        return self.pool['sale.order.line.wizard'].wizard_view(cr, uid, new_wizard_id, context)
