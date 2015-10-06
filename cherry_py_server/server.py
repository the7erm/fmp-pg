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

from fobjs.misc import _listeners, get_words_from_string

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

vote_data = {}
skip_countdown = {}
job_data = {}

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
        GObject.idle_add(playlist.force_broadcast_time)
        return

    def opened(self):
        return json.dumps({
            "CONNECTED": "OK", 
            "time": "%s" % utcnow().isoformat() 
        })

    def closed(self, code, reason="A client left the room without a proper explanation."):
        return

cherrypy.config.update({
    'server.socket_port': 5050,
    'server.socket_host': '0.0.0.0',
    '/ws': {
        'tools.websocket.on': True,
        'tools.websocket.handler_cls': ChatWebSocketHandler
    }
})

def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, unicode)):
        value = value.lower()
        if value in ('t','true','1','on'):
            return True
        if not value or value in('f', '0', 'false', 'off', 'null', 
                                 'undefined'):
            return False
    return bool(value)

class FmpServer(object):
    @cherrypy.expose
    def index(self):
        print "cherrypy.request.headers:", cherrypy.request.headers
        print "cherrypy.request:", cherrypy.request.remote
        return open('templates/index.html', 'r').read() % {
            'host': cherrypy.request.headers['Host'],
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
        sql = """SELECT uid, uname, admin, listening, cue_netcasts
                 FROM users
                 ORDER BY listening DESC, admin DESC, uname"""
        return json_dumps(get_results_assoc_dict(sql))

    @cherrypy.expose
    def set_listening(self, *args, **kwargs):
        return self.set_user_bool_column('listening')

    @cherrypy.expose
    def set_cue_netcasts(self, *args, **kwargs):
        return self.set_user_bool_column('cue_netcasts')

    @cherrypy.expose
    def set_admin(self, *args, **kwargs):
        return self.set_user_bool_column('admin')

    def set_user_bool_column(self, col):
        uid = cherrypy.request.params.get('uid')
        uid = int(uid)
        value = cherrypy.request.params.get(col)
        value = to_bool(value)
        whitelist = ('listening', 'cue_netcasts', 'admin')
        if col not in whitelist:
            return self.listeners()
        spec = {
            'uid': cherrypy.request.params.get('uid')
        }
        spec[col] = value

        sql = """UPDATE users 
                 SET {col} = %({col})s
                 WHERE uid = %(uid)s""".format(col=col)

        query(sql, spec)
        cherrypy.log(sql % spec)
        GObject.idle_add(playlist.reload_current)
        return self.listeners()


    @cherrypy.expose
    def vote_to_skip(self, watch_id=None, uid=None, vote=None,  
                     *args,**kwargs):

        vote = to_bool(vote)
        if watch_id is None:
            watch_id = current_watch_id()

        watch_id = int(watch_id)
        if uid is not None:
            uid = int(uid)

        if watch_id not in vote_data:
            vote_data[watch_id] = {}

        vote_data[watch_id][uid] = vote

        listeners = _listeners()
        len_listeners = len(listeners)
        
        print "len_listeners:", len_listeners
        print "skip_countdown.get(watch_id):", skip_countdown.get(watch_id)
        voted_to_skip_count = remove_old_votes(watch_id)

        if voted_to_skip_count >= (len_listeners * 0.5) and \
           not skip_countdown.get(watch_id):
            skip_countdown[watch_id] = time() + len_listeners
            if len_listeners < 5:
                skip_countdown[watch_id] = time() + 5
            elif len_listeners > 10:
                skip_countdown[watch_id] = time() + 10
                
        elif skip_countdown.get(watch_id) and (voted_to_skip_count == 0 or
                                          voted_to_skip_count < (len_listeners * 0.5)):
            del skip_countdown[watch_id]
        json_broadcast({'vote_data': vote_data, 
                        'voted_to_skip_count': voted_to_skip_count})

        playlist.files[playlist.index].vote_data = vote_data[watch_id]
        print "*"* 20
        print skip_countdown.get(watch_id)

        broadcast_countdown()
        return json_dumps(vote_data)

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
        
        return json_dumps(json_response)

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

    @cherrypy.expose
    def cue(self, *args, **kwargs):
        params = cherrypy.request.params
        params['reason'] = 'FROM Search'
        if not params.get('uid'):
            params['uid'] = _listeners()[0]['uid']

        if params.get('cued'):
            sql = """INSERT INTO preload (uid, fid, reason)
                     VALUES(%(uid)s, %(fid)s, %(reason)s)"""
        else:
            sql = """DELETE FROM preload WHERE fid = %(fid)s"""
        try:
            query(sql, params)
            result = {"RESULT": "OK"}
        except Exception, e:
            query("COMMIT;")
            result = {"RESULT": "ERROR",}
        print "query:", pg_cur.mogrify(sql, params)
        print result
        print params
        return json_dumps(result)

    @cherrypy.expose
    def artist_letters(self, *args, **kwargs):
        cherrypy.log(("+"*20)+" artists letters "+("+"*20))
        sql = """SELECT DISTINCT lower(substr(artist, 1, 1)) AS letter 
                 FROM artists a, files f, file_artists fa 
                 WHERE fa.aid = a.aid AND f.fid = fa.fid ORDER BY letter"""

        letters = get_results_assoc_dict(sql)
        letters = [v['letter'] for v in letters]
        return json_dumps(letters)

    @cherrypy.expose
    def artists(self, *args, **kwargs):
        params = cherrypy.request.params
        sql = """SELECT DISTINCT lower(artist) AS artist
                 FROM artists
                 WHERE artist ILIKE %(l)s
                 ORDER BY artist"""

        spec = {
            'l': params.get('l', '')+"%"
        }
        if spec['l'] == '_%':
            spec['l'] = '\_%'
        if spec['l'] == '%%':
            spec['l'] = '\%%'

        artists = get_results_assoc_dict(sql, spec)
        return json_dumps([v['artist'].title()
                                      .replace("'S","'s")
                                      .replace("_S","_s")
                                      .replace(" Of ", " of ")
                                      .replace("Of ", "of ")
                                      .replace(" The ", " the ")
                                      .replace(" And ", " and ")
                                      .replace(" Vs ", " vs ")
                                      .replace(" Vs. ", " vs. ")
                                      .replace(" A ", " a ")
                                      .replace(" You ", " you ")
                                      .replace(" To ", " to ")
                                      .replace(" With ", " with ")
                                      for v in artists])



    @cherrypy.expose
    def search(self, *args, **kwargs):
        params = cherrypy.request.params
        cherrypy.log(("+"*20)+" SEARCH "+("+"*20))
        cherrypy.log("search: kwargs:%s" % ( kwargs,))
        start = int(params.get("s", 0))
        limit = int(params.get("l", 10))
        only_cued = params.get('oc', False)
        owner = params.get("owner",'')
        try:
            uid = int(params.get('uid', 0))
        except:
            uid = 0

        only_cued = to_bool(only_cued)

        q = params.get("q", '').strip()
        if not q and not only_cued:
            response = {
                "RESULT": "OK",
                "results": [],
                "total": 0
            }
            return json_dumps(response)
        

        query_offset = "LIMIT %d OFFSET %d" % (limit, start)
        query_args = {}
        query_spec = {
          "SELECT": ["""DISTINCT f.fid, 
                        string_agg(DISTINCT a.artist, ',') AS artists,
                        string_agg(DISTINCT fl.basename, ',') AS basenames, 
                        title, sha512, p.fid AS cued, f.fid AS id, 
                        'f' AS id_type"""],
          "FROM": ["""files f LEFT JOIN preload p ON p.fid = f.fid
                              LEFT JOIN file_artists fa ON fa.fid = f.fid
                              LEFT JOIN artists a ON a.aid = fa.aid,
                      file_locations fl"""],
          "COUNT_FROM": ["files f, file_locations fl"],
          "ORDER_BY": [],
          "WHERE": ["fl.fid = f.fid"],
          "WHERERATINGSCORE": [],
          "GROUP_BY": ["f.fid, f.title, f.sha512, p.fid, id, id_type"]
        }

        query_base = """SELECT {SELECT}
                        FROM {FROM}
                        WHERE {WHERE}
                        GROUP BY {GROUP_BY}
                        ORDER BY {ORDER_BY}
                        {query_offset}"""

        query_base_count = """SELECT count(DISTINCT f.fid) AS total
                              FROM {COUNT_FROM}
                              WHERE {WHERE}"""
        

        if uid:
            query_args['uid'] = uid
            query_spec["SELECT"].append("usi.uid, usi.rating, usi.fid AS usi_fid, u.uname")
            query_spec["FROM"].append("user_song_info usi, users u")
            query_spec["WHERE"].append("usi.fid = f.fid AND "
                                       "usi.uid = %(uid)s AND "
                                       "u.uid = usi.uid")
            query_spec["GROUP_BY"].append('usi.uid, usi.rating, usi_fid, '
                                          'u.uname')
            query_spec['COUNT_FROM'].append("user_song_info usi, users u")

        if owner:
            query_args['owner'] = owner
            query_spec["FROM"].append("folders fld, folder_owners fo")
            query_spec['COUNT_FROM'].append("folders fld, folder_owners fo")
            query_spec["WHERE"].append("""fo.uid = %(owner)s AND 
                                          fld.folder_id = fo.folder_id AND
                                          fl.folder_id = fld.folder_id AND
                                          fl.fid = f.fid""")


        if q is not None:
            q = q.strip()
            q += " "
            words = get_words_from_string(q)
            q += " ".join(words)
            q = q.strip()
        if q:
            query_spec["SELECT"].append("ts_rank(tsv, query) AS rank")
            count_from = """keywords kw,
                            plainto_tsquery('english', %(q)s) query"""
            query_spec["FROM"].append(count_from)
            query_spec["COUNT_FROM"].append(count_from)
            query_spec["WHERE"].append("kw.fid = f.fid AND tsv @@ query")
            query_spec['GROUP_BY'].append("rank")
            query_args['q'] = q
            query_spec['ORDER_BY'].append("rank DESC")

        if only_cued:
            query_spec['SELECT'].append("CASE WHEN p.reason = 'FROM Search' "                         "THEN 0 ELSE 1 END AS p_reason, "
                                         "p.reason, plid")
            query_spec['ORDER_BY'].append("""p_reason, plid""")
            query_spec['GROUP_BY'].append("p.reason, plid")


        if only_cued:
            query_spec['WHERE'].append("p.fid = f.fid")
            query_spec['COUNT_FROM'].append("preload p")

        query_spec['ORDER_BY'].append("artists, title")

        search_query = query_base.format(
            SELECT=",".join(query_spec['SELECT']),
            FROM=",".join(query_spec['FROM']),
            WHERE=" AND ".join(query_spec['WHERE']),
            ORDER_BY=",".join(query_spec['ORDER_BY']),
            GROUP_BY=",".join(query_spec['GROUP_BY']),
            query_offset=query_offset
        )

        search_query = search_query.format(
            WHERERATINGSCORE=" OR ".join(query_spec['WHERERATINGSCORE']))

        count_query = query_base_count.format(
            SELECT=",".join(query_spec['SELECT']),
            COUNT_FROM=",".join(query_spec['COUNT_FROM']),
            WHERE=" AND ".join(query_spec['WHERE']),
            ORDER_BY=",".join(query_spec['ORDER_BY']),
            GROUP_BY=",".join(query_spec['GROUP_BY'])
        )

        count_query = count_query.format(
            WHERERATINGSCORE=" OR ".join(query_spec['WHERERATINGSCORE']))

        if not query_spec['WHERE']:
            search_query = search_query.replace("WHERE", '')
            count_query = count_query.replace("WHERE", '')

        results = []
        try:
            print "query:", pg_cur.mogrify(search_query, query_args)
            try:
              results = get_results_assoc_dict(search_query, query_args)
            except Exception, err:
              print "ERR", err
              query("COMMIT;")
        except psycopg2.IntegrityError, err:
            query("COMMIT;")
            print "*****ERROR"
            print "(server) psycopg2.IntegrityError:",err
        except psycopg2.InternalError, err:
            query("COMMIT;")
            print "(server) psycopg2.InternalError:",err

        print "count_query:", pg_cur.mogrify(count_query, query_args)
        total = 0
        try:
          print "total query:", pg_cur.mogrify(count_query, query_args)
          total = get_assoc_dict(count_query, query_args)
        except Exception, err:
          print "ERR", err
          query("COMMIT;")
            
        response = {
            "RESULT": "OK",
            "results": results,
            "total": total
        }
        return json_dumps(response)

    def getFolderOwners(self, folder_id):
        sql = """SELECT u.uid, u.uname, fo.folder_id AS fo_folder_id, 
                        fo.uid AS owner 
                 FROM users u 
                      LEFT JOIN folder_owners fo ON 
                                fo.folder_id = %(folder_id)s AND fo.uid = u.uid
                 ORDER BY admin DESC, listening DESC, uname;"""
        return get_results_assoc_dict(sql, {'folder_id': folder_id})


    @cherrypy.expose
    def folders(self, *args, **kwargs):
        folder_id = cherrypy.request.params.get('folder_id')
        sql = """SELECT *
                 FROM folders
                 WHERE folder_id = %(folder_id)s
                 LIMIT 1"""
        spec = {'folder_id': folder_id}
        folder = get_assoc_dict(sql, spec)
        folder['owners'] = self.getFolderOwners(folder_id)

        sql = """SELECT *
                 FROM folders
                 WHERE parent_folder_id = %(folder_id)s AND 
                       folder_id != %(folder_id)s
                 ORDER BY dirname"""
        children = get_results_assoc_dict(sql, spec)
        for child in children:
            child['owners'] = self.getFolderOwners(child['folder_id'])

        folder['loaded_children'] = True
        folder['children'] = children

        while len(children) == 1:
            for child in children:
                grand_children = get_results_assoc_dict(sql, child)
                child['children'] = grand_children
                child['loaded_children'] = True
                child['owners'] = self.getFolderOwners(child['folder_id'])
            children = grand_children
        for child in children:
            child['collapsed'] = True
            child['owners'] = self.getFolderOwners(child['folder_id'])
            
        return json_dumps([folder])

    @cherrypy.expose
    def set_owner(self, *args, **kwargs):
        params = cherrypy.request.params
        owner = params.get('owner')
        owner = to_bool(owner)
        
        params['owner'] = owner
        print "SET OWNER:", params
        if not params.get('owner'):
            sql = """DELETE FROM folder_owners
                     WHERE uid = %(uid)s AND folder_id = %(folder_id)s"""
            
        else:
            sql = """INSERT INTO folder_owners (uid, folder_id)
                     VALUES(%(uid)s, %(folder_id)s)"""
        try:
            query(sql, params)
        except:
            pass
        return json_dumps({"RESULT": "OK"})

    @cherrypy.expose
    def set_owner_recursive(self, *args, **kwargs):
        params = cherrypy.request.params
        params['id'] = params.get('folder_id')
        GObject.idle_add(playlist.jobs.cue, ({
            'name': 'folder_owner_progress',
            'params': params
        }))
        return json_dumps({"RESULT": "STARTED"})

def cherry_py_worker():
    static_path = os.path.realpath(sys.path[0])
    static_img_path = os.path.join(static_path, "images")
    cherrypy.quickstart(FmpServer(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': ChatWebSocketHandler
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': os.path.join(static_img_path,
                                                      "favicon.ico")
        },
        '/static': {
            'tools.staticdir.root': static_path,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "static"
        }
    })

