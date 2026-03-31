# -*- coding: utf-8 -*-
import subprocess

from odoo import http, models,fields,_,api
import logging
from odoo.http import request



from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)  # Set up Odoo's logger

class PosConfigInherit(models.Model):
    _inherit = 'pos.config'

    system_ip_address = fields.Char("System Device Name",required=1)
    user_name = fields.Char(string="User Name")
    password = fields.Char(String="Password")

    @api.constrains('payment_method_ids')
    def _check_payment_method_ids_journal(self):
        # override to disable original constraint
        pass

    @api.model
    def web_search_read(self, domain, specification, offset=0, limit=None, order=None, count_limit=None):
        current_ip = http.request.httprequest.remote_addr if http.request and http.request.httprequest else ''
        print("current", current_ip)

        if not self.env.user.has_group('point_of_sale.group_pos_manager'):
            # Apply domain filter if the user is not a POS manager
            domain = [('system_ip_address', '=', current_ip)]
        else:
            # No domain filter for POS managers
            domain = []

        return super().web_search_read(domain, specification, offset=offset, limit=limit, order=order,
                                       count_limit=count_limit)






    # def get_device_name_via_ssh(self, host, port, username, password):
    #     try:
    #         ssh_client = paramiko.SSHClient()
    #         ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    #         ssh_client.connect(host, port=port, username=username, password=password)
    #
    #         # Run the command to get the device's hostname
    #         stdin, stdout, stderr = ssh_client.exec_command('hostname')
    #         device_name = stdout.read().decode().strip()
    #
    #         ssh_client.close()
    #         return device_name
    #     except Exception as e:
    #         _logger.error(f"Error connecting via SSH: {e}")
    #         return None
    #
    #
    #
    # def open_ui(self):
    #     # agent = request.httprequest.environ.get('HTTP_USER_AGENT')
    #     # agent_details = httpagentparser.detect(agent)
    #     # session_info = request.env['ir.http'].session_info()
    #     # print(session_info)
    #     remote_ip = http.request.httprequest.remote_addr if http.request else 'Unknown'
    #     # device_name = request.httprequest.environ
    #     # print(device_name)
    #
    #     client_device_name = self.get_device_name_via_ssh(remote_ip, 22, self.user_name,self.password)
    #     print(client_device_name)
    #     # Log information about access
    #     if self.system_ip_address != client_device_name:
    #         _logger.warning(
    #             f"Access denied for name: {self.name} from device:  (IP: {remote_ip})"
    #         )
    #
    #
    #         message = "This System not have permission to access this terminal"
    #         return {
    #             'type': 'ir.actions.client',
    #             'tag': 'display_notification',
    #             'params': {
    #                 'message': message,
    #                 'type': 'danger',
    #                 'sticky': False,
    #             }
    #         }
    #     return super(PosConfigInherit, self).open_ui()
