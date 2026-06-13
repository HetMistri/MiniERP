# -*- coding: utf-8 -*-
# from odoo import http


# class MiniErp(http.Controller):
#     @http.route('/mini_erp/mini_erp', auth='public')
#     def index(self, **kw):
#         return "Hello, world"

#     @http.route('/mini_erp/mini_erp/objects', auth='public')
#     def list(self, **kw):
#         return http.request.render('mini_erp.listing', {
#             'root': '/mini_erp/mini_erp',
#             'objects': http.request.env['mini_erp.mini_erp'].search([]),
#         })

#     @http.route('/mini_erp/mini_erp/objects/<model("mini_erp.mini_erp"):obj>', auth='public')
#     def object(self, obj, **kw):
#         return http.request.render('mini_erp.object', {
#             'object': obj
#         })

