from odoo import http

from odoo.http import request

class AccountPostController(http.Controller):
    @http.route('/api/account.move/call_action', type='json', auth='public', methods=['POST'], csrf=False)
    def call_action_post_button(self, move_id):
        move = request.env['account.move'].sudo().browse(move_id)

        if not move.exists():
            return {'status': 'error', 'message': 'Account move record not found'}

        try:
            # Call the button action function (replace 'action_post' with your button's method name)
            move.action_post()
            return {'status': 'success', 'message': 'Button action executed successfully'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}