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
    configuration_details = fields.Text('Configuration Details')





    note = fields.Html('Note')

    def _execute_command(self, command):
        """Helper method to execute an SSH command and handle errors."""
        for service in self:
            server = service.server_id
            ssh = None
            try:
                ssh = server._get_ssh_client()
                stdin, stdout, stderr = ssh.exec_command(command)
                exit_status = stdout.channel.recv_exit_status()  # Wait for command to finish
                if exit_status != 0:
                    error_message = stderr.read().decode().strip()
                    _logger.error(f"Error executing command '{command}' on service {service.name}: {error_message}")
                    raise UserError(f"Error executing command: {error_message}")
                output = stdout.read().decode().strip()
                return output
            except Exception as e:
                _logger.error(f"Failed to execute command '{command}' on service {service.name}: {e}")
                raise UserError(f"Failed to execute command: {e}")
            finally:
                if ssh:
                    ssh.close()

    def check_service_status(self):
        """Method to check the status of the service."""
        for service in self:
            try:
                command = f'systemctl is-active {service.name}'
                status = self._execute_command(command)

                if status == 'active':
                    service.status = 'active'
                elif status == 'inactive':
                    service.status = 'inactive'
                else:
                    service.status = 'failed'
                    # service.restart_service()

                _logger.info(f"Service {service.name} status checked: {service.status}")

            except Exception as e:
                service.status = 'failed'
                # service.restart_service()
                _logger.error(f"An error occurred while checking the status of {service.name}: {e}")
            finally:
                service.last_checked = fields.Datetime.now()

    def _check_service_status_cron(self):

        records = self.search([], limit=500)
        records.check_service_status()
        if len(records) == 500:  # assumes there are more whenever search hits limit
            self.env.ref('server_management.ir_cron_check_server_status')._trigger()



    def start_service(self):
        """Method to start the service."""
        for service in self:

            try:
                command = f'systemctl start {service.name}'
                self._execute_command(command)

                service.check_service_status()
                _logger.info(f"Starting service: {service.name}")
                service.message_post(body=f"Service '{service.name}' started successfully.",
                                     message_type='notification')

            except Exception as e:
                _logger.error(f"Failed to start service {service.name}: {e}")
                service.message_post(body=f"Failed to start service '{service.name}': {e}", message_type='notification')

                raise UserError(f"Failed to start service {service.name}. See logs for details.")
            finally:
                service.last_checked = fields.Datetime.now()

    def stop_service(self):
        """Method to stop the service."""
        for service in self:
            try:
                command = f'systemctl stop {service.name}'
                self._execute_command(command)

                service.check_service_status()
                _logger.info(f"Stopping service: {service.name}")
                service.message_post(body=f"Service '{service.name}' stopped successfully.",
                                     message_type='notification')

            except Exception as e:
                _logger.error(f"Failed to stop service {service.name}: {e}")
                service.message_post(body=f"Failed to stop service '{service.name}': {e}", message_type='notification')

                raise UserError(f"Failed to stop service {service.name}. See logs for details.")
            finally:
                service.last_checked = fields.Datetime.now()

    def restart_service(self):
        """Method to restart the service."""
        for service in self:
            try:
                # Restarting the service
                command = f'systemctl restart {service.name}'
                self._execute_command(command)

                service.check_service_status()
                _logger.info(f"Restarting service: {service.name}")
                service.message_post(body=f"Service '{service.name}' restarted successfully.",
                                     message_type='notification')

            except Exception as e:
                _logger.error(f"Failed to restart service {service.name}: {e}")
                service.message_post(body=f"Failed to restart service '{service.name}': {e}",
                                     message_type='notification')

                raise UserError(f"Failed to restart service {service.name}. See logs for details.")
            finally:
                service.last_checked = fields.Datetime.now()
