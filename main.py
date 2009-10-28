#!/usr/bin/python
"""
main.py contains all the Tornado web handler code required to instantiate a
Fogmachine server

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

import os
import pdb
import re
import logging
import logging.handlers
import logging.config
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web

from logging.handlers import RotatingFileHandler

from tornado.web import RequestHandler

from fogmachine.model import *
from fogmachine.periodic_tasks import *
from fogmachine.virt import *
from fogmachine.taskomatic import *
from fogmachine.constants import *

# log settings
logging.config.fileConfig(LOG_CFGFILE)
log = logging.getLogger("fogmachine.main")

# table which maps textual actions to guest manipulation methods
GUEST_ACTIONS = {
    'delete': remove_guest,
    'start': start_guest,
    'stop': shutdown_guest,
    'destroy': destroy_guest,
    'restart': restart_guest,
    'refresh': update_guest_state,
    'pause': pause_guest,
    'unpause': unpause_guest
}

# table which maps textual actions to group manipulation methods
GROUP_ACTIONS = {
    'delete': remove_group,
    'start': start_group,
    'stop': shutdown_group,
    'destroy': destroy_group,
    'refresh': update_group_state,
    'pause': pause_group,
    'unpause': unpause_group
}

def startup():
    log.info("Turning on the Fogmachine...")
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(LISTEN_PORT)
    add_hosts(CONFIG_LOC)
    start_taskomatic()
    tornado.ioloop.IOLoop.instance().start()

class BaseHandler(RequestHandler):
    def validate_passwords(self):
        if not (self.is_argument_present("password") and self.is_argument_present("confirm_password")):
            return False
        if not (self.get_argument("password") == self.get_argument("confirm_password")):
            return False
        return True
    def get_current_user(self):
        return unicode(self.get_secure_cookie("username"))
    def get_user_object(self):
        return User.get_by(username=self.get_current_user())
    def user_has_guest_auth(self, guest):
        return ((guest.owner == self.get_user_object()) or self.get_user_object().is_admin)
    def user_has_group_auth(self, group):
        return ((group.owner == self.get_user_object()) or self.get_user_object().is_admin)
    def get_guest_object(self, guest_id):
        guest = None
        try:
            if re.match("([a-fA-F0-9]{2}[:]?){5}[a-fA-F0-9]{2}", guest_id):
                # looking up by MAC address of guest
                guest = Guest.get_by(mac_address=unicode(guest_id.lower()))
            else:
                # looking up by strict guest ID number
                guest = Guest.get(int(guest_id))
        except:
            self.send_errmsg("Invalid guest ID.")
        return guest
    def get_group_object(self, group_id):
        group = None
        try:
            group = Group.get(int(group_id))
        except:
            self.send_errmsg("Invalid group ID.")
        return group
    def user_is_admin(self):
        try:
            return self.get_user_object().is_admin
        except:
            return False
    def get_secure_cookie(self, name, if_none=""):
        cook = RequestHandler.get_secure_cookie(self, name)
        if cook == None:
            return if_none
        return cook
    def is_argument_present(self, name):
        return not (self.request.arguments.get(name, None) == None)
    def render(self, template_name, **kwargs):
        error = self.get_secure_cookie("errmsg")
        status = self.get_secure_cookie("statmsg")
        self.clear_cookie("errmsg")
        self.clear_cookie("statmsg")
        #session.clear()
        RequestHandler.render(self,
            template_name,
            is_admin=self.user_is_admin(),
            errmsg=error,
            statmsg=status,
            **kwargs)   
    def send_errmsg(self, errmsg):
        self.set_secure_cookie("errmsg", errmsg)
    def send_statmsg(self, statmsg):
        self.set_secure_cookie("statmsg", statmsg)
            
class MainHandler(BaseHandler):
    def get(self):
        self.render('static/templates/base.html',
            title="Main")
            
class AdminHandler(BaseHandler):
    def get(self):
        hosts = Host.query.order_by('hostname').all()
        guests = {}
        for s_host in hosts:
            guests[s_host] = s_host.guests
        context = {
            'title': "Admin Console",
            'hosts': hosts,
            'guests': guests
        }
        self.render("static/templates/admin.html",
            **context)

class ListHandler(BaseHandler):
    def get(self):
        #TODO: put these in periodic handler
        hosts = Host.query.order_by('hostname').all()
        guests = {}
        for s_host in hosts:
            guests[s_host] = s_host.guests
        context = {
            'title': "List Hosts/Guests",
            'hosts': hosts,
            'guests': guests
        }
        self.render("static/templates/list.html",
            **context)

class CheckoutHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        hosts = Host.query.order_by('hostname').all()
        cobbler = getCobbler()
        profiles = cobbler.get_profiles()
        prof_names = [profile['name'] for profile in profiles]
        context = {
            'title': "Checkout Guests",
            'hosts': hosts,
            'profiles': prof_names
        }
        self.render("static/templates/checkout.html",
            **context)
            
    def post(self):
        try:
            cobbler = getCobbler()
            profile = cobbler.get_profile(self.get_argument("profile"))
            guest = create_guest(
                profile,
                self.get_argument("virt_name"),
                datetime.now() + timedelta(days=int(self.get_argument("expire_days"))),
                self.get_argument("purpose"),
                self.get_user_object())
            if guest is None:
                self.send_errmsg("Host resources inadequate for selected profile.  Try again!")
                self.redirect("/guest/checkout")
            self.send_statmsg("Successfully checked out guest '%s' on %s." % (guest.virt_name, guest.host.hostname))
            log.info("User %s checked out guest '%s' on %s" %
                (self.get_current_user(), guest.virt_name, guest.host.hostname))
            self.redirect("/guest/reservations")
        except:
            self.send_errmsg("Checkout failed:\n%s" % traceback.format_exc())
            self.redirect("/guest/checkout")

class RegisterHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect("/")
            return
        self.render("static/templates/register.html",
            title="User Registration")
    def post(self):
        try:
            if not (self.validate_passwords()):
                self.send_errmsg("Passwords empty/do not match.")
                self.redirect("/user/register")
                return
            if (User.get_by(username=self.get_argument("username"))):
                self.send_errmsg("User '%s' exists." % self.get_argument("username"))
                self.redirect("/user/register")
                return
            newuser = User(username=self.get_argument("username"),
                password=self.get_argument("password"),
                email=self.get_argument("email"))
            session.flush()
            self.set_secure_cookie("username", newuser.username)
            self.send_statmsg("Successfully created account '%s'." % newuser.username)
            self.redirect("/")
        except:
            self.send_errmsg("Registration failed:\n%s" % traceback.format_exc())
            self.redirect("/user/register")
                
class ProfileHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = User.get_by(username=self.current_user)
        context = {
            'title': 'Your Profile',
            'username': user.username,
            'email': user.email
        }
        self.render("static/templates/profile.html",
            **context)
    def post(self):
        try:
            if not (self.validate_passwords()):
                self.send_errmsg("Passwords empty/do not match.")
                self.redirect("/user/profile")
                return
            user = User.get_by(username=self.current_user)
            user.password = self.get_argument("password")
            user.email = self.get_argument("email")
            session.flush()
            self.send_statmsg("Successfully edited profile.")
            self.redirect("/user/profile")
        except:
            self.send_errmsg("Profile change failed:\n%s" % traceback.format_exc())
            self.redirect("/user/profile")
                
class ReservationsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        session.clear()
        user = User.get_by(username=self.current_user)
        context = {
            'title': "Your Reservations",
            'guests': user.guests
        }
        self.render("static/templates/reservations.html",
            **context)

class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/templates/login.html",
            title="Login")
    def post(self):
        try:
            user = User.get_by(username=self.get_argument("username"))
            if user.password == self.get_argument("password"):
                log.info("User %s logged in successfully." % 
                    user.username)
                self.set_secure_cookie("username", user.username)
                self.send_statmsg("Successfully logged in.")
                self.redirect("/")
            else:
                log.info("User %s failed login." % 
                    user.username)
                self.send_errmsg("Username or password incorrect")
                self.redirect("/user/login")
        except:
            log.info("Failed login: username: %s, pass: %s." % 
                (self.get_argument("username"), self.get_argument("password")))
            log.info("Resulting traceback:\n%s" % traceback.format_exc())
            self.send_errmsg("Username or password incorrect")
            self.redirect("/user/login")

class LogoutHandler(BaseHandler):
    def get(self):
        log.info("User %s logged out successfully." % 
                    self.get_current_user())
        self.clear_cookie("username")
        self.send_statmsg("Successfully logged out.")
        self.redirect("/")

class GuestActionHandler(BaseHandler):
    """
    Handles actions for guests in a REST-ful manner, such as setting
    hostname/ip or running libvirt calls (create, destroy, undefine, etc.)
    """
    def post(self, guest_id, action):
        guest = self.get_guest_object(guest_id)
        curr_user = self.get_user_object()
        
        if not self.user_has_guest_auth(guest):
            self.send_errmsg("You are not authorized to perform this action.")
        elif action == "extend":
            try:
                log.info("User %s extended reservation for guest %s by %s days." % 
                    (curr_user.username, 
                     guest.virt_name,
                     int(self.get_argument("days").strip())))
                extend_guest_reservation(guest, 
                    int(self.get_argument("days").strip()))
                self.send_statmsg("Successfully extended guest reservation by %s days." %
                    int(self.get_argument("days").strip()))
            except:
                self.send_errmsg("Reservation extension failed:\n%s" % 
                    traceback.format_exc())
        else:
            self.send_errmsg("Invalid action.")
        update_guest_state(guest)
        self.redirect(self.request.headers["Referer"])
    
    def get(self, guest_id, action):
        guest = self.get_guest_object(guest_id)
        curr_user = self.get_user_object()
        
        # action-handling logic...  here
        if action == "set":
            # handle special case of guests phoning home after kickstart
            # obviously we can't utilize the user cookie, so this
            # is more or less a gaping security hole
            guest.ip_address = unicode(self.get_argument("ip"))
            guest.hostname = unicode(self.get_argument("hostname"))
            session.flush()
            log.info("Guest %s registered with hostname: %s, ip: %s" %
                (guest.virt_name, guest.hostname, guest.ip_address))
            self.write("1")
            run_triggers(guest)
            return
        elif action == "getuser":
            # handle another special case, where you want to get the username
            # of the owner of the guest over HTTP...  useful for Satellite
            # installations and the like
            log.info("User info requested for guest %s." % guest.virt_name)
            self.write("%s,%s" % (guest.owner.username, guest.owner.email))
            return
        elif not self.user_has_guest_auth(guest):
            self.send_errmsg("You are not authorized to perform this action.")
        
        log.info("User %s ran action '%s' on guest %s." % 
            (curr_user.username, action, guest.virt_name))
        
        try:
            guest_name = guest.virt_name
            GUEST_ACTIONS[action](guest)
            self.send_statmsg("Successfully ran '%s' action on guest %s." %
                (action, guest_name))
        except:
            self.send_errmsg("Guest action %s failed:\n%s" % (action, traceback.format_exc()))
        
        # update the guest state (unless we've deleted it)
        if action != "delete":
            update_guest_state(guest)
        
        self.redirect(self.request.headers["Referer"])
        
class GroupActionHandler(BaseHandler):
    """
    Handles actions for groups in a REST-ful manner
    """
    def get(self, group_id, action):
        group = self.get_group_object(group_id)
        if group == None:
            # group lookup failed, redirect user to from whence they came
            self.redirect(self.request.headers["Referer"])
        curr_user = self.get_user_object()
        if not self.user_has_group_auth(group):
            self.send_errmsg("You are not authorized to perform this action.")
        
        try:
            group_name = group.name
            GROUP_ACTIONS[action](group)
            self.send_statmsg("Successfully ran '%s' action on group %s." %
                (action, group_name))
        except:
            self.send_errmsg("Group action %s failed:\n%s" % (action, traceback.format_exc()))
        
        # update the guest state (unless we've deleted it)
        if action != "delete":
            update_group_state(group)
        
        self.redirect(self.request.headers["Referer"])
    
class GroupCheckoutHandler(BaseHandler):
    pass
    
class GroupReservationsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        user = User.get_by(username=self.current_user)
        context = {
            'title': "Your Group Reservations",
            'groups': user.groups
        }
        self.render("static/templates/group_reservations.html",
            **context)

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "login_url": "/user/login",
    "cookie_secret": "984fewh43fwaaLIUEF/=EFE9isvjkrvsdsnvakeuf3"
}
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/guest/list", ListHandler),
    (r"/guest/checkout", CheckoutHandler),
    (r"/guest/reservations", ReservationsHandler),
    (r"/guest/([0-9a-fA-F:]+)/([a-z]+)", GuestActionHandler),
    (r"/group/checkout", GroupCheckoutHandler),
    (r"/group/reservations", GroupReservationsHandler),
    (r"/group/([0-9])/([a-z]+)", GroupActionHandler),
    (r"/user/login", LoginHandler),
    (r"/user/logout", LogoutHandler),
    (r"/user/profile", ProfileHandler),
    (r"/user/register", RegisterHandler),
    (r"/admin", AdminHandler)],
    **settings)
    
if __name__ == "__main__":
    startup()
