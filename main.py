#!/usr/bin/python
import os
import traceback
import xmlrpclib
import tornado.httpserver
import tornado.ioloop
import tornado.web

from fogmachine.model import *
from fogmachine.config_reader import add_hosts
from tornado.web import RequestHandler

#variables that you might want to change (location of cobbler host, vhost config file)
COBBLER_HOST = "sat-blade-8.idm.lab.bos.redhat.com"
CONFIG_LOC = "./virthosts.conf"
LISTEN_PORT = 8888

class BaseHandler(RequestHandler):
    def get_current_user(self):
        return self.get_secure_cookie("username")
    def render(self, template_name, errmsg="", **kwargs):
        RequestHandler.render(self,
            template_name,
            errmsg=errmsg,
            **kwargs)
            
class MainHandler(BaseHandler):
    def get(self):
        self.render('static/templates/base.html',
            title="Main")

class ListHandler(BaseHandler):
    def get(self):
        hosts = Host.query.order_by('cobbler_name').all()
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
        hosts = Host.query.order_by('cobbler_name').all()
        context = {
            'title': "Checkout Guests",
            'hosts': hosts
        }
        self.render("static/templates/checkout.html",
            **context)

class RegisterHandler(BaseHandler):
    def get(self):
        if self.current_user:
            self.redirect("/")
            return
        self.render("static/templates/register.html",
            title="User Registration")
    def post(self):
        try:
            if not (self.get_argument("password") == self.get_argument("confirm_password")):
                self.render("static/templates/register.html",
                    title="User Registration",
                    errmsg="Passwords do not match.")
                return
            newuser = User(username=self.get_argument("username"),
                password=self.get_argument("password"),
                email=self.get_argument("email"))
            session.commit()
            self.set_secure_cookie("username", newuser.username)
            self.redirect("/")
        except:
            self.render("static/templates/register.html",
                title="User Registration",
                errmsg="Registration failed:\n%s" % traceback.format_exc())

class LoginHandler(BaseHandler):
    def get(self):
        self.render("static/templates/login.html",
            title="Login")
    def post(self):
        try:
            user = User.get_by(username=self.get_argument("username"))
            if user.password == self.get_argument("password"):
                self.set_secure_cookie("username", user.username)
                self.redirect("/")
            else:
                self.render("static/templates/login.html",
                    title="Login",
                    errmsg="Username or password incorrect.")
        except:
            self.render("static/templates/login.html",
                title="Login",
                errmsg="Username or password incorrect.")

class LogoutHandler(BaseHandler):
    def get(self):
        self.set_secure_cookie("username", "")
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
    (r"/login", LoginHandler),
    (r"/logout", LogoutHandler)],
    **settings)
    
if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(LISTEN_PORT)
    add_hosts(CONFIG_LOC)
    tornado.ioloop.IOLoop.instance().start()
