#!/usr/bin/env python
# lib/flask_server.py -- flask server
#    Copyright (C) 2013 Eugene Miller <theerm@gmail.com>
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

from __init__ import *
from flask import Flask
from flask import request
from flask import redirect
from flask import session
from flask import jsonify

import datetime
import random
import time
import hashlib
import json
import socket
import alsaaudio
import logging
import re

from bson import json_util
import json

from player import PLAYING

import threading
import time

from flask import render_template
import lib.fobj as fobj

from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application

# from flasky import app

class MainHandler(RequestHandler):
  def get(self):
    self.write("This message comes from Tornado ^_^")

app = Flask(__name__)
app.debug = True

tr = WSGIContainer(app)

application = Application([
    (r"/tornado", MainHandler),
    (r".*", FallbackHandler, dict(fallback=tr)),
])

@app.route("/")
def index():
    global playing, player, tray
    print "FLASK PLAYING:", playing.filename
    print "REQUEST:",request
    print "request.args:",request.args
    cmd = request.args.get("cmd","")
    if cmd:
        if cmd == "pause":
            player.pause()
        if cmd == "next":
            player.next()
        if cmd == "prev":
            player.prev()
        if cmd == "seek_ns":
            pos = request.args.get("value",0)
            player.seek_ns(pos)
            
        if cmd == "rate":
            rating = request.args.get("value",0)
            uid = request.args.get("uid",0)
            print "************* RATE ****************"
            print "RATE:uid:%s rating:%s" % (uid, rating)
            fid = request.args.get("fid","")
            if not fid and uid and hasattr(playing, "ratings_and_scores"):
                print "RATE 2:uid:%s rating:%s" % (uid, rating)
                playing.rate(uid=uid, rating=rating)
            elif fid and uid:
                print "RATE 3: fid:%s, uid:%s rating:%s" % (fid, uid, rating)
                f = fobj.get_fobj(fid=fid)
                f.rate(uid=uid, rating=rating)
                return json_dump(f.to_dict())

        if cmd == "vol":
            set_volume(request.args.get("value",-1))

        if request.args.get("status",""):
            return status()
        return redirect("/")
    return render_template("index.html", player=player, playing=playing, 
                           PLAYING=PLAYING, volume=get_volume())

@app.route("/status/")
def status():
    # -{{player.pos_data["left_str"]}} {{player.pos_data["pos_str"]}}/{{player.pos_data["dur_str"]}}
    global player, playing
    # print "PLAYING",playing.to_dict()

    return jsonify(player=player.to_dict(), playing=playing.to_dict(),
                   volume=get_volume())

def get_volume():
    cards = alsaaudio.cards()
    for i, c in enumerate(cards):
        try:
            m = alsaaudio.Mixer('Master',cardindex=i)
            result = m.getvolume()
            volume = result.pop()
            return volume
        except alsaaudio.ALSAAudioError:
            continue
    return -1;

def prase_words(q, filter_by="all"):
    q = "%s" % q
    words = q.split()
    querys = []

    word_template = """
        LOWER(a.artist) SIMILAR TO %s OR
        LOWER(g.genre) SIMILAR TO %s OR
        LOWER(f.basename) SIMILAR TO %s OR
        LOWER(f.title) SIMILAR TO %s OR
        LOWER(al.album_name) SIMILAR TO %s
    """
    
    dot_template = """
        a.artist ILIKE %s OR
        g.genre ILIKE %s OR
        f.basename ILIKE %s OR
        f.title ILIKE %s OR
        al.album_name ILIKE %s
    """

    non_word = re.compile(r"[\W]")
    for w in words:
        if not w:
            continue
        w = w.lower()
        template = word_template
        if non_word.search(w):
            template = dot_template
            w = "%%%s%%" % w
        else:
            w = "%%[[:<:]]%s[[:>:]]%%" % w

        querys.append(pg_cur.mogrify(template, (w,w,w,w,w)))

    if querys:
        if filter_by == "any":
            query = "(%s)" % (") OR (".join(querys))
        else:
            query = "(%s)" % (") AND (".join(querys))
        return query
    return ""

