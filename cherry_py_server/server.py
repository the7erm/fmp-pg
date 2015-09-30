#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# server.py -- cherrypy server for fmp
#    Copyright (C) 2015 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango,\
                          GLib, Gio
GObject.threads_init()

import cherrypy
from utils import utcnow

from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage, BinaryMessage
import json

from time import time
import os
import sys
import math

try:
    from db.db import *
except:
    sys.path.append("../")
    from db.db import *

from fobjs.misc import _listeners

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

vote_data = {}
skip_countdown = {}

class ChatWebSocketHandler(WebSocket):
    def received_message(self, m):
        print "received_message:", m
        broadcast({
            "CONNECTED": "OK", 
            "time": "%s" % utcnow().isoformat() 
        })
        broadcast({
            "player-playing": playlist.files[playlist.index].json()
        })
        playlist.force_broadcast_time()

    
        return
        # cherrypy.engine.publish('websocket-broadcast', m)

    def opened(self):
        return json.dumps({
            "CONNECTED": "OK", 
            "time": "%s" % utcnow().isoformat() 
        })

    def closed(self, code, reason="A client left the room without a proper explanation."):
        return
        # cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

cherrypy.config.update({
    'server.socket_port': 5050,
    'server.socket_host': '0.0.0.0',
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
    def rate(self, *args, **kwargs):
        spec = {
            'uid': cherrypy.request.params.get('uid'),
            'fid': cherrypy.request.params.get('fid'),
            'rating': cherrypy.request.params.get('rating')
        }
        print "***************** CALLED RATE ********"
        sql = """UPDATE user_song_info usi
                 SET rating = %(rating)s
                 WHERE fid = %(fid)s AND uid = %(uid)s"""
        print sql % spec
        query(sql, spec)
        sql = """UPDATE user_song_info usi
                 SET true_score = (
                        (rating * 2 * 10) + 
                        (score * 10)
                     ) / 2.0
                 WHERE fid = %(fid)s AND uid = %(uid)s"""
        query(sql, spec)
        playlist.reload_current()
        return "rate"

    @cherrypy.expose
    def seek(self, seek):
        GObject.idle_add(self.do_seek,(seek))
        return "Seek"

    def do_seek(self, value):
        print("SEEK:", value)
        playlist.player.position = value

    @cherrypy.expose
    def next(self):
        GObject.idle_add(playlist.next)
        return "Next"

    @cherrypy.expose
    def pause(self):
        print "WEB PAUSE", "*"*100
        GObject.idle_add(playlist.player.pause)
        print "/WEB PAUSE","*"*100
        return "pause"

    @cherrypy.expose
    def prev(self):
        GObject.idle_add(playlist.prev)
        return "prev"

    @cherrypy.expose
    def listeners(self):
        sql = """SELECT uid, uname, admin, listening
                 FROM users
                 ORDER BY listening DESC, admin DESC, uname"""

        return json.dumps(get_results_assoc_dict(sql))


    @cherrypy.expose
    def set_listening(self, *args, **kwargs):
        spec = {
            'uid': cherrypy.request.params.get('uid'),
            'listening': cherrypy.request.params.get('listening')
        }
        sql = """UPDATE users 
                 SET listening = %(listening)s
                 WHERE uid = %(uid)s"""

        query(sql, spec)
        cherrypy.log(sql % spec)
        playlist.reload_current()
        return self.listeners()

    @cherrypy.expose
    def vote_to_skip(self, fid=None, uid=None, vote=None, *args,**kwargs):
        if fid is not None:
            fid = int(fid)
        if uid is not None:
            uid = int(uid)
        if fid not in vote_data:
            vote_data[fid] = {}

        if not vote or vote == 'false':
            vote = False
        else:
            vote = True

        vote_data[fid][uid] = vote

        remove_old_votes = []
        voted_to_skip_count = 0

        for uid, voted in vote_data[fid].items():
            if voted:
                voted_to_skip_count += 1

        for _fid, v in vote_data.items():
            if _fid != fid:
                remove_old_votes.append(_fid)

        for _fid in remove_old_votes:
            del vote_data[_fid]

        remove_old_votes = []

        for _fid, v in skip_countdown.items():
            if _fid != fid:
                remove_old_votes.append(_fid)

        for _fid in remove_old_votes:
            del skip_countdown[_fid]

        listeners = _listeners()
        if voted_to_skip_count >= (len(listeners) * 0.5) and \
           not skip_countdown.get(fid):
            skip_countdown[fid] = time() + 5
        elif skip_countdown.get(fid):
            del skip_countdown[fid]

        cherrypy.engine.publish('websocket-broadcast', TextMessage(
            json.dumps({'vote_data': vote_data, 'voted_to_skip_count': voted_to_skip_count})))

        playlist.files[playlist.index].vote_data = vote_data[fid]
        print "*"* 20
        print skip_countdown.get(fid)
        
        return json.dumps(vote_data)

    @cherrypy.expose
    def ws(self):
        cherrypy.log("Handler created: %s" % repr(cherrypy.request.ws_handler))

    @cherrypy.expose
    # @cherrypy.tools.json_out(content_type='application/json')
    def satellite(self):
        response = cherrypy.response
        response.headers['Content-Type'] = 'application/json'
        start = time()
        json_response = {
            'preload': preload.json(),
            'utcnow:': utcnow().isoformat(),
            'playlist': playlist.json()
        }
        gen_time = time() - start
        cherrypy.log("gen_time: %s", str(gen_time))
        json_response['gen_time'] = "%s" % gen_time
        
        return json.dumps(json_response)

    @cherrypy.expose
    def download(self, fid=None, eid=None):
        if fid is not None:
            sql = """SELECT dirname, basename
                     FROM file_locations
                     WHERE fid = %(fid)s"""
            files = get_results_assoc_dict(sql, {"fid": fid})
            for f in files:
                filename = os.path.join(f['dirname'], f['basename'])
                if os.path.exists(filename):
                    return cherrypy.lib.static.serve_file(
                        filename, "application/x-download",
                        "attachment", f['basename'])

        if eid is not None:
            sql = """SELECT episode_url, local_file
                     FROM netcast_episodes
                     WHERE eid = %(eid)s"""
            files = get_results_assoc_dict(sql, {"eid": eid})
            for f in files:
                filename = f['local_file']
                if os.path.exists(filename):
                    return cherrypy.lib.static.serve_file(
                        filename, "application/x-download",
                        "attachment", os.path.basename(filename))

        return cherrypy.NotFound()


def cherry_py_worker():
    static_path = os.path.realpath(sys.path[0])
    cherrypy.quickstart(FmpServer(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': ChatWebSocketHandler
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': "/home/erm/fmp-pg/static/favicon.ico"
        },
        '/static/fmp-logo.svg': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': "/home/erm/fmp-pg/static/fmp-logo.svg"
        },
        '/static': {
            'tools.staticdir.root': static_path,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "static"
        }
    })

