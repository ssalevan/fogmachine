#!/usr/bin/python
"""
model.py defines the database schema for Fogmachine

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

import elixir
import ConfigParser

from sqlalchemy.orm import scoped_session, sessionmaker
elixir.session = scoped_session(sessionmaker(autoflush=True,
    autocommit=True))

from elixir import *
from constants import *

#elixir/sqlalchemy specific config
metadata.bind = DATABASE_CONNECTION
metadata.bind.echo = False

class Host(Entity):
    """
    Represents a Virtualized Host in the database, contains information
    pertaining to its attributes
    """
    hostname = Field(Unicode(255), required=True)
    connection = Field(Unicode(255), required=True)
    virt_type = Field(Unicode(255), required=True)
    free_mem = Field(Integer)
    num_guests = Field(Integer)
    guests = OneToMany('Guest', cascade='all, delete-orphan')
    using_options(tablename='host')
    
class User(Entity):
    """
    Represents a Fogmachine user, pairs a user to the guests they have checked
    out
    """
    username = Field(Unicode(255), required=True)
    password = Field(Unicode(255), required=True)
    email = Field(Unicode(255), required=True)
    is_admin = Field(Boolean, default=False)
    guest_notifications = Field(Boolean, default=True)
    group_notifications = Field(Boolean, default=True)
    guests = OneToMany('Guest', cascade='all, delete-orphan')
    groups = OneToMany('Group', cascade='all, delete-orphan')

class Guest(Entity):
    """
    Represents a Virtualized Guest, paired it to its corresponding Host object
    and the User that created it
    """
    virt_name = Field(Unicode(255), required=True)
    cobbler_profile = Field(Unicode(255), required=True)
    host = ManyToOne('Host', required=True, ondelete='cascade', onupdate='cascade')
    expire_date = Field(DateTime, required=True)
    ram_required = Field(Integer, required=True)
    owner = ManyToOne('User', ondelete='cascade', onupdate='cascade')
    guest_template = ManyToOne('GuestTemplate')
    group = ManyToOne('Group')
    purpose = Field(Unicode(255), default=u"It is a mystery...")
    state = Field(Unicode(255), default=u"unchecked")
    is_provisioned = Field(Boolean, default=False)
    mac_address = Field(Unicode(255))
    ip_address = Field(Unicode(255))
    hostname = Field(Unicode(255))
    vnc_port = Field(Unicode(255))
    
class Group(Entity):
    """
    Represents a collection of instantiated guests which pertain to an
    organization established in a GroupDefinition object
    """
    name = Field(Unicode(255), required=True)
    owner = ManyToOne('User', required=True)
    expire_date = Field(DateTime, required=True)
    is_provisioned = Field(Boolean, default=False)
    purpose = Field(Unicode(255), default=u"It is a mystery...")
    guests = OneToMany('Guest')
    template = ManyToOne('GroupTemplate')
    
class GroupTemplate(Entity):
    """
    Represents a collection of GuestTemplate objects, stratified
    into an ordered collection of guest stratum (in case guests need to
    be provisioned in a sequential order, as is the case when one needs to
    provision an environment with servers and clients)
    """
    name = Field(Unicode(255), required=True)
    groups = OneToMany('Group')
    strata = OneToMany('GuestStratum', order_by='strata_level')
    
class GuestStratum(Entity):
    """
    Represents a layer of GuestTemplate objects
    """
    strata_level = Field(Integer, required=True)
    parent_template = ManyToOne('GroupTemplate', required=True)
    elements = OneToMany('GuestTemplate')
    
class GuestTemplate(Entity):
    """
    Represents a template for provisioning a guest, allows for inclusion of
    Cobbler metavariables and information gleaned post-Fogmachine kickstart
    """
    name = Field(Unicode(255), required=True)
    cobbler_profile = Field(Unicode(255), required=True)
    metavars = Field(Unicode(2047))
    stratum = ManyToOne('GuestStratum')
    provisioned_guests = OneToMany('Guest')
       
setup_all()
create_all()
