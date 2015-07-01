import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango,\
                          GLib, Gio
GObject.threads_init()

import cherrypy

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage, BinaryMessage
import json

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

class ChatWebSocketHandler(WebSocket):
    def received_message(self, m):
        cherrypy.engine.publish('websocket-broadcast', m)

    def closed(self, code, reason="A client left the room without a proper explanation."):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

cherrypy.config.update({
    'server.socket_port': 5050,
    '/ws': {
        'tools.websocket.on': True,
        'tools.websocket.handler_cls': ChatWebSocketHandler
    }
})

class FmpServer(object):
    @cherrypy.expose
    def index(self):
        print "cherrypy.request.local:", cherrypy.request.local
        return open('templates/index.html', 'r').read() % {
            'host': 'localhost', 
            'port': 5050, 
            'scheme': 'ws'
        }

    @cherrypy.expose
    def next(self):
        playlist.next()
        return "Next"

    @cherrypy.expose
    def pause(self):
        Gdk.threads_leave()
        print "WEB PAUSE", "*"*100
        playlist.player.state_string = 'TOGGLE'
        print "/WEB PAUSE","*"*100
        return "pause"

    @cherrypy.expose
    def prev(self):
        playlist.prev()
        wait()
        return "prev"

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

def cherry_py_worker():
    cherrypy.quickstart(FmpServer(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': ChatWebSocketHandler
            }
    })

def broadcast(data):
    wait()
    cherrypy.engine.publish('websocket-broadcast', 
            TextMessage(json.dumps(data)))