def listeners_info_for_fid(fid):
    query = """SELECT uname, usi.*
               FROM user_song_info usi, users u
               WHERE usi.fid = %s AND u.uid = usi.uid AND u.listening = true
               ORDER BY admin DESC, uname ASC
    """
    print "query:%s" % query
    results = []
    try:
        for r in get_results_assoc(query, (fid,)):
            # f = fobj.get_fobj(**r)
            #fd = f.to_dict()
            # fd.cued = r.cued
            results.append(dict(r))
        print "results:",results
    except psycopg2.IntegrityError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.IntegrityError:",err
    return results

def get_results(q="", start=0, limit=20, filter_by="all"):
    start = int(start)
    limit = int(limit)
    """
    SELECT DISTINCT f.fid, basename, genre, artist, p.fid AS cued,
           album_name, 
           ts_rank(tsv, query)
FROM files f
    LEFT JOIN file_artists fa ON f.fid = fa.fid 
    LEFT JOIN artists a ON a.aid = fa.aid 
    LEFT JOIN file_genres fg ON fg.fid = f.fid 
    LEFT JOIN genres g ON g.gid = fg.gid 
    LEFT JOIN preload p ON p.fid = f.fid
    LEFT JOIN album_files af ON af.fid = f.fid
    LEFT JOIN albums al ON al.alid = af.alid,
    keywords kw,
    plainto_tsquery('the erm fears') query
WHERE kw.fid = f.fid AND tsv @@ query
ORDER BY ts_rank DESC;"""

    query = """SELECT DISTINCT f.fid, basename, title, genre, artist, p.fid AS cued,
                               album_name,
                               ts_rank(tsv, query)
                   FROM files f 
                        LEFT JOIN file_artists fa ON f.fid = fa.fid 
                        LEFT JOIN artists a ON a.aid = fa.aid 
                        LEFT JOIN file_genres fg ON fg.fid = f.fid 
                        LEFT JOIN genres g ON g.gid = fg.gid 
                        LEFT JOIN preload p ON p.fid = f.fid
                        LEFT JOIN album_files af ON af.fid = f.fid
                        LEFT JOIN albums al ON al.alid = af.alid,
                        keywords kw,
                        to_tsquery(%s) query
                    WHERE kw.fid = f.fid AND tsv @@ query
                    ORDER BY ts_rank DESC
            """

    query = "%s LIMIT %d OFFSET %d" % (query, limit, start)
    print "QUERY:%s" % query
    results = []
    _q = q.split()
    if filter_by == "all":
        q = " & ".join(_q)
    else:
        q = " | ".join(_q)
    try:
        for r in get_results_assoc(query, (q,)):
            # f = fobj.get_fobj(**r)
            #fd = f.to_dict()
            # fd.cued = r.cued
            rdict = dict(r)
            rdict['usi'] = listeners_info_for_fid(r['fid'])
            results.append(rdict)
    except psycopg2.IntegrityError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.IntegrityError:",err
    except psycopg2.InternalError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.InternalError:",err
    return results


def set_volume(vol):
    cards = alsaaudio.cards()
    print "SET_VOLUME:",vol
    print "type:",type(vol)
    if isinstance(vol, str) or isinstance(vol,unicode):
        print "SET_VOLUME2:",vol
        if vol in ("-","+"):
            cur_vol = get_volume()
            if vol == "-":
                vol = cur_vol - 3
            else:
                vol = cur_vol + 3

            if vol < 0:
                vol = 0
            if vol > 100:
                vol = 100
        print "SET_VOLUME3:",vol
    try:
        vol=int(vol)
    except:
        print "FAIL:",vol
        return

    if vol < 0 or vol > 100:
        return;
    for i, c in enumerate(cards):
        try:
            m = alsaaudio.Mixer('Master',cardindex=i)
            m.setvolume(vol)
        except alsaaudio.ALSAAudioError:
            continue

