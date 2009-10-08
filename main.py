#!/usr/bin/python
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
from fogmachine.config_reader import add_hosts

#variables that you might want to change (location of cobbler host, vhost config file)
#COBBLER_HOST = "vpn-12-144.rdu.redhat.com"
COBBLER_HOST = "marillion.rdu.redhat.com"
COBBLER_API = "http://%s/cobbler_api" % COBBLER_HOST
COBBLER_USER = "cobbler"
COBBLER_PASS = "dog8code"
CONFIG_LOC = "./virthosts.conf"
LISTEN_PORT = 8888

#log settings
LOG_CFGFILE = "./logging.conf"
logging.config.fileConfig(LOG_CFGFILE)

log = logging.getLogger("fogmachine.main")

def startup():
    log.info("Turning on the Fogmachine...")
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(LISTEN_PORT)
    add_hosts(CONFIG_LOC)
    start_taskomatic()
    tornado.ioloop.IOLoop.instance().start()

def getCobbler():
    return xmlrpclib.Server(COBBLER_API)
    
def getCobblerToken():
    return getCobbler().login(COBBLER_USER, COBBLER_PASS)

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
            profiles = cobbler.get_profiles()
            selected_profile = None
            for profile in profiles:
                if profile['name'] == self.get_argument("profile"):
                    selected_profile = profile
            host = find_suitable_host(selected_profile)
            if host is None:
                self.send_errmsg("Host resources inadequate for selected profile.  Try again!")
                self.redirect("/guest/checkout")
            guest = create_guest(host,
                self.get_argument("profile"),
                self.get_argument("virt_name"),
                self.get_argument("expire_days"),
                self.get_argument("purpose"),
                self.get_user_object(),
                COBBLER_HOST)
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
            session.commit()
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
            session.commit()
            self.send_statmsg("Successfully edited profile.")
            self.redirect("/user/profile")
        except:
            self.send_errmsg("Profile change failed:\n%s" % traceback.format_exc())
            self.redirect("/user/profile")
                
class ReservationsHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
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
    def get(self, guest_id, action):
        # guest_id-handling logic here
        guest = None
        curr_user = self.get_user_object()
        try:
            if re.match("([a-fA-F0-9]{2}[:]?){5}[a-fA-F0-9]{2}", guest_id):
                # looking up by MAC address of guest
                guest = Guest.get_by(mac_address=unicode(guest_id.lower()))
            else:
                # looking up by strict guest ID number
                guest = Guest.get(int(guest_id))
        except:
            self.send_errmsg("Invalid guest ID.")
        # action-handling logic...  here
        if action == "set":
            # handle special case of guests phoning home after kickstart
            # obviously we can't utilize the user cookie, so this
            # is more or less a gaping security hole
            guest.ip_address = unicode(self.get_argument("ip"))
            guest.hostname = unicode(self.get_argument("hostname"))
            session.commit()
            log.info("Guest %s registered with hostname: %s, ip: %s" %
                (guest.virt_name, guest.hostname, guest.ip_address))
            self.write("1")
            return
        elif not ((guest.owner == curr_user) or curr_user.is_admin):
            self.send_errmsg("You are not authorized to perform this action.")
        elif action == "delete":
            try:
                log.info("User %s deleted guest %s." % 
                    (curr_user.username, guest.virt_name))
                remove_guest(guest)
                self.send_statmsg("Successfully deleted guest.")
            except:
                self.send_errmsg("Guest delete failed:\n%s" % traceback.format_exc())
        elif action == "start":
            try:
                log.info("User %s started guest %s." % 
                    (curr_user.username, guest.virt_name))
                start_guest(guest)
                self.send_statmsg("Successfully started guest.")
            except:
                self.send_errmsg("Guest start failed:\n%s" % traceback.format_exc())
        elif action == "stop":
            try:
                log.info("User %s shutdown guest %s." % 
                    (curr_user.username, guest.virt_name))
                shutdown_guest(guest)
                self.send_statmsg("Successfully shut guest down.")
            except:
                self.send_errmsg("Guest shutdown failed:\n%s" % traceback.format_exc())
        elif action == "destroy":
            try:
                log.info("User %s destroyed guest %s." % 
                    (curr_user.username, guest.virt_name))
                destroy_guest(guest)
                self.send_statmsg("I totally destroyed that guest.")
            except:
                self.send_errmsg("Guest destruction failed:\n%s" % traceback.format_exc())
        elif action == "restart":
            try:
                log.info("User %s restarted guest %s." % 
                    (curr_user.username, guest.virt_name))
                restart_guest(guest)
                self.send_statmsg("Successfully restarted guest.")
            except:
                self.send_errmsg("Guest restart failed:\n%s" % traceback.format_exc())
        elif action == "pause":
            try:
                log.info("User %s paused guest %s." % 
                    (curr_user.username, guest.virt_name))
                pause_guest(guest)
                self.send_statmsg("Successfully paused guest.")
            except:
                self.send_errmsg("Guest pause failed:\n%s" % traceback.format_exc())
        elif action == "unpause":
            try:
                log.info("User %s unpaused guest %s." % 
                    (curr_user.username, guest.virt_name))
                unpause_guest(guest)
                self.send_statmsg("Successfully unpaused guest.")
            except:
                self.send_errmsg("Guest unpause failed:\n%s" % traceback.format_exc())
        else:
            self.send_errmsg("Invalid action.")
        update_guest_state(guest)
        self.redirect(self.request.headers["Referer"])

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
    (r"/guest/([0-9a-fA-f:]+)/([a-z]+)", GuestActionHandler),
    (r"/user/login", LoginHandler),
    (r"/user/logout", LogoutHandler),
    (r"/user/profile", ProfileHandler),
    (r"/user/register", RegisterHandler),
    (r"/admin", AdminHandler)],
    **settings)
    
if __name__ == "__main__":
    startup()
