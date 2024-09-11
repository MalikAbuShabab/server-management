# Server Management Module for Odoo

## Overview

This Odoo module allows users to manage servers, execute server commands via SSH, and track planned and unplanned maintenance activities. The module provides functionality to define servers, issue commands, and monitor server maintenance events.

### Features:
- Manage servers with essential details like name, IP address, and server type.
- Execute SSH commands on servers through the Odoo interface.
- Log both planned and unplanned maintenance activities for servers.
- Define different user roles and security permissions for managing servers and maintenance tasks.
- Customizable actions for server management and command execution.

## Models

### 1. **Server**
Manages details about the servers, including:
- Server Name
- IP Address
- Server Type (e.g., Web, Database, File Storage)
- User Authentication (password or SSH key)
- Status (active/inactive)

### 2. **Server Command**
Handles the commands that can be executed on the server. Features:
- Command Name (e.g., `Reboot`, `Check Disk Space`)
- Command (e.g., `sudo reboot`, `df -h`)
- Log of executed commands and results

### 3. **Server Maintenance**
Manages server maintenance activities, such as:
- Planned Maintenance: Scheduled maintenance activities.
- Unplanned Maintenance: Tracking server downtime or unscheduled repairs.
- Maintenance Details: Duration, status, and actions taken.

## Installation

1. Download or clone the module into the Odoo `addons` directory.
   ```bash
   git clone https://github.com/MalikAbuShabab/server-management /path/to/odoo/addons/