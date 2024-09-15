import logging
import paramiko
from odoo import fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class Service(models.Model):
    _name = 'service'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Service'

    name = fields.Char('Service Name', required=True)
    server_id = fields.Many2one('server', string='Server', required=True)
    url = fields.Char('URL')
    port = fields.Integer('Port')
    status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('failed', 'Failed'),
    ], string='Status', default='inactive')
    last_checked = fields.Datetime('Last Checked')
    is_active = fields.Boolean('Is Active', tracking=True, default=True)
    note = fields.Html('Note')

    def _execute_command(self, command):
        """Helper method to execute an SSH command and handle errors."""
        for service in self:
            server = service.server_id
            ssh = None
            try:
                ssh = server._get_ssh_client()
                stdin, stdout, stderr = ssh.exec_command(command, timeout=100)
                exit_status = stdout.channel.recv_exit_status()  # Wait for command to finish

                # Handling exit statuses for systemctl is-active
                if exit_status == 0:
                    _logger.info(f"Service {service.name} is active.")
                    return 'active'
                elif exit_status == 3:
                    _logger.info(f"Service {service.name} is inactive.")
                    return 'inactive'
                else:
                    error_message = stderr.read().decode().strip()
                    _logger.error(f"Unexpected exit status {exit_status} for service {service.name}: {error_message}")
                    return 'failed'

            except Exception as e:
                _logger.error(f"Failed to execute command '{command}' on service {service.name}: {e}")
                raise UserError(f"Failed to execute command: {e}")
            finally:
                if ssh:
                    ssh.close()



    def check_service_status(self):
        """Method to check the status of the services in parallel."""
        for  service in self:
            try:
                command = f'systemctl is-active {service.name}'
                status = service._execute_command(command)

                if status == 'active':
                    service.status = 'active'
                elif status == 'inactive':
                    service.status = 'inactive'
                else:
                    service.status = 'failed'

                _logger.info(f"Service {service.name} status checked: {service.status}")
            except Exception as e:
                service.status = 'failed'
                _logger.error(f"An error occurred while checking the status of {service.name}: {e}")
            finally:
                service.last_checked = fields.Datetime.now()

    def _check_service_status_cron(self):

        records = self.search([('is_active', '=', True)], limit=500)
        records.check_service_status()
        if len(records) == 500:  # assumes there are more whenever search hits limit
            self.env.ref('server_management.ir_cron_check_server_status')._trigger()

    def start_service(self):
        """Method to start the service."""
        for service in self:
            self._service_action(service, 'start')

    def stop_service(self):
        """Method to stop the service."""
        for service in self:
            self._service_action(service, 'stop')

    def restart_service(self):
        """Method to restart the service."""
        for service in self:
            self._service_action(service, 'restart')

    def _service_action(self, service, action):
        """Generic method for starting, stopping, or restarting a service."""
        try:
            command = f'systemctl {action} {service.name}'
            self._execute_command(command)

            service.check_service_status()
            _logger.info(f"{action.capitalize()} service: {service.name}")
            service.message_post(body=f"Service '{service.name}' {action}ed successfully.", message_type='notification')

        except Exception as e:
            _logger.error(f"Failed to {action} service {service.name}: {e}")
            service.message_post(body=f"Failed to {action} service '{service.name}': {e}", message_type='notification')
            raise UserError(f"Failed to {action} service {service.name}. See logs for details.")
        finally:
            service.last_checked = fields.Datetime.now()