def broadcast(data):
    if not data.get('time-status'):
        print "broadcast:", data
    cherrypy.engine.publish('websocket-broadcast', 
            TextMessage(json.dumps(data)))
    cherrypy.engine.publish('websocket-broadcast', TextMessage(
        json.dumps({'vote_data': vote_data})))
    try:
        fid = playlist.files[playlist.index].fid
    except:
        fid = -1

    cherrypy.engine.publish('websocket-broadcast', TextMessage(
        json.dumps({'fid': fid})))
    seconds_left_to_skip = None
    print "skip_countdown:",skip_countdown, skip_countdown.get(fid)
    if skip_countdown.get(fid) is not None:
        seconds_left_to_skip = math.ceil(skip_countdown[fid] - time())
        print "seconds_left_to_skip:", seconds_left_to_skip
        if seconds_left_to_skip < 0:
            print "*** DE INC ***"
            playlist.files[playlist.index].vote_data = vote_data[fid]
            GObject.idle_add(playlist.majority_next, ())
            seconds_left_to_skip = 0
            del skip_countdown[fid]

    cherrypy.engine.publish('websocket-broadcast', TextMessage(
        json.dumps({
            'skip_countdown': skip_countdown,
            'seconds_left_to_skip': seconds_left_to_skip
        })))




