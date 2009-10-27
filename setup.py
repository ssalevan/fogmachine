#!/usr/bin/python

from distutils.core import setup

VERSION = "0.1"
SHORT_DESC = "WebUI-based cloud creation tool"
LONG_DESC = """
Fogmachine allows users to deploy virtual machines across a wide array of host
machines, as specified in a configuration file.  It uses Cobbler and Facebook's
Tornado framework to accomplish the heavy lifting, and it's got a swanky WebUI
for your viewing pleasure.
"""

if __name__ == "__main__":
    # main Fogmachine directory
    sharepath     = "/usr/share/fogmachine"
    logpath       = sharepath + "/logs"
    
    # webUI stuff
    staticpath    = sharepath + "/static"
    # webUI subdirs
    appletspath   = staticpath + "/applets"
    csspath       = staticpath + "/css"
    imagespath    = staticpath + "/images"
    jspath        = staticpath + "/js"
    templatespath = staticpath + "/templates"
    
    # where daemonizer stuff lands
    initpath      = "/etc/init.d"
    confpath      = "/etc/fogmachine"
    
    setup(
        name = "fogmachine",
        version = VERSION,
        author = "Steve Salevan",
        author_email = "ssalevan@redhat.com",
        license = "GPL",
        packages = [
            "fogmachine"
        ],
        scripts = [
            "scripts/fogmachined"
        ],
        data_files = [
            # daemonizer script
            (initpath, [ 'config/fogmachined' ]),
            
            # main fogmachine files
            (sharepath, [ 'main.py' ]),
            (sharepath, [ 'README' ]),
            
            # config files
            (confpath, [ 'cfg_tmpl/fogmachine.conf' ]),
            (confpath, [ 'cfg_tmpl/logging.conf' ]),
            (confpath, [ 'cfg_tmpl/virthosts.conf' ]),
            
            # webUI files
            (staticpath,    [ 'static/favicon.ico' ]),
            (appletspath,   [ 'static/applets/VncViewer.jar' ]),
            (csspath,       [ 'static/css/fogmachine.css' ]),
            (imagespath,    [ 'static/images/fogmachine.jpg' ]),
            (jspath,        [ 'static/js/vncwindow.js' ]),
            (templatespath, [ 'static/templates/admin.html' ]),
            (templatespath, [ 'static/templates/base.html' ]),
            (templatespath, [ 'static/templates/checkout.html' ]),
            (templatespath, [ 'static/templates/list.html' ]),
            (templatespath, [ 'static/templates/login.html' ]),
            (templatespath, [ 'static/templates/profile.html' ]),
            (templatespath, [ 'static/templates/register.html' ]),
            (templatespath, [ 'static/templates/reservations.html' ]),
            
            # create the log directory, guhhhh
            (logpath, [])
        ],
        description=SHORT_DESC,
        long_description=LONG_DESC  
    )
