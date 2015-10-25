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
import shutil
tmpdir = os.path.expanduser("~/.fmp/tmp")

try:
    from db.db import *
except:
    sys.path.append("../")
    from db.db import *

from fobjs.misc import _listeners, get_words_from_string, to_bool,\
                       listener_watcher, leave_threads, jsonize

from fobjs.user_file_info_class import UserFileInfo
from fobjs.local_fobj_class import Local_FObj

convert_files = []

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

def convert_to_int(value, default=None):

    try:
        value = int(value)
    except:
        value = default
    return value

def convert_to_float(value, default=None):

    try:
        value = float(value)
    except:
        value = default
    return value

class FmpServer(object):
    def __init__(self, *args, **kwargs):
        super(FmpServer, self).__init__(*args, **kwargs)
        listener_watcher.connect('listeners-changed', self.on_listeners_change)

    def on_listeners_change(self, *args, **kwargs):
        leave_threads()
        json_broadcast({"listeners": listener_watcher.listeners})

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
        GObject.idle_add(playlist.reload_current)
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
        return json_dumps(listener_watcher.users)

    @cherrypy.expose
    def set_listening(self, *args, **kwargs):
        self.history()
        return self.set_user_bool_column('listening')

    @cherrypy.expose
    def set_listening_on_satellite(self, *args, **kwargs):
        return self.set_user_bool_column('listening_on_satellite')

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
        whitelist = ('listening', 'cue_netcasts', 'admin',
                     'listening_on_satellite')
        if col not in whitelist:
            return self.listeners()
        listener_watcher.set_user_bool_column(uid, col, value)
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

        listeners = listener_watcher.listeners
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
            if len_listeners == 1 or len_listeners == voted_to_skip_count:
                skip_countdown[watch_id] = time()

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

    def get_uids(self):
        uid_param = cherrypy.request.params.get('uid')
        uids = []
        for uid in uid_param.split(","):
            try:
                uid = int(uid)
                uid = str(uid)
            except:
                continue
            uids.append(uid)
        return uids

    def preload_query(self, sql, OFFSET_LIMIT, UID_IN_AND, ignore_fids,
                      results, limit, uids):
        AND_FID_NOT_IN = ""
        if ignore_fids:
            AND_FID_NOT_IN = " AND fid NOT IN (%s)" % ",".join(
                str(x) for x in ignore_fids)

        sql = sql.format(LIMIT=OFFSET_LIMIT, UID_IN_AND=UID_IN_AND,
                         AND_FID_NOT_IN=AND_FID_NOT_IN)
        print "SQL:", mogrify(sql)
        res = get_results_assoc_dict(sql)
        print "MADE IT PAST SQL"
        for r in res:
            ignore_fids.append(r['fid'])
            print "RES:", r
            r['limit_uids'] = uids
            lf = Local_FObj(**r)
            print "MADE IT PAST LF"
            if not lf.basename.lower().endswith(".mp3"):
                filename = converter.get_converted_filename(
                        lf.fid, lf.filename)
                if not os.path.exists(filename):
                    print "MISSING:",filename
                    converter.add_file(lf.fid, lf.filename)
                    sql = """DELETE FROM preload WHERE fid = %(fid)s"""
                    query(sql, r)
                    sql = """DELETE FROM preload_cache WHERE fid = %(fid)s"""
                    query(sql, r)
                    continue
            print "APPENDING:", lf.json()
            results.append(lf.json())

            if limit is not None and len(results) > limit:
                break

    @cherrypy.expose
    def preload(self, *args, **kwargs):
        uids = self.get_uids()
        limit = cherrypy.request.params.get("limit")
        try:
            limit = int(limit)
        except:
            limit = None

        if limit is None:
            limit = 1

        OFFSET_LIMIT = ""

        if limit is not None:
            OFFSET_LIMIT = "OFFSET 0 LIMIT %d" % limit

        UID_IN_AND = ""
        if uids:
            UID_IN_AND = "p.uid IN ({UIDS}) AND ".format(UIDS=",".join(uids))

        queries = [
            """SELECT p.*, u.uname
               FROM preload p, users u
               WHERE reason ILIKE '%%FROM Search%%' AND
                     {UID_IN_AND} u.uid = p.uid
                     {AND_FID_NOT_IN}
               ORDER BY plid
               {LIMIT}""",
            """SELECT p.*, u.uname
               FROM preload_cache p, users u
               WHERE reason ILIKE '%%FROM Search%%' AND
                     {UID_IN_AND} u.uid = p.uid
                     {AND_FID_NOT_IN}
               ORDER BY pcid
               {LIMIT}""",
            """SELECT p.*, u.uname
               FROM preload p, users u
               WHERE reason NOT ILIKE '%%FROM Search%%' AND
                     {UID_IN_AND} u.uid = p.uid
                     {AND_FID_NOT_IN}
               ORDER BY plid
               {LIMIT}""",
            """SELECT p.*, u.uname
               FROM preload_cache p, users u
               WHERE reason NOT ILIKE '%%FROM Search%%' AND
                     {UID_IN_AND} u.uid = p.uid
                     {AND_FID_NOT_IN}
               ORDER BY pcid
               {LIMIT}""",
        ]

        results = []
        ignore_fids = []
        for sql in queries:
            self.preload_query(sql, OFFSET_LIMIT, UID_IN_AND,
                               ignore_fids, results, limit, uids)

        return json_dumps({
            "uids": uids,
            "results": results
        })

    @cherrypy.expose
    def history(self, *args, **kwargs):
        uids = self.get_uids()
        fid_param = cherrypy.request.params.get('fid')

        UID_IN = "uh.uid IN ({UIDS}) AND".format(UIDS=",".join(uids))

        AND_FID = 'uh.fid IS NOT NULL'
        fid = convert_to_int(fid_param, None)

        if fid:
            AND_FID = "uh.fid = %(fid)s"

        spec = {
            'fid': fid
        }

        limit = 1
        sql = """SELECT uh.*
                 FROM user_history uh
                 WHERE {UID_IN} uh.time_played IS NOT NULL AND
                       {AND_FID}
                 ORDER BY time_played DESC
                 LIMIT 10""".format(
                    UID_IN=UID_IN,
                    AND_FID=AND_FID
                )

        results = []
        print mogrify(sql, spec)
        res = get_results_assoc_dict(sql, spec)
        for r in res:
            print "R:",r
            r['limit_uids'] = uids
            lf = Local_FObj(**r)
            results.append(lf.json())
            if not lf.filename.lower().endswith(".mp3"):
                converter.add_file(lf.fid, lf.filename)
        results.reverse()
        return json_dumps(results)


    @cherrypy.expose
    def mark_as_played(self, uid=None, fid=None, eid=None, percent=None,
                       now=None):

        uids = self.get_uids()

        cherrypy.log("*"*100)
        cherrypy.log("mark_as_played from server")
        fid = convert_to_int(fid, 0)
        eid = convert_to_int(eid, 0)
        # uid = convert_to_int(uid, 0)

        percent = convert_to_float(percent, 0.0)

        if fid:
            spec = {
                'fid': fid
            }
            sql = """DELETE FROM preload
                     WHERE fid = %(fid)s AND uid IN ({UIDS})""".format(
                        UIDS=",".join(uids))
            query(sql, spec)

            sql = """DELETE FROM preload_cache
                     WHERE fid = %(fid)s AND uid IN ({UIDS})""".format(
                        UIDS=",".join(uids))
            query(sql, spec)

            sql = """SELECT *
                     FROM users u, user_song_info usi
                     WHERE usi.uid IN ({UIDS}) AND usi.fid = %(fid)s AND
                           u.uid = usi.uid
                     LIMIT 1""".format(UIDS=",".join(uids))
            print mogrify(sql, spec)
            userDbInfo = get_assoc_dict(sql, spec)
            userDbInfo['mark_as_played_from_server'] = True
            kwargs = {
                'fid': fid,
                'userDbInfo': userDbInfo,
                'mark_as_played_from_server': True
            }
            for uid in uids:
                kwargs['uid'] = int(uid)
                usi = UserFileInfo(**kwargs)
                usi.mark_as_played(percent_played=percent)
            print "LOADED USI"
            return json_dumps({"usi": usi.json()})


        return json_dumps({"RESULT": "OK"})


    @cherrypy.expose
    def genres(self, query=None, fetch_all=False):
        if query is None:
            query = ""

        query = query+"%"
        sql = """SELECT *
                 FROM genres
                 WHERE genre ILIKE %(genre)s
                 ORDER BY genre"""
        if not fetch_all:
            sql +" LIMIT 10"
        else:
            query = "%"+query

        result = get_results_assoc_dict(sql,{"genre": query})
        return json_dumps(result)

    @cherrypy.expose
    def genre_enabled(self, *args, **kwargs):
        gid = cherrypy.request.params.get('gid')
        enabled = cherrypy.request.params.get("enabled")
        enabled = to_bool(enabled)
        sql = """UPDATE genres
                 SET enabled = %(enabled)s
                 WHERE gid = %(gid)s"""
        spec = {
            'gid': gid,
            'enabled': enabled
        }
        query(sql, spec)

    @cherrypy.expose
    def set_score(self, *arg, **kwargs):
        sql = """UPDATE user_song_info
                 SET score = %(score)s,
                     true_score = %(true_score)s
                 WHERE uid = %(uid)s AND
                       fid = %(fid)s"""
        query(sql, kwargs)
        print "SET_SCORE"
        print mogrify(sql, kwargs)
        sql = """UPDATE user_song_info usi
                 SET true_score = (
                        (rating * 2 * 10) +
                        (score * 10)
                     ) / 2.0
                 WHERE fid = %(fid)s AND uid = %(uid)s"""
        query(sql, kwargs)
        GObject.idle_add(playlist.reload_current)
        print mogrify(sql, kwargs)

    @cherrypy.expose
    def add_genre(self, fid, genre):
        fid = int(fid)
        if not genre:
            return json_dumps({
                "RESULT": "Error",
                "Error": "No genre"
            })
        sql = """SELECT *
                 FROM genres
                 WHERE genre = %(genre)s
                 LIMIT 1"""

        spec = {'genre': genre}
        genreDbInfo = get_assoc_dict(sql, spec)
        if not genreDbInfo:
            sql = """INSERT INTO genres (genre)
                     VALUES (%(genre)s)
                     RETURNING *"""
            genreDbInfo = get_assoc_dict(sql, spec)


        genreDbInfo['fid'] = fid
        sql = """SELECT * FROM file_genres
                 WHERE fid = %(fid)s AND gid = %(gid)s
                 LIMIT 1"""

        present = get_assoc_dict(sql, genreDbInfo)
        if present:
            return json_dumps(present)

        sql = """INSERT INTO file_genres (fid, gid)
                 VALUES(%(fid)s, %(gid)s)
                 RETURNING *"""
        res = get_assoc_dict(sql, genreDbInfo)
        return json_dumps(res)


    @cherrypy.expose
    def remove_genre(self, fid, genre):
        fid = int(fid)
        if not genre:
            return
        sql = """SELECT *
                 FROM genres
                 WHERE genre = %(genre)s
                 LIMIT 1"""

        spec = {'genre': genre}
        genreDbInfo = get_assoc_dict(sql, spec)
        if not genreDbInfo:
            return json_dumps({"RESULT": "OK", "MSG":"Not present"})

        genreDbInfo['fid'] = fid
        sql = """DELETE FROM file_genres
                 WHERE fid = %(fid)s AND gid = %(gid)s"""

        query(sql, genreDbInfo)

        sql = """SELECT count(*) AS total
                 FROM file_genres
                 WHERE gid = %(gid)s"""

        total = get_assoc_dict(sql, genreDbInfo)

        if total['total'] == 0:
            sql = """DELETE FROM genres WHERE gid = %(gid)s"""
            query(sql, genreDbInfo)

        return json_dumps({"RESULT": "OK"})


    @cherrypy.expose
    def download(self, fid=None, eid=None):
        if fid is not None:
            sql = """SELECT dirname, basename
                     FROM file_locations
                     WHERE fid = %(fid)s"""
            files = get_results_assoc_dict(sql, {"fid": fid})
            for f in files:
                original_filename = os.path.join(f['dirname'], f['basename'])
                print "FILENAME:", original_filename
                if os.path.exists(original_filename):
                    print "EXISTS:", original_filename
                    basename = f['basename']
                    if not basename.lower().endswith(".mp3"):
                        converted_filename = converter.get_converted_filename(
                            fid, original_filename)
                        if not os.path.exists(converted_filename):
                            print "MISSING:", converted_filename
                            converter.add_file(fid, original_filename)
                            continue
                        basename += ".converted.mp3"
                    else:
                        converted_filename = original_filename
                        print "USING original_filename:", original_filename
                    # path, content_type=None, disposition=None, name=None, debug=False
                    args = {
                        "path": converted_filename,
                        "content_type": "audio/mpeg",
                        "disposition":"inline",
                        "name": basename
                    }
                    print "ARGS:", args

                    return cherrypy.lib.static.serve_file(**args)
            print "OUT OF LOOP?"

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
    def tags(self, *args, **kwargs):
        word = cherrypy.request.params.get('word')
        word = str(word)
        word = word.lower()
        queries = [
            """SELECT word
               FROM words
               WHERE word LIKE %(word)s
               ORDER BY word
               LIMIT 10""",
            # GET words that start with the string, and are 1 character
            # Longer than our search that are all letters.
            """SELECT word
               FROM words
               WHERE word LIKE %(word_)s AND word !~* '\W' AND
                     len < (length(%(word_)s) + 1) {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
            """SELECT word
               FROM words
               WHERE word LIKE %(word_)s AND word !~* '\W' AND
                     len >= (length(%(word_)s) + 1) AND
                     len < (length(%(word_)s) + 3) {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
            # Anything that starts with our word
            """SELECT word
               FROM words
               WHERE word LIKE %(word_)s AND word !~* '\W' {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
            # Anything that contains our word without punctuation.
            """SELECT word
               FROM words
               WHERE word LIKE %(_word_)s
               ORDER BY word
               LIMIT 10""",
            # Anything that contains our word with punctuation.
            """SELECT word
               FROM words
               WHERE word LIKE %(word_)s AND word ~* '\W' {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
            """SELECT word
               FROM words
               WHERE word LIKE %(_word_)s  AND word ~* '\W' {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
            # Same as above just other characters like .,-
            """SELECT word
               FROM words
               WHERE word LIKE %(word_)s AND word ~* '\W' AND
                     len < (length(%(word_)s) + 1) {AND_NOT_IN}
               ORDER BY word
               LIMIT 10""",
        ]
        results = []
        spec = {
            "word": word,
            "word_": word+"%",
            "_word_": "%"+word+"%"
        }
        for sql in queries:
            if len(results) > 10:
                break;
            words = []
            for w in results:
                if not w:
                    continue
                words.append(mogrify("%s", (w,)))

            AND_NOT_IN = ""

            if words:
                AND_NOT_IN = " AND word NOT IN (%s)" % ",".join(words)

            sql = sql.format(AND_NOT_IN=AND_NOT_IN)
            res = get_results_assoc_dict(sql, spec)
            for r in res:
                if r['word'] not in results:
                    results.append(r['word'])
                    if len(results) > 10:
                        break

        words = []
        for r in results:
            words.append({'word':word})

        return json_dumps(results)


    @cherrypy.expose
    def search(self, *args, **kwargs):
        start_time = time()
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
        if q is not None:
            q = q.strip()
            q += " "
            words = get_words_from_string(q)
            q += " ".join(words)
            q = q.strip()
        """
        if not q and not only_cued:
            response = {
                "RESULT": "OK",
                "results": [],
                "total": 0
            }
            return json_dumps(response)
        """


        query_offset = "LIMIT %d OFFSET %d" % (limit, start)
        query_args = {}
        query_spec = {
          "SELECT": ["""DISTINCT f.fid, f.artists_agg AS artists,
                        f.basename_agg AS basenames,
                        title, sha512, p.fid AS cued, f.fid AS id,
                        'f' AS id_type"""],
          "FROM": ["""files f LEFT JOIN preload p ON p.fid = f.fid"""],
          "COUNT_FROM": ["files f"],
          "ORDER_BY": [],
          "WHERE": [],
          "WHERERATINGSCORE": [],
          "GROUP_BY": ["f.fid, f.title, f.sha512, p.fid, id, id_type",
                       "f.artists_agg, f.basename_agg"]
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
            query_spec["SELECT"].append("usi.uid, usi.rating, "
                                        "usi.fid AS usi_fid, "
                                        "u.uname, usi.true_score, "
                                        "usi.score, usi.ultp")
            query_spec["FROM"].append("user_song_info usi, users u")
            query_spec["WHERE"].append("usi.fid = f.fid AND "
                                       "usi.uid = %(uid)s AND "
                                       "u.uid = usi.uid")
            query_spec["GROUP_BY"].append('usi.uid, usi.rating, usi_fid, '
                                          'u.uname, usi.true_score, '
                                          'usi.score, usi.ultp')
            query_spec['COUNT_FROM'].append("user_song_info usi, users u")
            if not q and not only_cued:
                query_spec['ORDER_BY'].append("ultp DESC NULLS LAST")

        if owner:
            query_args['owner'] = owner
            owner_from = ("folders fld, folder_owners fo, "
                          "file_locations fl")
            query_spec["FROM"].append(owner_from)
            query_spec['COUNT_FROM'].append(owner_from)
            query_spec["WHERE"].append("""fo.uid = %(owner)s AND
                                          fld.folder_id = fo.folder_id AND
                                          fl.folder_id = fld.folder_id AND
                                          fl.fid = f.fid""")

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
            query_spec['SELECT'].append("CASE WHEN p.reason = 'FROM Search' "                        "THEN 0 ELSE 1 END AS p_reason, "
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
            "results": jsonize(results),
            "total": total
        }
        cherrypy.log(">>>>>>>>>>>>> query running time:%s" % (
            time() - start_time))
        return json_dumps(response)

    @cherrypy.expose
    def users(self):
        return json_dumps(jsonize(listener_watcher.users))

    @cherrypy.expose
    def sync(self, fid, uid):
        spec = {
            'fid': int(fid),
            'uid': int(uid)
        }

        sql = """SELECT *
                 FROM users
                 WHERE uid = %(uid)s
                 LIMIT 1"""
        user = get_assoc_dict(sql, spec)

        if not user['sync_dir']:
            return json_dumps({"RESULT": "Error",
                               "Error": "That user does not have a sync dir."})

        if not os.path.exists(user['sync_dir']):
            try:
                os.makedirs(user['sync_dir'], 0775)
            except:
                pass
            if not os.path.exists(user['sync_dir']):
                return json_dumps({"RESULT": "Error",
                                   "Error": "The sync_dir %r doesn't exist "
                                            "and couldn't be created."
                                            % user['sync_dir']})

        sql = """SELECT *
                 FROM folders
                 WHERE dirname = %(sync_dir)s
                 LIMIT 1"""
        user_folder = get_assoc_dict(sql, user)
        if not user_folder:
            sql = """INSERT INTO folders (dirname)
                     VALUES(%(sync_dir)s)
                     RETURNING *"""
            user_folder = get_assoc_dict(sql, user)
        user_folder['sync_dir'] = user_folder['dirname']

        sql = """SELECT *
                 FROM file_locations
                 WHERE fid = %(fid)s"""
        locations = get_results_assoc_dict(sql, spec)

        sql = """SELECT *
                 FROM folder_owners
                 WHERE uid = %(uid)s AND
                       folder_id = %(folder_id)s"""

        for l in locations:
            spec['folder_id'] = l['folder_id']
            is_owner = get_assoc_dict(sql, spec)
            if is_owner and is_owner != {}:
                return json_dumps({"RESULT": "Error",
                                   "Error": "You already have this file"})

        for l in locations:
            src = os.path.join(l['dirname'], l['basename'])
            dst = os.path.join(user['sync_dir'], l['basename'])
            if not os.path.exists(src):
                continue

            if os.path.exists(dst):
                return json_dumps({"RESULT": "OK",
                                   "Message": "You already have this file."})

            copied = False
            try:
                os.link(src, dst)
                copied = True
            except:
                pass

            if not copied:
                try:
                    shutil.copy2(src, dst)
                    copied = True
                except:
                    pass

            if not copied:
                return json_dumps({
                    "RESULT": "Error",
                    "Error": "Unable to copy file to %r" % dst
                })

            insert_sql = """INSERT INTO file_locations
                     (
                        atime,
                        basename,
                        dirname,
                        end_fingerprint,
                        exists,
                        fid,
                        fingerprint,
                        fixed,
                        folder_id,
                        front_fingerprint,
                        last_scan,
                        middle_fingerprint,
                        mtime,
                        size
                     )
                     VALUES(
                        %(atime)s,
                        %(basename)s,
                        %(dirname)s,
                        %(end_fingerprint)s,
                        %(exists)s,
                        %(fid)s,
                        %(fingerprint)s,
                        %(fixed)s,
                        %(folder_id)s,
                        %(front_fingerprint)s,
                        %(last_scan)s,
                        %(middle_fingerprint)s,
                        %(mtime)s,
                        %(size)s
                    )
                    RETURNING *"""

            spec.update(l)
            print "USER FOLDER"
            pprint(user_folder)
            spec.update({
                'sync_dir': user_folder['sync_dir'],
                'dirname': user_folder['sync_dir'],
                'folder_id': user_folder['folder_id']
            })

            sql = """SELECT * FROM file_locations
                     WHERE dirname = %(sync_dir)s AND
                           basename = %(basename)s
                     LIMIT 1"""
            record = get_assoc_dict(sql, spec)
            if record:
                return json_dumps({"RESULT": "OK",
                                   "Message": "Already copied"})

            print mogrify(insert_sql, spec)
            record = get_assoc_dict(insert_sql, spec)
            if record and record['dirname'] == user_folder['sync_dir']\
               and record['folder_id'] == user_folder:
                return json_dumps({"RESULT": "OK",
                                   "Message": "Copied to sync dir."})
            else:
                return json_dumps({
                    "RESULT": "Error",
                    "Error": "Unable to insert new file_location record."
                })

        return json_dumps({"RESULT": "FAIL",
                           "Message":
                           "The source file doesn't exist anywhere."})


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
    static_path = sys.path[0]
    static_img_path = os.path.join(static_path, "static", "images")
    print "IMAGE PATH:", static_img_path
    favicon = os.path.join(static_img_path, "favicon.ico")
    print "IMAGE:", favicon
    cherrypy.quickstart(FmpServer(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': ChatWebSocketHandler
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': favicon
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
        return fid
    except:
        print "FAILED FID"
        fid = -1

    try:
        eid = playlist.files[playlist.index].eid
        if eid:
            watch_id = eid
            return eid
    except:
        eid = -1

    # cherrypy.log("watch_id:%s" % watch_id)
    return watch_id

def broadcast_countdown():
    watch_id = current_watch_id()

    # print({'fid': fid, 'eid': eid, 'watch_id': watch_id})
    voted_to_skip_count = remove_old_votes(watch_id)
    #print({'fid': fid, 'eid': eid, 'watch_id': watch_id}, 'after')

    seconds_left_to_skip = None
    # print "skip_countdown:",skip_countdown, skip_countdown.get(watch_id)
    if skip_countdown.get(watch_id) is not None:
        print "skip_countdown:",skip_countdown, skip_countdown.get(watch_id)
        if playlist.player.state_string != "PLAYING":
            skip_countdown[watch_id] = time() + 5
        seconds_left_to_skip = math.ceil(skip_countdown[watch_id] - time())
        print "seconds_left_to_skip:", seconds_left_to_skip
        if seconds_left_to_skip < 0:
            print "*** DE INC ***"
            playlist.files[playlist.index].vote_data = vote_data[watch_id]
            del skip_countdown[watch_id]
            GObject.idle_add(playlist.majority_next, ())
            seconds_left_to_skip = 0


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
        print "broadcast:", json.dumps(data, sort_keys=True,
                            indent=4, separators=(',', ': '))
    json_broadcast(data)
    broadcast_countdown()
    json_broadcast({'vote_data':vote_data})






