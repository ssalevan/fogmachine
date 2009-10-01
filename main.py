#!/usr/bin/python
import os
import pdb
import traceback
import tornado.httpserver
import tornado.ioloop
import tornado.web

from fogmachine.model import *
from fogmachine.periodic_tasks import *
from fogmachine.virt import *
from fogmachine.config_reader import add_hosts
from tornado.web import RequestHandler

#variables that you might want to change (location of cobbler host, vhost config file)
COBBLER_HOST = "sat-blade-8.idm.lab.bos.redhat.com"
COBBLER_API = "http://%s/cobbler_api" % COBBLER_HOST
COBBLER_USER = "cobbler"
COBBLER_PASS = "dog8code"
CONFIG_LOC = "./virthosts.conf"
LISTEN_PORT = 8888

def getCobbler():
    cobbler = xmlrpclib.Server(COBBLER_API)
    cobbler.login(COBBLER_USER, COBBLER_PASS)
    return cobbler

class BaseHandler(RequestHandler):
    def validate_passwords(self):
        if not (self.is_argument_present("password") and self.is_argument_present("confirm_password")):
            return False
        if not (self.get_argument("password") == self.get_argument("confirm_password")):
            return False
        return True
    def get_current_user(self):
        return self.get_secure_cookie("username")
    def get_user_object(self):
        return User.get_by(username=self.get_current_user())
    def is_argument_present(self, name):
        return not (self.request.arguments.get(name, None) == None)
    def render(self, template_name, **kwargs):
        error = str(self.get_secure_cookie("errmsg"))
        status = str(self.get_secure_cookie("statmsg"))
        self.clear_errmsg()
        self.clear_statmsg()
        RequestHandler.render(self,
            template_name,
            errmsg=error,
            statmsg=status,
            **kwargs)
    def clear_errmsg(self):
        self.clear_cookie("errmsg")
    def send_errmsg(self, errmsg):
        self.set_secure_cookie("errmsg", errmsg)
    def clear_statmsg(self):
        self.clear_cookie("statmsg")
    def send_statmsg(self, statmsg):
        self.set_secure_cookie("statmsg", statmsg)
            
class MainHandler(BaseHandler):
    def get(self):
        self.render('static/templates/base.html',
            title="Main")

class ListHandler(BaseHandler):
    def get(self):
        #TODO: put these in periodic handler
        update_free_mem()
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
            guest = create_guest(Host.query.all()[0],
                self.get_argument("profile"),
                self.get_argument("virt_name"),
                self.get_argument("expire_days"),
                self.get_argument("purpose"),
                self.get_user_object(),
                COBBLER_HOST)
            self.send_statmsg("Successfully checked out guest '%s' on %s." % (guest.virt_name, guest.host.hostname))
            self.redirect("/reservations")
        except:
            self.send_errmsg("Checkout failed:\n%s" % traceback.format_exc())
            self.redirect("/checkout")

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
                self.redirect("/register")
                return
            if (User.get_by(username=self.get_argument("username"))):
                self.send_errmsg("User '%s' exists." % self.get_argument("username"))
                self.redirect("/register")
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
            self.redirect("/register")
                
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
                self.redirect("/profile")
                return
            user = User.get_by(username=self.current_user)
            user.password = self.get_argument("password")
            user.email = self.get_argument("email")
            session.commit()
            self.send_statmsg("Successfully edited profile.")
            self.redirect("/profile")
        except:
            self.send_errmsg("Profile change failed:\n%s" % traceback.format_exc())
            self.redirect("/profile")
                
class ReservationsHandler(BaseHandler):
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
                self.set_secure_cookie("username", user.username)
                self.send_statmsg("Successfully logged in.")
                self.redirect("/")
            else:
                self.send_errmsg("Username or password incorrect")
                self.redirect("/login")
        except:
            self.send_errmsg("Username or password incorrect")
            self.redirect("/login")

class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie("username")
        self.send_statmsg("Successfully logged out.")
        self.redirect("/")

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
    "login_url": "/login",
    "cookie_secret": "984fewh43fwaaLIUEF/=EFE9isvjkrvsdsnvakeuf3"
}
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/list", ListHandler),
    (r"/checkout", CheckoutHandler),
    (r"/register", RegisterHandler),
    (r"/reservations", ReservationsHandler),
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler),
    (r"/profile", ProfileHandler)],
    **settings)
    
if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(LISTEN_PORT)
    add_hosts(CONFIG_LOC)
    tornado.ioloop.IOLoop.instance().start()