"""
                 List of relations
 Schema |           Name           | Type  | Owner 
--------+--------------------------+-------+-------
 public | album_files              | table | erm
 public | albums                   | table | erm
 public | artists                  | table | erm
 public | dont_pick                | table | erm
 public | file_artists             | table | erm
 public | file_genres              | table | erm
 public | files                    | table | erm
 public | genres                   | table | erm
 public | netcast_episodes         | table | erm
 public | netcast_listend_episodes | table | erm
 public | netcast_subscribers      | table | erm
 public | netcasts                 | table | erm
 public | preload                  | table | erm
 public | tags_binary              | table | erm
 public | tags_text                | table | erm
 public | user_artist_history      | table | erm
 public | user_artist_info         | table | erm
 public | user_history             | table | erm
 public | user_song_info           | table | erm
 public | users                    | table | erm
(20 rows)
"""

def json_obj_handler(obj):
    if obj is None:
        return 'null';
    """Default JSON serializer."""
    import calendar, datetime

    if isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(
        calendar.timegm(obj.timetuple()) * 1000 +
        obj.microsecond / 1000
    )
    return millis

def json_dump(obj):
    return json.dumps(obj, default=json_obj_handler) or "{};"

@app.route('/search/', methods=['GET', 'POST'])
def search():
    results = None
    q = request.args.get("q","")
    filter_by = "%s" % request.args.get("f","all")
    if filter_by == "any":
        filter_by = "any"
    else:
        filter_by = "all"
    start = "%s" % request.args.get("s", "0")
    limit = "%s" % request.args.get("s", "20")
    start_time = time.time()
    print "start:",start_time
    results = get_results(q, start=start, limit=20, filter_by=filter_by)
    print "end:", time.time() - start_time
    json_results = json_dump(results)

    if not request.args.get("ajax", False):
        return render_template("search.html", playing=playing, PLAYING=PLAYING,
                               results=json_results, q=request.args.get("q",""),
                               filter_by=filter_by)
    resp = {
        "player": player.to_dict(), 
        "playing": playing.to_dict(),
        "results": results, 
        "q": request.args.get("q","")
    }
    print "RESP:"
    return json_results

@app.route('/cue/', methods=['GET', 'POST'])
def cue():
    user = get_assoc("""SELECT uid
                        FROM users WHERE listening = true
                        LIMIT 1""")
    fid = request.args.get('fid')
    finfo = get_assoc("""SELECT * 
                         FROM files 
                         WHERE fid = %s 
                         LIMIT 1""", (fid,))
    if finfo and fid:
        cue = request.args.get('cue', 'false')
        print "CUE:",cue
        if cue == 'true':
            cue = True
        else:
            cue = False
        if cue:
            query("""INSERT INTO preload (fid, uid, reason)
                     VALUES (%s, %s, %s)""", (fid, user['uid'], "From search"))
            return "{cued:true}"
        else:
            query("""DELETE FROM preload WHERE fid = %s""", (fid,))
            return "{cued:false}"



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # session['username'] = request.form['username']
        user = get_assoc("""SELECT * 
                            FROM users 
                            WHERE uname = %s 
                            LIMIT 1""", (request.form['username'],))
        if user:

            return redirect(url_for('index'))


    return render_template("login.html", playing=playing, PLAYING=PLAYING)

def worker(*args, **kwargs):
    """thread worker function"""
    print 'WORKER, args:',args, kwargs
    while True:
        try:
            # app.run(debug=False, host='0.0.0.0', port=5050)
            app.debug = True
            application.listen(5050)
            IOLoop.instance().start()
        except socket.error, e:
            print "##########################################"
            print "socket.error:",e
            print "##########################################"
            print "ATTEMPTING RE-BIND in 10 seconds"
            time.sleep(10)
    return


def start_in_thread():
    print "START CALLED!"
    t = threading.Thread(target=worker, args=(0,))
    threads.append(t)
    t.start()

def start():
    print "START()"
    worker()

def call_test():
    print "CALL TEST COMPLETED"

def quit():
    kill_threads()


if __name__ == "__main__":
    worker()
    # app.run(debug=False, host='0.0.0.0', port=5050)

