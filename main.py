#!/usr/bin/python
import tornado.httpserver
import tornado.ioloop
import tornado.web
import os

from fogmachine.model import *
from tornado.web import RequestHandler

class MainHandler(RequestHandler):
    def get(self):
        self.render('static/templates/base.html',
            title="Main")

class ListHandler(RequestHandler):
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

class CheckoutHandler(RequestHandler):
    def get(self):
        self.render("static/templates/checkout.html",
            title="Checkout Guests")

settings = {
    "static_path": os.path.join(os.path.dirname(__file__), "static"),
}
application = tornado.web.Application([
    (r"/", MainHandler),
    (r"/list", ListHandler),
    (r"/checkout", CheckoutHandler)],
    **settings)
    
if __name__ == "__main__":
    http_server = tornado.httpserver.HTTPServer(application)
    http_server.listen(8888)
    tornado.ioloop.IOLoop.instance().start()
