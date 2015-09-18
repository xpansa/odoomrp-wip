# -*- encoding: utf-8 -*-

from openerp import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'purchase.order'

    @api.cr_uid_ids_context
    def open_wizard_variable_attribute(self, cr, uid, order, context=None):
        if not context:
            context = {}

        context.update({
        	'active_model': self._name,
        	'active_ids': order,
        	'active_id': len(order) and order[0] or False
        })

        order_obj = self.pool['purchase.order'].browse(cr, uid, len(order) and order[0] or [], context=context)
        new_wizard_id = self.pool['purchase.order.line.wizard'].create(cr, uid, {
        	'order_id': len(order) and order[0] or False,
            'name': ' ',
            'state': 'draft',
            'partner_id': order_obj.partner_id.id if order_obj else False,
            'date_order': order_obj.date_order if order_obj else False,
            'price_unit': 1.00,
            'date_planned': order_obj.minimum_planned_date if order_obj and order_obj.minimum_planned_date else order_obj.date_order,
        })

        return self.pool['purchase.order.line.wizard'].wizard_view(cr, uid, new_wizard_id, context)
