#!/usr/bin/python

import xmlrpclib
from datetime import datetime, timedelta

from model import *
from virt import *

def getVirt(host):
    virt = Virt(host.connection, host.hostname)
    return virt
    
def create_guest(host, profile, virt_name, expire_days, purpose, owner, cobbler_host):
    virt = getVirt(host)
    virt.install(cobbler_host, profile, virt_name=virt_name)
    newguest = Guest(virt_name=virt_name,
        cobbler_profile=profile,
        expire_date=datetime.now() + timedelta(days=int(expire_days)),
        purpose=purpose,
        host=host,
        owner=owner)
    session.commit()
    return newguest

def update_free_mem():
    for host in Host.query.all():
        virt = getVirt(host)
        host.free_mem = virt.freemem()
    session.commit()
    
def update_guest_states():
    for guest in Guest.query.all():
        update_guest_state(guest)

def retire_expired_guests():
    for guest in Guest.query.all():
        if guest.expire_date > datetime.now():
            remove_guest(guest)

def update_guest_state(guest):
    virt = getVirt(guest.host)
    guest.status = virt.get_status(guest.virt_name)
    session.commit()

def remove_guest(guest):
    virt = getVirt(guest.host)
    virt.shutdown(guest.virt_name)
    virt.undefine(guest.virt_name)
    session.delete(guest)
    session.commit()
