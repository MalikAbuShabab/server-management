import logging
from odoo import fields, models, api
from odoo.exceptions import ValidationError
import paramiko
import re

_logger = logging.getLogger(__name__)

class Server(models.Model):
    _name = 'server'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Server'

    name = fields.Char('Server Name', tracking=True, required=True)
    ip_address = fields.Char('IP Address', tracking=True, required=True)
    username = fields.Char('Server Username', required=True)
    operating_system = fields.Char('Operating System')
    ssh_port = fields.Integer('SSH Port', tracking=True, default=22)
    is_active = fields.Boolean('Is Active', tracking=True, default=True)
    last_checked = fields.Datetime('Last Checked')

    password_type = fields.Selection([
        ('password', 'Password'),
        ('key', 'Key'),
    ], string='Password Type', default='password')

    password = fields.Char('Password')  # For password authentication
    private_key = fields.Text('Private Key')  # For key-based authentication

    status = fields.Selection([
        ('running', 'Running'),
        ('stopped', 'Stopped'),
        ('error', 'Error'),
    ], string='Status', default='running')

    customer_id = fields.Many2one('res.partner', string='Customer', ondelete='set null')
    service_ids = fields.One2many('service', 'server_id', string='Services')
    command_ids = fields.One2many('server.command', 'server_id', string='Commands')
    maintenance_ids = fields.One2many('server.maintenance', 'server_id', string='Maintenance Records')
    note = fields.Html('Note')

    @api.constrains('ip_address')
    def _check_ip_address(self):
        """Ensure that the IP address is in a valid format."""
        for record in self:
            if not self._is_valid_ip(record.ip_address):
                raise ValidationError(f"{record.ip_address} is not a valid IP address.")

    @staticmethod
    def _is_valid_ip(ip):
        """Basic validation for an IP address format."""
        pattern = r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$"
        return re.match(pattern, ip) is not None

    def _get_ssh_client(self):
        """Create and return an SSH client connection based on the server's configuration."""
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            if self.password_type == 'password':
                ssh.connect(self.ip_address, port=self.ssh_port, username=self.username, password=self.password)
            elif self.password_type == 'key':
                key = paramiko.RSAKey.from_private_key(self.private_key)
                ssh.connect(self.ip_address, port=self.ssh_port, username=self.username, pkey=key)
            else:
                raise ValidationError("Unknown password type for server authentication.")
            return ssh
        except paramiko.AuthenticationException:
            _logger.error(f"Authentication failed for server {self.name}.")
            raise
        except paramiko.SSHException as e:
            _logger.error(f"SSH connection failed for server {self.name}: {e}")
            raise
        except Exception as e:
            _logger.error(f"Unexpected error during SSH connection for server {self.name}: {e}")
            raise

    def check_server_status(self):
        """Method to check the status of the server."""
        timeout = 10  # Set the timeout value in seconds
        for server in self:
            try:
                ssh = server._get_ssh_client()
                ssh.exec_command("uptime", timeout=timeout)
                server.status = 'running'
                _logger.info(f"Server {server.name} is running.")
            except paramiko.AuthenticationException:
                server.status = 'stopped'
                _logger.error(f"Authentication failed for server {server.name}.")
            except paramiko.SSHException as e:
                server.status = 'error'
                _logger.error(f"SSH connection failed for server {server.name}: {e}")
            except Exception as e:
                server.status = 'error'
                _logger.error(f"Unexpected error while checking the status of server {server.name}: {e}")
            finally:
                server.last_checked = fields.Datetime.now()
                try:
                    ssh.close()
                except Exception:
                    pass

    def _check_server_status_cron(self):
        """Cron job to periodically check the status of all servers."""
        records = self.search([('is_active', '=', True)], limit=500)
        if records:
            records.check_server_status()
            if len(records) == 500:  # Assumes there are more if the limit is hit
                self.env.ref('server_management.ir_cron_check_server_status')._trigger()

    @api.model
    def create(self, vals):
        """Override create method to add additional logic."""
        _logger.info(f"Creating a new server entry: {vals.get('name')}")
        return super(Server, self).create(vals)

    def write(self, vals):
        """Override write method to add additional logic."""
        masked_vals = {k: v if k != 'password' else '***' for k, v in vals.items()}
        _logger.info(f"Updating server {self.name} with values: {masked_vals}")
        return super(Server, self).write(vals)


class ServerCommand(models.Model):
    _name = 'server.command'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Server Command'

    name = fields.Char('Command Name', required=True)
    command = fields.Text('Command', required=True)
    server_id = fields.Many2one('server', string='Server', ondelete='cascade')
    result = fields.Text('Result')
    status = fields.Selection([
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ], string='Status', default='pending')

    @api.model
    def create(self, vals):
        """Override create method to log command creation."""
        _logger.info(f"Creating a new server command: {vals.get('name')} for server ID {vals.get('server_id')}")
        return super(ServerCommand, self).create(vals)

    def execute_command(self):
        """Execute the command on the associated server."""
        for command in self:
            try:
                server = command.server_id
                ssh = server._get_ssh_client()
                command.status = 'running'
                stdin, stdout, stderr = ssh.exec_command(command.command, timeout=20)
                command.result = stdout.read().decode() + stderr.read().decode()
                if stdout.channel.recv_exit_status() == 0:
                    command.status = 'completed'
                    _logger.info(f"Successfully executed command '{command.name}' on server {server.name}.")
                else:
                    command.status = 'failed'
                    _logger.error(f"Command '{command.name}' failed on server {server.name}.")
                command.message_post(body=f"Executed command '{command.name}' on server {server.name}.",
                                     message_type='notification')
            except Exception as e:
                _logger.error(f"Failed to execute command '{command.name}' on server {server.name}: {e}")
                command.result = str(e)
                command.status = 'failed'
                command.message_post(body=f"Failed to execute command '{command.name}' on server {server.name}: {e}",
                                     message_type='notification')
            finally:
                ssh.close()
                command.write({'status': command.status, 'result': command.result})


class ServerMaintenance(models.Model):
    _name = 'server.maintenance'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Server Maintenance'

    name = fields.Char('Maintenance Name', required=True)
    server_id = fields.Many2one('server', string='Server', required=True, ondelete='cascade')
    maintenance_type = fields.Selection([
        ('planned', 'Planned'),
        ('unplanned', 'Unplanned'),
    ], string='Maintenance Type', required=True, default='unplanned')
    start_date = fields.Datetime('Start Date', required=True)
    end_date = fields.Datetime('End Date')
    description = fields.Html('Description')

    status = fields.Selection([
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='scheduled')

    responsible_user_id = fields.Many2one('res.users', string='Responsible User')

    @api.model
    def create(self, vals):
        _logger.info(f"Creating a new maintenance record for server ID {vals.get('server_id')}")
        return super(ServerMaintenance, self).create(vals)

    def start_maintenance(self):
        """Start the maintenance."""
        for maintenance in self:
            maintenance.status = 'in_progress'
            maintenance.server_id.status = 'stopped'
            _logger.info(f"Started maintenance {maintenance.name} for server {maintenance.server_id.name}")

    def complete_maintenance(self):
        """Complete the maintenance."""
        for maintenance in self:
            maintenance.status = 'completed'
            maintenance.server_id.status = 'running'
            maintenance.end_date = fields.Datetime.now()
            _logger.info(f"Completed maintenance {maintenance.name} for server {maintenance.server_id.name}")
