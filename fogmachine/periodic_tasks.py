#!/usr/bin/python
"""
periodic_tasks.py defines all related helper methods which enable Fogmachine
to manipulate virtual guests, groups of virtual guests, and virtual hosts

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

import xmlrpclib
import logging
import re
import random
from datetime import datetime, timedelta
from libvirt import libvirtError
from itertools import ifilter

from model import *
from virt import *
from constants import *

def getCobbler():
    return xmlrpclib.Server(COBBLER_API)
    
def getCobblerToken():
    return getCobbler().login(COBBLER_USER, COBBLER_PASS)

def getVirt(host):
    """
    Convenience function:
    Returns a Virt object corresponding to the Host object passed in
    (the heavy lifting goes on in Virt, so this makes life a little easier)
    """
    virt = Virt(host.connection, host.hostname)
    return virt

def _read_config(file_loc):
    """
    Opens config file, strips comments, returns list of hosts specified
    """
    cfg_file = open(file_loc, 'r')
    cfg_lines = cfg_file.readlines()
    entries = []
    for line in cfg_lines:
        # strip comments/surrounding whitespace
        line = re.sub("#.*","",line).strip()
        # check if line matches comma-separated entry pattern
        if(re.match(".*,.*,.*",line)):
            entry = line.split(',')
            entries.append([
                unicode(entry[0].strip()),
                unicode(entry[1].strip()),
                unicode(entry[2].strip())])
    cfg_file.close()
    return entries
    
def add_hosts(file_loc):
    """
    Adds hosts contained within specified Fogmachine hosts config file
    """
    all_hosts = _read_config(file_loc)
    # clean out hosts no longer present
    for host in Host.query.all():
        if not [host.hostname, host.connection, host.virt_type] in all_hosts:
            session.delete(host)
    # add new hosts (if any)
    for host in _read_config(file_loc):
        if not Host.get_by(hostname=host[0]):
            newhost = Host(hostname=host[0],
                connection=host[1],
                virt_type=host[2])
    session.flush()
    
def get_cobbler_profiles_for_template(group_template):
    """
    Returns the names of the cobbler profiles contained within a GroupTemplate
    object
    """
    cobbler_profiles = []
    for stratum in group_template.strata:
        cobbler_profiles.extend(
            [guest_temp.cobbler_profile
                for guest_temp in stratum.elements])
    return cobbler_profiles
    
def get_available_ram(host):
    """
    Gets the amount of RAM available for provisioning new guests on the
    supplied host, equivalent to free memory - memory required for all managed
    guests
    """
    stopped_guests = Guest.query.filter(Guest.host == host 
        and Guest.state != u"running").all()
    stopped_guest_ram = sum([guest.ram_required for guest in stopped_guests])
    return host.free_mem - stopped_guest_ram
    
def get_random_mac():
    """
    from xend/server/netif.py
    Generate a random MAC address.
    Uses OUI 00-16-3E, allocated to
    Xensource, Inc.  Last 3 fields are random.
    return: MAC address string
    """
    mac = [ 0x00, 0x16, 0x3e,
        random.randint(0x00, 0x7f),
        random.randint(0x00, 0xff),
        random.randint(0x00, 0xff) ]
    return ':'.join(map(lambda x: "%02x" % x, mac))
    
def create_guest(target_obj, virt_name, expire_date, purpose, owner, system=False):
    """
    Creates a guest using the install() function from Virt then creates a database
    entry for the new guest, returning this entry for your pleasure
    """
    host = find_suitable_host(target_obj, system)
    
    if host is None:
        return None
        
    virt = getVirt(host)
    cobbler = getCobbler()
    
    if system:
        ram_required = cobbler.get_profile(target_obj['profile'])['virt_ram']
        virt.install(COBBLER_HOST, target_obj['name'], virt_name=virt_name, system=True)
    else:
        ram_required = target_obj['virt_ram']
        virt.install(COBBLER_HOST, target_obj['name'], virt_name=virt_name)
    newguest = Guest(virt_name=virt_name,
        ram_required=int(ram_required),
        cobbler_profile=unicode(target_obj['name']),
        expire_date=expire_date,
        purpose=purpose,
        host=host,
        owner=owner,
        mac_address=virt.get_mac_address(virt_name))
    session.flush()
    return newguest

def extend_guest_reservation(guest, days):
    """
    Extends the expiration date for the supplied guest by the supplied 
    number of days
    """
    guest.expire_date = guest.expire_date + timedelta(days=days)
    session.flush()

def find_suitable_host(target, system=False):
    """
    Given a Cobbler profile hash (taken from Cobbler's XMLRPC output),
    figures out what Host to provision the guest onto and returns this
    object
    """
    if system:
        # inherit information from system's associated Cobbler profile
        target = getCobbler().get_profile(target['profile'])
    mem_needed = target['virt_ram']
    vcpus_needed = target['virt_cpus']
    virt_type = unicode(target['virt_type'])
    hosts = Host.query.filter(Host.free_mem >= mem_needed and 
        Host.virt_type == virt_type).order_by('free_mem').all()
    if len(hosts) is 0:
        return None
    return hosts[len(hosts) - 1]
    
def hosts_can_provision_group(group_template):
    """
    Given a GroupTemplate object and a Cobbler object, determines whether
    a group can be provisioned within the confines of the resources 
    available from your current virtual hosts
    """
    cobbler_profiles = get_cobbler_profiles_for_template(group_template)
    
    # see if we have enough RAM
    ram_required = [getCobbler().get_profile(profile)['virt_ram']
        for profile in cobbler_profiles]
    ram_required.sort(reverse=True)
    ram_on_each_host = [get_available_ram(host)
        for host in Host.query.all()]
    ram_on_each_host.sort(reverse=True)
        
    for single_req in ram_required:
        space_allocated = False
        for i in xrange(0,len(ram_on_each_host)):
            if ram_on_each_host[i] >= single_req:
                ram_on_each_host[i] -= single_req
                space_allocated = True
                break
        if not space_allocated:
            return False
            
    return True

def update_free_mem():
    """
    Periodic task (run by taskomatic):
    Updates available memory for all Host objects via libvirt
    """
    for host in Host.query.all():
        virt = getVirt(host)
        host.free_mem = virt.freemem()
        host.num_guests = virt.get_number_of_guests()
    session.flush()
    
def update_guest_states():
    """
    Updates state (running status, vnc ports) for all Guest objects
    """
    for guest in Guest.query.all():
        update_guest_state(guest)

def retire_expired_guests():
    """
    Periodic task:
    Deletes Guest objects whose expiration dates have passed
    """
    for guest in Guest.query.all():
        if guest.expire_date < datetime.now():
            remove_guest(guest)

def update_guest_state(guest):
    """
    Updates state (running status, vnc port) for a single Guest
    """
    if guest == None:
        return
    virt = getVirt(guest.host)
    guest.state = virt.get_status(guest.virt_name)
    guest.vnc_port = virt.get_vnc_port(guest.virt_name)
    session.flush()

def remove_guest(guest):
    """
    By hook or by crook, removes a guest from a virt host and then
    deletes its corresponding Guest object from the database
    """
    virt = getVirt(guest.host)
    try:
        virt.destroy(guest.virt_name)
    except libvirtError:
        pass # libvirt throws error if guest is already shutdown
    virt.undefine(guest.virt_name)
    
    # remove any links to guest from related tables
    guest.host.guests.remove(guest)
    if guest.guest_template != None:
        guest.guest_template.provisioned_guests.remove(guest)
        guest.group.guests.remove(guest)
    
    # get rid of the durn thing
    session.delete(guest)
    session.flush()
    
def send_guest_complete_email(guest):
    """
    Sends a notification e-mail to the owner of a freshly-provisioned guest,
    notifying them that their guest has been successfully provisioned
    """
    pass

def send_group_complete_email(group):
    """
    Sends a notification e-mail to the owner of a freshly-provisioned group,
    notifying them that their group has been successfully provisioned
    """
    pass
   
def run_triggers(guest):
    """
    Sends provisioning completed emails to guest owners, runs group-related
    triggers if guest belongs to a group
    """
    if not guest.is_provisioned:
        guest.is_provisioned = True
        session.flush()
        send_guest_complete_email(guest)
        run_group_triggers(guest)
        
def run_group_triggers(guest):
    """
    Checks if the guest is a member of a group, runs next sequential
    provisioning step if all guests on current group stratum are
    provisioned
    """
    if guest.group == None:
        return
    # get other guests in guest's group
    of_group = Guest.query.filter(Guest.group==guest.group).all()
    
    # check if provisioning is complete on the current guest stratum
    for group_guest in of_group:
        if (guest.guest_template.stratum == group_guest.guest_template.stratum):
            if not group_guest.is_provisioned:
                return
            
    next_strata = get_next_guest_stratum(guest.guest_template.stratum)
    provision_group_guest_stratum(guest.group, 
        next_strata)

def get_next_guest_stratum(stratum):
    """
    Returns the next sequential stratum in a GroupTemplate given the supplied
    GuestStratum object
    """
    cur_level = stratum.strata_level
    if len(stratum.parent_template.strata) == cur_level + 1:
        return None
    return stratum.parent_template.strata[cur_level + 1]
    
def replace_fogmachine_variables(group, metavars):
    """
    Given a metavariable string (which ends up being passed to Cobbler),
    replaces any text contained within {% and %} delimiters with the 
    information requested and converts the string to a dictionary suitable
    for being passed to Cobbler
    """
    to_replace = re.finditer('{%(.*?)%}', metavars)
    for elem in to_replace:
        # figure out matching text
        complete_match = elem.group(0)
        contents = elem.group(1).strip()
        # get guest template and requested attribute from text
        guest_template = contents.split('.')[0]
        attribute = contents.split('.')[1]
        # grab the corresponding guest to the GuestTemplate 
        # from the supplied group
        gt_obj = GuestTemplate.query.filter(
            GuestTemplate.name==guest_template).one()
        guest_obj = Guest.query.filter(Guest.group==group
            and Guest.guest_template==gt_obj).one()
        # get the requested attribute, pickle it, and replace the delimited 
        # text
        replacement = str(getattr(guest_obj, attribute))
        metavars = metavars.replace(complete_match, replacement)
    # convert metavar string to dict
    mv_dict = {}
    metavar_list = [metavar.strip() for metavar in metavars.split(',')]
    for mv in metavar_list:
        key = mv.split('=')[0].strip()
        value = mv.split('=')[1].strip()
        mv_dict[key] = value
    return mv_dict

def start_group(group):
    """
    Starts all provisioned guests in a supplied group
    """
    guests = Guest.query.filter(Guest.group==group and 
        Guest.state!=u'running' and Guest.is_provisioned==True).all()
    for guest in guests:
        start_guest(guest)
        
def shutdown_group(group):
    """
    Shuts down all provisioned guests in a supplied group
    """
    guests = Guest.query.filter(Guest.group==group and
        Guest.state!=u'shutdown' and Guest.is_provisioned==True).all()
    for guest in guests:
        shutdown_guest(guest)
        
def pause_group(group):
    """
    Pauses all provisioned guests in a supplied group
    """
    guests = Guest.query.filter(Guest.group==group and
        Guest.state!=u'paused' and Guest.is_provisioned==True).all()
    for guest in guests:
        pause_guest(guest)
        
def unpause_group(group):
    """
    Unpauses all provisioned guests in a supplied group
    """
    guests = Guest.query.filter(Guest.group==group and
        Guest.state==u'paused' and Guest.is_provisioned==True).all()
    for guest in guests:
        unpause_guest(guest)

def provision_group_guest_stratum(group, guest_stratum):
    """
    Provisions a guest stratum defined in a GroupTemplate, inserts the 
    resulting guests into the 'guests' list of the supplied Group object
    """
    
    if guest_stratum == None:
        group.is_provisioned = True
        session.flush()
        send_group_complete_email(group)
        return
    
    for guest_template in guest_stratum.elements:
        # if user has added {% and %} delimiters to the supplied metavars,
        # they want Fogmachine to replace the text within them with something
        # more useful (IE: hostname, IP, etc.), so we do that here:
        new_metavars = replace_fogmachine_variables(group,
            guest_template.metavars)
            
        # create a unique Cobbler System object for the supplied profile and
        # metavars
        cobbler = getCobbler()
        token = getCobblerToken()
        virt_bridge = cobbler.get_profile(
            guest_template.cobbler_profile)['virt_bridge']
            
        system = cobbler.new_system(token)
        cobbler.modify_system(system, "name",
            "%s-%s" % (group.name, guest_template.name), token)
        cobbler.modify_system(system, "profile",
            guest_template.cobbler_profile, token)
        cobbler.modify_system(system, "ksmeta",
            new_metavars, token)
        cobbler.modify_system(system, "modify_interface", {
            "macaddress-eth0" : get_random_mac(),
            "virtbridge-eth0" : virt_bridge
        }, token)
        
        cobbler.save_system(system, token)
        
        sys_obj = cobbler.get_system("%s-%s" % (group.name, guest_template.name))
        
        # find a suitable host and get the required memory
        ram_required = cobbler.get_profile(
            guest_template.cobbler_profile)['virt_ram']
            
        # create the guest based off of the System object we created
        guest = create_guest(sys_obj,
            u"%s-%s" % (group.name, guest_template.name),
            group.expire_date, group.purpose, group.owner,
            system=True)
        guest.group = group
        guest.guest_template = guest_template
        guest.guest_template.provisioned_guests.append(guest)
        session.flush()
    
def create_group(group_template, name, owner, expire_date, purpose):
    """
    Instantiates a group of machines based upon the supplied group template,
    requires a Cobbler object (as returned by main.py's getCobbler method)
    to function
    """
    if not hosts_can_provision_group(group_template):
        return False
    group = Group(name=name,
        owner=owner,
        expire_date=expire_date,
        purpose=purpose,
        template=group_template)
    session.flush()
    provision_group_guest_stratum(group, group_template.strata[0])
    return True
    
def remove_group(group):
    """
    Removes a group and all related bindings
    """
    for guest in group.guests:
        remove_guest(guest)
    group.template.groups.remove(group)
    session.delete(group)
    session.flush()
    
def start_guest(guest):
    """
    Starts the guest which corresponds to the supplied Guest object
    """
    virt = getVirt(guest.host)
    virt.create(guest.virt_name)
    
def shutdown_guest(guest):
    """
    Shuts down the guest which corresponds to the supplied Guest object
    """
    virt = getVirt(guest.host)
    virt.shutdown(guest.virt_name)
    
def destroy_guest(guest):
    """
    Destroys the guest which corresponds to the supplied Guest object
    """
    virt = getVirt(guest.host)
    virt.destroy(guest.virt_name)
    
def restart_guest(guest):
    """
    Restarts the guest which corresponds to the supplied Guest object
    """
    shutdown_guest(guest)
    start_guest(guest)
    
def pause_guest(guest):
    """
    Pauses the guest which corresponds to the supplied Guest object
    """
    virt = getVirt(guest.host)
    virt.pause(guest.virt_name)
    
def unpause_guest(guest):
    """
    Unpauses the guest which corresponds to the supplied Guest object
    """
    virt = getVirt(guest.host)
    virt.unpause(guest.virt_name)
