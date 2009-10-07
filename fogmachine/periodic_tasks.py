#!/usr/bin/python

import xmlrpclib
import logging
from datetime import datetime, timedelta
from libvirt import libvirtError

from model import *
from virt import *

def getVirt(host):
    """
    Convenience function:
    Returns a Virt object corresponding to the Host object passed in
    (the heavy lifting goes on in Virt, so this makes life a little easier)
    """
    virt = Virt(host.connection, host.hostname)
    return virt
    
def create_guest(host, profile, virt_name, expire_days, purpose, owner, cobbler_host):
    """
    Creates a guest using the install() function from Virt then creates a database
    entry for the new guest, returning this entry for your pleasure
    """
    virt = getVirt(host)
    virt.install(cobbler_host, profile, virt_name=virt_name)
    newguest = Guest(virt_name=virt_name,
        cobbler_profile=profile,
        expire_date=datetime.now() + timedelta(days=int(expire_days)),
        purpose=purpose,
        host=host,
        owner=owner,
        mac_address=virt.get_mac_address(virt_name))
    session.commit()
    return newguest

def find_suitable_host(profile):
    """
    Given a Cobbler profile hash (taken from Cobbler's XMLRPC output),
    figures out what Host to provision the guest onto and returns this
    object
    """
    mem_needed = profile['virt_ram']
    vcpus_needed = profile['virt_cpus']
    virt_type = unicode(profile['virt_type'])
    hosts = Host.query.filter(Host.free_mem >= mem_needed and 
        Host.virt_type == virt_type).order_by('free_mem').all()
    if len(hosts) is 0:
        return None
    return hosts[0]

def update_free_mem():
    """
    Periodic task (run by taskomatic):
    Updates available memory for all Host objects via libvirt
    """
    for host in Host.query.all():
        virt = getVirt(host)
        host.free_mem = virt.freemem()
        host.num_guests = virt.get_number_of_guests()
    session.commit()
    
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
    virt = getVirt(guest.host)
    guest.state = virt.get_status(guest.virt_name)
    guest.vnc_port = virt.get_vnc_port(guest.virt_name)
    session.commit()

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
    session.delete(guest)
    session.commit()
    
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
