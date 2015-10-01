# -*- coding: utf-8 -*-
#
#
#    Xpansa Product Variant
#    Copyright (C) 2014 Xpansa Group (<http://xpansa.com>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

{
    'name': 'Base Product Template Variable Attribute',
    'version': '0.1',
    'author': 'Xpansa Group',
    'category': 'Hidden',
    'website': 'http://xpansa.com',
    'description': '''
        Extend Product Template using special variable attribute
    ''',
    'depends': [
        'base',
        'product',
        'account',
        'sale',
        'sale_product_variants',
        'purchase',
        'purchase_product_variants'
    ],
    'data': [
        'views/product_template_view.xml',
    ],
    'qweb': [
    ],
    'installable': True,
    'auto_install': False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: