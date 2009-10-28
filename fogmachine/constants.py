#!/usr/bin/python
"""
constants.py serves as a class which allows all Fogmachine-related tools
to access constants specified in the Fogmachine configuration file,
fogmachine.conf

Copyright 2009, Red Hat, Inc
Steve Salevan <ssalevan@redhat.com>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 2 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
02110-1301  USA
"""

import ConfigParser

FOGMACHINE_CFG = "/etc/fogmachine/fogmachine.conf"
CONFIG_LOC = "/etc/fogmachine/virthosts.conf"
LOG_CFGFILE = "/etc/fogmachine/logging.conf"

def get_fogmachine_config():
    config = ConfigParser.ConfigParser()
    config.read(FOGMACHINE_CFG)
    return config
    
COBBLER_HOST = get_fogmachine_config().get('fogmachine', 'cobbler_server')
COBBLER_USER = get_fogmachine_config().get('fogmachine', 'cobbler_user')
COBBLER_PASS = get_fogmachine_config().get('fogmachine', 'cobbler_password')

COBBLER_API = "http://%s/cobbler_api" % COBBLER_HOST

LISTEN_PORT = int(get_fogmachine_config().get('fogmachine', 'listen_port'))
DATABASE_CONNECTION = get_fogmachine_config().get('fogmachine', 'database_connection')