def remove_old_votes(watch_id):
    remove_old_votes = []
    voted_to_skip_count = 0
    if watch_id == -1:
        return

    if watch_id not in vote_data:
        return 0

    for uid, voted in vote_data[watch_id].items():
        if voted:
            voted_to_skip_count += 1

    for _watch_id, v in vote_data.items():
        if _watch_id != watch_id:
            remove_old_votes.append(_watch_id)

    for _watch_id in remove_old_votes:
        del vote_data[_watch_id]

    remove_old_votes = []

    for _watch_id, v in skip_countdown.items():
        if _watch_id != watch_id:
            remove_old_votes.append(_watch_id)

    for _watch_id in remove_old_votes:
        del skip_countdown[_watch_id]


    return voted_to_skip_count

def current_watch_id():
    watch_id = -1

    try:
        fid = playlist.files[playlist.index].fid
        if fid:
            watch_id = fid
    except:
        print "FAILED FID"
        fid = -1
        
    try:
        eid = playlist.files[playlist.index].eid
        if eid:
            watch_id = eid
    except:
        eid = -1

    cherrypy.log("watch_id:%s" % watch_id)
    return watch_id

def broadcast_countdown():
    watch_id = current_watch_id()

    # print({'fid': fid, 'eid': eid, 'watch_id': watch_id})
    voted_to_skip_count = remove_old_votes(watch_id)
    #print({'fid': fid, 'eid': eid, 'watch_id': watch_id}, 'after')

    seconds_left_to_skip = None
    print "skip_countdown:",skip_countdown, skip_countdown.get(watch_id)
    if skip_countdown.get(watch_id) is not None:
        if playlist.player.state_string != "PLAYING":
            skip_countdown[watch_id] = time() + 5
        seconds_left_to_skip = math.ceil(skip_countdown[watch_id] - time())
        print "seconds_left_to_skip:", seconds_left_to_skip
        if seconds_left_to_skip < 0:
            print "*** DE INC ***"
            playlist.files[playlist.index].vote_data = vote_data[watch_id]
            GObject.idle_add(playlist.majority_next, ())
            seconds_left_to_skip = 0
            del skip_countdown[watch_id]

    json_broadcast({
        'skip_countdown': skip_countdown,
        'seconds_left_to_skip': seconds_left_to_skip
    })

def json_headers():
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'

def json_dumps(obj):
    json_headers()
    return json.dumps(obj)

def JsonTextMessage(data):
    return TextMessage(json.dumps(data))

def broadcast_jobs():
    json_broadcast({'jobs': job_data})

def json_broadcast(data):
    cherrypy.engine.publish('websocket-broadcast', JsonTextMessage(data))

def broadcast(data):
    if not data.get('time-status'):
        print "broadcast:", data
    json_broadcast(data)
    json_broadcast({'vote_data':vote_data})
    broadcast_countdown()






