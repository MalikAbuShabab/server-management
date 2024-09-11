from odoo.tests.common import TransactionCase

class TestServerManagement(TransactionCase):

    def setUp(self):
        super(TestServerManagement, self).setUp()
        # Set up test data
        self.Server = self.env['server']
        self.ServerCommand = self.env['server.command']
        self.ServerMaintenance = self.env['server.maintenance']
        self.test_server = self.Server.create({
            'name': 'Test Server',
            'ip_address': '192.168.1.1',
            'username': 'testuser',
            'password': 'testpassword',
            'password_type': 'password',
        })
        self.test_command = self.ServerCommand.create({
            'name': 'Test Command',
            'command': 'echo Hello World',
            'server_id': self.test_server.id,
        })
        self.test_maintenance = self.ServerMaintenance.create({
            'name': 'Test Maintenance',
            'server_id': self.test_server.id,
            'maintenance_type': 'planned',
            'start_date': '2024-09-01 00:00:00',
        })

    def test_server_creation(self):
        """ Test the creation of a server """
        server = self.Server.search([('name', '=', 'Test Server')])
        self.assertEqual(len(server), 1, "Server creation failed")

    def test_command_execution(self):
        """ Test execution of a server command """
        self.test_command.execute_command()
        self.assertEqual(self.test_command.status, 'completed', "Command execution failed")

    def test_maintenance_creation(self):
        """ Test the creation of a maintenance record """
        maintenance = self.ServerMaintenance.search([('name', '=', 'Test Maintenance')])
        self.assertEqual(len(maintenance), 1, "Maintenance creation failed")

    def test_maintenance_status_change(self):
        """ Test changing maintenance status """
        self.test_maintenance.start_maintenance()
        self.assertEqual(self.test_maintenance.status, 'in_progress', "Maintenance start status change failed")
        self.test_maintenance.complete_maintenance()
        self.assertEqual(self.test_maintenance.status, 'completed', "Maintenance complete status change failed")

    def test_ip_address_validation(self):
        """ Test IP address validation """
        with self.assertRaises(Exception, msg="192.168.1.256 should be an invalid IP address"):
            self.Server.create({
                'name': 'Invalid IP Server',
                'ip_address': '192.168.1.256',
                'username': 'invaliduser',
                'password': 'invalidpassword',
            })
