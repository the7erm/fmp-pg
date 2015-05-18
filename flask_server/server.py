#!/usr/bin/env python2
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

from gevent import monkey
monkey.patch_all()

from __init__ import *
from flask import Flask, request, redirect, session, jsonify, send_file, \
                  Response, render_template

from threading import Thread
from flask.ext.socketio import SocketIO, emit, join_room, leave_room
from flask.ext.cache import Cache
from werkzeug.datastructures import Headers
import datetime
import random
import time
import hashlib
import json
import socket
import alsaaudio
import logging
import re
import base64
import StringIO
import psycopg2
import decimal
import os
import sys
from lib.netcast_fobj import Netcast
from copy import deepcopy
from pprint import pprint, pformat
from lib.parse_df import update_devices
import shutil
import math
import traceback

# from bson import json_util
import json

from lib.player import PLAYING

import threading
import time

from flask import render_template
import lib.fobj as fobj
from lib.rating_utils import rate as simple_rate, mark_as_played, \
                             calculate_true_score_for_fid_uid,\
                             set_score_for_uid, convert_when_to_dt,\
                             update_user_history


from lib.local_file_fobj import get_words_from_string, Local_File
from lib.scanner import scan_file

from tornado.wsgi import WSGIContainer
from tornado.ioloop import IOLoop
from tornado.web import FallbackHandler, RequestHandler, Application

# from flasky import app

from satellite import get_id_type, get_time

debug = True

def _print(*args, **kwargs):
    if debug:
        for arg in args:
            print arg,
        if kwargs != {}:
            print kwargs
        print
        sys.stdout.flush()

def _pprint(*args, **kwargs):
    if debug:
        pprint(*args, **kwargs)
        sys.stdout.flush()

class MainHandler(RequestHandler):
  def get(self):
    self.write("This message comes from Tornado ^_^")



app = Flask(__name__)
app.debug = False
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
cache = Cache(app,config={'CACHE_TYPE': 'simple'})
thread = None

import gtk
import gobject

import gevent


def _trigger_loop():
    gobject.timeout_add(10, gevent_loop, priority=gobject.PRIORITY_HIGH)

def gevent_loop():
    gevent.sleep(0.001)
    _trigger_loop()
    return False

def emit_time_status(*args, **kwargs):
    return

def get_extended():
    global player, playing
    extended = player.to_dict()
    extended.update(playing.to_full_dict())
    return extended;

@app.errorhandler(500)
def error_500(e):
    print "*"*20,"ERROR 500","*"*20
    print "E:",e
    request_data = request.get_data()
    print "request_data:",request_data
    traceback.print_exc()
    print "*"*20,"/ERROR 500","*"*20
    return "Internal Service Error 500", 500

@app.route("/test-500/")
def test_500(*args, **kwargs):
    print "ERROR 500 TEST"
    float("I MUST FAIL")


@app.route("/index-old/")
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
                           PLAYING=PLAYING, volume=get_volume(),
                           extended=get_extended())


def index2():
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
                           PLAYING=PLAYING, volume=get_volume(), 
                           extended=get_extended())

# @app.route("/angular/")
@app.route("/")
def angular():
    global playing, player, tray
    return render_template("angular.html", player=player, playing=playing, 
                           PLAYING=PLAYING, volume=get_volume(), 
                           extended=get_extended())

@app.route("/angular/")
def angluar_new():
    global playing, player, tray
    return render_template("angular_new.html", player=player, playing=playing, 
                           PLAYING=PLAYING, volume=get_volume(), 
                           extended=get_extended())

def reload_playing(fid):
    global playing, player
    print "-="*20
    playing_dict = playing.to_dict()
    print "playing_dict.get('fid'):",playing_dict.get('fid')

    if str(playing_dict.get('fid', "")) == str(fid):
        print "RELOAD PLAYING"
        playing.__init__(fid=fid)
    print "-"*20

@app.route("/remove-file-artist/")
def remove_file_artist():
    cache.clear()
    fid = request.args.get("fid")
    aid = request.args.get("aid")
    print "fid:", fid
    print "aid:", aid
    query("""DELETE FROM file_artists
                 WHERE fid = %s AND aid = %s""", 
             (fid, aid))
    
    total = get_assoc("""SELECT count(*) as total
                         FROM file_artists
                         WHERE aid = %s""", (aid,))
    if total['total'] == 0:
      query("""DELETE FROM artists 
               WHERE aid = %s""", (aid,))
    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")

    reload_playing(fid)

    return json_dump({"result": "success"})

@app.route("/add-file-artist/")
def add_file_artist():
    cache.clear()
    fid = request.args.get("fid")
    artist = request.args.get("artist")
    if not artist:
      return json_dump({"result": "failure"});
    artist_info = get_assoc("""SELECT * 
                               FROM artists 
                               WHERE artist = %s 
                               LIMIT 1""",
                           (artist, ))
    if not artist_info:
      artist_info = get_assoc("""INSERT INTO artists (artist)
                                 VALUES(%s) RETURNING *""",
                             (artist,))
    present = get_assoc("""SELECT * 
                           FROM file_artists
                           WHERE fid = %s and aid = %s
                           LIMIT 1""",
                        (fid, artist_info['aid']))

    if not present:
        print "INSERTING"
        artist_info  = get_assoc("""INSERT INTO file_artists (fid, aid) 
                     VALUES(%s, %s)
                     RETURNING * """,
                  (fid, artist_info['aid']))

    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")
    reload_playing(fid)
    return json_dump({"result": "success",
                      "aid": artist_info['aid'], 
                      "fid": fid})

@app.route("/remove-file-genre/")
def remove_file_genre():
    cache.clear()
    fid = request.args.get("fid")
    gid = request.args.get("gid")
    print "fid:", fid
    print "gid:", gid
    return json_dump({"result": "test"})
    query("""DELETE FROM file_genres
                 WHERE fid = %s AND gid = %s""", 
             (fid, gid))
    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")
    reload_playing(fid)
    return json_dump({"result": "success"})

@app.route("/add-file-genre/")
def add_file_genre():
    cache.clear()
    fid = request.args.get("fid")
    genre = request.args.get("genre")
    if not genre:
      return json_dump({"result": "failure"});
    info = get_assoc("""SELECT * 
                        FROM genres 
                        WHERE genre = %s 
                        LIMIT 1""",
                    (genre, ))
    if not info:
      info = get_assoc("""INSERT INTO genres (genre)
                                 VALUES(%s) RETURNING *""",
                             (genre,))

    present = get_assoc("""SELECT * 
                           FROM file_genres
                           WHERE fid = %s and gid = %s
                           LIMIT 1""",
                        (fid, info['gid']))

    if not present:
        print "INSERTING"
        info  = get_assoc("""INSERT INTO file_genres (fid, gid) 
                             VALUES(%s, %s)
                             RETURNING * """,
                         (fid, info['gid']))

    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")
    reload_playing(fid)
    return json_dump({"result": "success",
                      "gid": info['gid'], 
                      "fid": fid})

@app.route("/remove-file-album/")
def remove_file_album():
    cache.clear()
    fid = request.args.get("fid")
    alid = request.args.get("alid")
    print "fid:", fid
    print "alid:", alid
    query("""DELETE FROM album_files
                 WHERE fid = %s AND alid = %s""", 
             (fid, aid))
    
    total = get_assoc("""SELECT count(*) as total
                         FROM album_files
                         WHERE alid = %s""", (alid,))
    if total['total'] == 0:
      query("""DELETE FROM album_files 
               WHERE alid = %s""", (alid,))

    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")

    reload_playing(fid)

    return json_dump({"result": "success"})

@app.route("/add-file-album/")
def add_file_album():
    cache.clear()
    fid = request.args.get("fid")
    album_name = request.args.get("album_name")
    if not album_name:
      return json_dump({"result": "failure"});
    info = get_assoc("""SELECT * 
                        FROM albums 
                        WHERE album_name = %s 
                        LIMIT 1""",
                    (album_name, ))
    if not info:
      info = get_assoc("""INSERT INTO albums (album_name)
                          VALUES(%s) RETURNING *""",
                      (album_name,))

    present = get_assoc("""SELECT * 
                           FROM album_files
                           WHERE fid = %s and aid = %s
                           LIMIT 1""",
                       (fid, info['alid']))

    if not present:
        info  = get_assoc("""INSERT INTO album_files (fid, alid) 
                             VALUES(%s, %s)
                             RETURNING * """,
                         (fid, info['alid']))

    query("""UPDATE files SET edited = true WHERE fid = %s""", (fid,))
    query("COMMIT")
    reload_playing(fid)
    return json_dump({"result": "success",
                      "alid": info['alid'], 
                      "fid": fid})

@app.route("/kw")
def keywords():
    # http://gd.geobytes.com/AutoCompleteCity?callback=jQuery17107360035724240884_1403536897337&q=che&_=1403536918779
    # jQuery17107360035724240884_1403536897338(["Cheyenne Wells, CO, United States","Cheyenne, OK, United States","Cheyenne, WY, United States","Cheyney, PA, United States","Glen Richey, PA, United States","New Port Richey, FL, United States","Ocheyedan, IA, United States","Pechey, QL, Australia","Port Richey, FL, United States","Richey, MT, United States","Richeyville, PA, United States","Teachey, NC, United States"]);
    print "request.args:", request.args
    callback = request.args.get('callback')
    words = []

    q = "%s" % request.args.get('q', "")

    limit = 10
    max_results = 10

    result = cache_get_results_assoc("""SELECT artist 
                                        FROM artists 
                                        WHERE artist ~* %s
                                        ORDER BY artist
                                        LIMIT """+str(limit), (q,))

    for w in result:
        l = w["artist"].lower().strip()
        if l not in words:
            words.append(l)

    limit = max_results - len(words)

    if limit > 0:
        result = cache_get_results_assoc("""SELECT genre 
                                            FROM genres 
                                            WHERE genre ~* %s
                                            ORDER BY genre 
                                            LIMIT """+str(limit), (q,))

        for w in result:
            l = w["genre"].lower().strip()
            if l not in words:
               words.append(l)

        limit = max_results - len(words)

    if limit > 0:
        result = cache_get_results_assoc("""SELECT basename 
                                            FROM file_locations 
                                            WHERE basename ~* %s
                                            ORDER BY basename
                                            LIMIT """+str(limit), (request.args.get('q'),))

        for w in result:
            l = w['basename'].lower().strip()
            if l not in words:
                words.append(l)

    words.sort()

    if callback:
        return "%s(%s)" % (callback,json.dumps(words)), 200
    else:
        return json.dumps(words), 200

@app.route("/kwa")
def keywords_artists():
    q = "%s" % request.args.get('q', "")

    result = cache_get_results_assoc("""SELECT aid, artist 
                                        FROM artists 
                                        WHERE artist ~* %s
                                        ORDER BY artist
                                        LIMIT 10""", (q,))
    response = []
    for r in result:
        response.append({"aid": r['aid'], "artist": r['artist']})

    return json.dumps(response)

@app.route("/kwg")
def keywords_genres():
    q = "%s" % request.args.get('q', "")

    result = cache_get_results_assoc("""SELECT gid, genre 
                                        FROM genres 
                                        WHERE genre ~* %s
                                        ORDER BY genre
                                        LIMIT 10""", (q,))
    response = []
    for r in result:
        response.append({"gid": r['gid'], "genre": r['genre']})

    return json.dumps(response)

@app.route("/kwal")
def keywords_albums():
    q = "%s" % request.args.get('q', "")

    result = cache_get_results_assoc("""SELECT alid, album_name 
                                        FROM albums 
                                        WHERE album_name ~* %s
                                        ORDER BY album_name
                                        LIMIT 10""", (q,))
    response = []
    for r in result:
        response.append({"alid": r['alid'], "album_name": r['album_name']})

    return json.dumps(response)

@cache.memoize(timeout=5)
def file_history(_id, id_type):
    history_res = get_results_assoc("""SELECT uh.*, uname
                                       FROM user_history uh, users u
                                       WHERE uh.uid = u.uid AND 
                                             u.listening = true AND
                                             time_played IS NOT NULL AND
                                             uh.id = %s AND 
                                             uh.id_type = %s
                                       ORDER BY u.uname, 
                                                time_played DESC, 
                                                admin DESC""",
                                       (_id, id_type))
    results = []
    previous_date = None
    previous_uid = None
    for h in history_res:
        h = dict(h)
        h['time_played'] = h['time_played'].isoformat()
        if previous_uid != h['uid']:
            previous_date = None
        previous_uid = h['uid']
        h['gap'] = None
        if previous_date:
            q = """SELECT count(*) AS total
                                  FROM user_history 
                                  WHERE id != %s AND 
                                        time_played >= %s AND
                                        time_played <= %s AND 
                                        uid = %s""";
            args = (_id,
                    h['time_played'],
                    previous_date,
                    h['uid'])
            # print "QUERY:", pg_cur.mogrify(q, args)
            played = cache_get_assoc(q, args)
            results[len(results) - 1]['gap'] = played['total']
        previous_date = h['time_played']
        h['date_played'] = h['date_played'].isoformat()

        results.append(h)
    return results

@app.route("/status/")
def status():
    # print "STATUS"
    # -{{player.pos_data["left_str"]}} {{player.pos_data["pos_str"]}}/{{player.pos_data["dur_str"]}}
    global playing, player
    # print "PLAYING",playing.to_dict()
    
    player_dict = player.to_dict()
    playing_dict = playing.to_full_dict()

    extended = deepcopy(player_dict)
    extended.update(deepcopy(playing_dict))

    extended['history'] = []
    if playing_dict.get('fid'):
      extended['history'] = file_history(playing_dict['fid'], 'f')
    elif playing_dict.get('eid'):
      extended['history'] = file_history(playing_dict['eid'], 'e')

    if not extended.get('artists'):
      extended['artists'] = [{'artist':extended['artist_title']}]

    if not extended.get('genres'):
      extended['genres'] = []

    extended = convert_res_to_dict(extended)

    return jsonify(player=player_dict, playing=playing_dict,
                   volume=get_volume(), extended=extended)

def get_volume():
    cards = alsaaudio.cards()
    for i, c in enumerate(cards):
        try:
            m = alsaaudio.Mixer('Master', cardindex=i)
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

@cache.memoize(timeout=60)
def listeners_info_for_fid(fid):
    query = """SELECT uname, usi.*, f.sha512
               FROM user_song_info usi, users u, files f
               WHERE usi.fid = %s AND u.uid = usi.uid AND u.listening = true AND
                     f.fid = usi.fid
               ORDER BY admin DESC, uname ASC
    """
    # print "query:%s" % query
    return convert_to_dict(cache_get_results_assoc(query, (fid,)))

@cache.memoize(timeout=30)
def convert_to_dict(res):
    if not res:
        return []
    results = []
    for r in res:
        results.append(dict(r))
    return results

def artists_for_fid(fid):
    res = get_results_assoc("""SELECT a.*
                               FROM files f, artists a, file_artists fa
                               WHERE f.fid = %s AND
                                     fa.fid = f.fid AND
                                     a.aid = fa.aid
                               ORDER BY artist""", (fid,))
    return convert_to_dict(res)

def albums_for_fid(fid):
    res = get_results_assoc("""SELECT al.* 
                               FROM files f, albums al, album_files af
                               WHERE f.fid = %s AND
                                     af.fid = f.fid AND
                                     al.alid = af.alid
                               ORDER BY album_name""", (fid,))
    return convert_to_dict(res)

def genres_for_fid(fid):
    res = get_results_assoc("""SELECT g.* 
                               FROM files f, genres g, file_genres fg
                               WHERE f.fid = %s AND
                                     fg.fid = f.fid AND
                                     fg.gid = g.gid
                               ORDER BY genre""", (fid,))
    return convert_to_dict(res)

@cache.memoize(timeout=50)
def get_search_results(q="", start=0, limit=20, filter_by="all", 
                      return_total=False):
    start = int(start)
    limit = int(limit)
    query_offset = "LIMIT %d OFFSET %d" % (limit, start)
    # print "Q:",q
    print "get_search_results<<<<<<<<<<<<<<<<<<<<<<<<"
    original_q = deepcopy(q)
    query_args = {}
    query_spec = {
      "SELECT": ["""DISTINCT f.fid, 
                    string_agg(DISTINCT a.artist, ',') AS artists, 
                    title, sha512, p.fid AS cued, f.fid AS id, 
                    'f' AS id_type"""],
      "FROM": ["""files f LEFT JOIN preload p ON p.fid = f.fid
                          LEFT JOIN file_artists fa ON fa.fid = f.fid
                          LEFT JOIN artists a ON a.aid = fa.aid"""],
      "COUNT_FROM": ["files f"],
      "ORDER_BY": [],
      "WHERE": [],
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

    true_score_re = re.compile("true_score\:(\d+)")
    true_score_match = true_score_re.search(q)
    rating_re = re.compile("rating\:(\d+)")
    rating_match = rating_re.search(q)

    if true_score_match or rating_match:
        query_spec['FROM'].append("user_song_info usi")
        query_spec['COUNT_FROM'].append("user_song_info usi")
        sql = """f.fid IN (
                            SELECT DISTINCT usi2.fid 
                            FROM user_song_info usi2
                            WHERE usi2.uid IN (SELECT uid 
                                               FROM users 
                                               WHERE listening = true)
                            AND ({WHERERATINGSCORE})
                          ) AND 
                 f.fid = usi.fid AND
                 usi.uid IN (SELECT uid 
                             FROM users 
                             WHERE listening = true)"""
        query_spec['WHERE'].append(sql)

    if true_score_match:
        true_score = true_score_match.group(1)
        q = q.replace("true_score:%s" % true_score, "").strip()
        true_score = int(true_score)
        query_spec["SELECT"].append("avg(true_score) AS true_score_avg")
        low_true_score = math.floor(true_score / 10) * 10
        high_true_score = low_true_score + 10
        if low_true_score >= 90:
            query_spec["WHERERATINGSCORE"].append("""(
                                        usi2.true_score >= %(low_true_score)s
                                      )""")
        else:
            query_spec["WHERERATINGSCORE"].append("""(
                                        usi2.true_score >= %(low_true_score)s AND
                                        usi2.true_score < %(high_true_score)s
                                      )""")
        query_args['low_true_score'] = low_true_score
        query_args['high_true_score'] = high_true_score
    
    rating = -1
    if rating_match:
        rating = rating_match.group(1)
        q = q.replace("rating:%s" % rating, "").strip()
        query_spec["SELECT"].append(
            "avg(rating) AS rating_avg")
        query_spec["WHERERATINGSCORE"].append("usi2.rating = %(rating)s")
        query_args['rating'] = rating

    
    if true_score_match and rating_match:
        true_score_first_re = re.compile("true_score\:(\d+).*rating\:(\d+)")
        true_score_first_match = true_score_first_re.search(original_q)
        if true_score_first_match:
            query_spec['ORDER_BY'].append("true_score_avg DESC")
            query_spec['ORDER_BY'].append("rating_avg DESC")
        else:
            query_spec['ORDER_BY'].append("rating_avg DESC")
            query_spec['ORDER_BY'].append("true_score_avg DESC")
    elif true_score_match and not rating_match:
        query_spec['ORDER_BY'].append("true_score_avg DESC")
    elif rating_match and not true_score_match:
        query_spec['ORDER_BY'].append("rating_avg DESC")

    if q is not None:
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
          res = cache_get_results_assoc(search_query, query_args)
        except Exception, err:
          print "ERR", err
        print "RES:", res
        for r in res:
            # f = fobj.get_fobj(**r)
            #fd = f.to_dict()
            # fd.cued = r.cued
            rdict = dict(r)
            print "rdict:", rdict
            results.append(rdict)
    except psycopg2.IntegrityError, err:
        query("COMMIT;")
        print "*****ERROR"
        print "(flask_server) psycopg2.IntegrityError:",err
    except psycopg2.InternalError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.InternalError:",err

    if not return_total:
        return results
    print "count_query:", pg_cur.mogrify(count_query, query_args)
    total = cache_get_assoc(count_query, query_args)
    print "MADE IT"
    return results, total['total']

def locations_for_fid(fid):
    sql = """SELECT fl.device_id, flid, label, dirname, basename
             FROM file_locations fl
                  LEFT JOIN devices d ON d.device_id = fl.device_id
             WHERE fid = %s
             ORDER BY label"""
    locations = cache_get_results_assoc(sql, (fid,))

    results = []
    for l in locations:
        obj = dict(l)
        full_path = os.path.join(l['dirname'], l['basename'])
        obj['exists'] = os.path.exists(full_path)
        obj['writable'] = os.access(full_path, os.W_OK)
        results.append(obj)

    return results


@cache.memoize(timeout=60)
def convert_res_to_dict(r):
    print "REGENERATING"
    # print "R:",r
    rdict = dict(r)
    sha512 = ""
    if r['sha512']:
        sha512 = r['sha512']
    # print "DICT:",rdict
    try:
        fid = r['fid']
        rdict['ratings'] = listeners_info_for_fid(fid)
        rdict['artists'] = artists_for_fid(fid)
        rdict['albums'] = albums_for_fid(fid)
        rdict['genres'] = genres_for_fid(fid)
        rdict['locations'] = locations_for_fid(fid)
        if rdict['locations']:
            rdict['dirname'] = rdict['locations'][0]['dirname']
            rdict['basename'] = rdict['locations'][0]['basename']
        else:
            rdict['dirname'] = '-missing-'
            rdict['basename'] = '-missing-'

    except psycopg2.IntegrityError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.IntegrityError:",err
    except psycopg2.InternalError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.InternalError:",err
    return rdict

@app.route("/file-info/<fid>/")
@cache.cached(timeout=30)
def file_info(fid, methods=["GET"]):
    r = get_assoc("""SELECT DISTINCT f.fid, dirname, basename, title,
                                     sha512, p.fid AS cued
                     FROM files f 
                          LEFT JOIN preload p ON p.fid = f.fid,
                          file_locations fl
                     WHERE f.fid = %s AND 
                           fl.fid = f.fid""", 
                     (fid, ))
    rdict = convert_res_to_dict(r)
    rdict['history'] = file_history(r['fid'], 'f')

    return json_dump(rdict)

@app.route("/episode-info/<eid>")
def episode_info(eid, methods=["GET"]):
    r = get_assoc("""SELECT * 
                     FROM netcast_episodes ne, netcasts n
                     WHERE ne.eid = %s AND n.nid = ne.nid""", (eid, ))
    rdict = dict(r)
    rdict['id'] = eid
    rdict['id_type'] = 'e'
    rdict['artist_title'] = "%s - %s" % (rdict['netcast_name'], rdict['episode_title'])
    rdict['artists'] = [{
        "aid": "-1",    
        "artist": rdict['netcast_name']
    }]
    rdict['title'] = rdict['episode_title']
    rdict['dirname'], rdict['basename'] = os.path.split(rdict['local_file'])

    return json_dump(rdict)

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

    if isinstance(obj, decimal.Decimal):
        return float(obj)

    if isinstance(obj, datetime.date):
        obj = datetime.datetime(*obj.timetuple()[:3])

    if isinstance(obj, datetime.datetime):
        if obj.utcoffset() is not None:
            obj = obj - obj.utcoffset()
    millis = int(
        calendar.timegm(obj.timetuple()) * 1000 +
        obj.microsecond / 1000
    )
    return millis
    

@cache.memoize(30)
def json_dump(obj):
    _json = json.dumps(obj, default=json_obj_handler) or "{};"
    # print "JSON:",_json
    return _json

@app.route('/search/', methods=['GET', 'POST'])
def search():
    global player, playing, PLAYING
    json_results = search_data()
    filter_by = get_filter_by()
    extended = get_extended();
    return render_template("search.html", playing=playing, PLAYING=PLAYING,
                           results=json_results, q=request.args.get("q",""),
                           filter_by=filter_by, player=player,
                           extended=extended, volume=get_volume())

def get_filter_by():
    filter_by = "%s" % request.args.get("f", "all")
    if filter_by == "any":
        filter_by = "any"
    else:
        filter_by = "all"
    return filter_by

@app.route('/search-data/', methods=['GET', 'POST'])
def search_data():
    global player, playing
    results = None
    q = request.args.get("q","")
    start, limit = get_start_limit()
    filter_by=get_filter_by()

    print "LIMIT:%s" % limit
    start_time = time.time()
    print "start:",start_time
    results = get_search_results(q, start=start, limit=limit, 
                                 filter_by=filter_by)
    print "end:", time.time() - start_time
    return json_dump(results)

def mark_netcast_as_listened(eid, uid, percent_played, when=None, 
                             *args, **kwargs):
    when = convert_when_to_dt(when)
    update_data = {
      'uid': uid,
      'id': eid,
      'eid': eid,
      'id_type': 'e',
      'percent_played': percent_played,
      'time_played': when,
      'date_played': when.date(),
      'when': when,
      'when_date': when.date(),
      'reason': ""
    }

    print "mark_netcast_as_listened", eid, uid
    sql = """SELECT eid, uid 
             FROM netcast_listend_episodes
             WHERE eid = %(eid)s AND uid = %(uid)s"""
    present = get_assoc(sql, update_data)
    

    if not present:
        sql = """INSERT INTO netcast_listend_episodes (eid, uid, 
                                                       percent_played)
                 VALUES(%(eid)s, %(uid)s, %(percent_played)s)"""

        query(sql, update_data)


    update_user_history(update_data)

def update_score(uid, fid, skip_score):
    if not skip_score:
        return
    sql = """SELECT score 
             FROM user_song_info 
             WHERE uid = %s AND fid = %s"""
    current_score = get_assoc(sql, (uid, fid))
    score = current_score['score']
    print "BEFORE score:", score
    score += skip_score
    print "AFTER score:", score
    if score > 10:
        score = 10
        print "max:10"

    if score <= 0:
        score = 1
        print "min:1"

    sql = """UPDATE user_song_info
             SET score = %s
             WHERE uid = %s AND fid = %s"""

    query(sql, (score, uid, fid))

def mark_dirty_played(obj, listeners):
    print "mark_dirty_played:", obj
    if not obj or not listeners or obj == {}:
        return
    if not obj.get('dirty') and not obj.get('played'):
        return
    print "*"*20
    print "mark_dirty_played:", obj
    id_type = obj.get("id_type", 'f')
    if not obj.get('time'):
        obj['time'] = get_time()
    when = datetime.datetime.fromtimestamp(obj['time'])
    percent_played = obj.get('percent_played')

    if id_type == 'e':
        print "mark_dirty_played OBJ:",pformat(obj)
        _id = obj.get('id')
        for l in listeners:
            print "l:", l
            mark_netcast_as_listened(_id, l['uid'], percent_played, when)
        return

    print "DIRTY"
    
    if id_type == 'f':
        fid = obj.get("id")
    else:
        fid = obj.get('fid')

    print "FID:", fid
    print "WHEN:", when
    print "LISTENERS:", listeners
    
    print "PERCENT_PLAYED:", percent_played
    skip_score = obj.get('skip_score', 0)
    _print("SKIP SCORE:", skip_score)
    reason = obj.get('reason', '')
    if not percent_played:
        print "NO PERCENT PLAYED"
    else:
        for l in listeners:
            # mark_as_played(fid, uid, when, percent_played, *args, **kwargs)
            print "MARK AS PLAYED:", l, fid
            _print("SKIP SCORE:", skip_score)
            update_score(l['uid'], fid, skip_score)
            mark_as_played(fid=fid, 
                           uid=l['uid'], 
                           percent_played=percent_played,
                           when=when,
                           reason=reason)
    
    sql = """DELETE FROM preload WHERE fid = %s"""
    query(sql, (fid,))


def add_obj_to_playlist(obj, playing, new_playlist, already_added,
                        playing_id, playing_id_type):
    print "OBJ:", obj
    o_id, o_id_type = get_id_type(obj)
    obj['o_id'] = o_id
    obj['o_id_type'] = o_id_type
    key = "%s-%s" % (o_id_type, o_id)
    if o_id == playing_id and o_id_type == playing_id_type:
        obj.update(playing)
    if key not in already_added:
        new_playlist.append(obj)
        already_added.append(key)

def build_playlist(history, netcasts, preload, playing):
    new_playlist = []
    already_added = []
    playing_id, playing_id_type = get_id_type(playing)

    
    while preload:
        obj = preload.pop(0)
        add_obj_to_playlist(obj, playing, new_playlist, already_added,
                            playing_id, playing_id_type)
        
        if netcasts:
            last_10 = new_playlist[-10:]
            found_netcast = False
            for f in last_10:
                h_id, h_id_type = get_id_type(f)
                if h_id_type == 'e':
                    found_netcast = True
                    break

            if not found_netcast:
                obj = netcasts.pop(0)
                add_obj_to_playlist(obj, playing, new_playlist, already_added,
                                    playing_id, playing_id_type)

    
    while netcasts:
        obj = netcasts.pop(0)
        add_obj_to_playlist(obj, playing, new_playlist, already_added,
                            playing_id, playing_id_type)

    while history:
        obj = history.pop(0)
        add_obj_to_playlist(obj, playing, new_playlist, already_added,
                            playing_id, playing_id_type)

    add_obj_to_playlist(playing, playing, new_playlist, already_added,
                        playing_id, playing_id_type)
    index = 0

    _print("[PLAYLIST]")
    for i, p in enumerate(new_playlist):
        _print("I:",i)
        if i == index:
            _print("INDEX:", i)
            _pprint(p)
    _print("[/PLAYLIST]")

    return index, new_playlist
    
    

@app.route('/satellite/', methods=['GET', 'POST'])
def satellite():
    print "satellite"
    # cache.clear()
    global playing, player, interaction_tracker
    request_json = request.get_json()
    sql = """SELECT uid, uname FROM users"""
    users = []
    res = cache_get_results_assoc(sql)
    for r in res:
        users.append(dict(r))

    if request_json:
        print "request_json:"
        pprint(request_json)
        remote_last_interaction = request_json.get('last_interaction', 0)
        remote_state = request_json.get('state', 'PAUSED')
        priority = interaction_tracker.get_priority(remote_last_interaction,
                                                    remote_state)

        _playing = request_json.get('playing',{})
        _playlist = request_json.get("playlist", [])
        listeners = request_json.get('listeners', [])
        if not listeners or priority == 'server':
            sql = """SELECT uid, uname FROM users WHERE listening = true"""
            listeners = []
            res = cache_get_results_assoc(sql)
            for r in res:
                listeners.append(dict(r))
        
        listening_uids = []
        for l in listeners:
            listening_uids.append(l['uid'])
            listening(l['uid'], 'true')

        for u in users:
            if u['uid'] not in listening_uids:
              listening(u['uid'], 'false')

        _history = request_json.get("satellite_history", [])
        for p in _history:
            _listeners = p.get('listeners')
            if not _listeners:
                _listeners = listeners
            mark_dirty_played(p, _listeners)

        for p in _playlist:
            _listeners = p.get('listeners')
            if not _listeners:
                _listeners = listeners
            mark_dirty_played(p, _listeners)

        _listeners = _playing.get('listeners')
        if not _listeners:
            _listeners = listeners
        mark_dirty_played(_playing, _listeners)

        playing_dict = get_extended()
        _percent_played = request_json['playing'].get('percent_played', 0)
        playing_dict_percent = playing_dict['pos_data']['percent_played']
        playing_dict_percent = playing_dict_percent.replace("%", "")
        playing_dict_percent = float(playing_dict_percent)

        percent_played = "%.2f" % _percent_played
        playing_dict_percent = "%.2f" % playing_dict_percent
        if priority == 'client' and playing_dict_percent != percent_played:
            if playing_dict.get('id') != request_json['playing'].get('id'):
                sync_playing(request_json['playing'])
            print "*"*20,"SEEK","*"*20
            print "playing_dict_percent:", playing_dict_percent, "!=",
            print percent_played
            player.seek(str(_percent_played)+"%")
            player.update_time()
            playing_dict = get_extended()
            print "_PLAYING:", _playing
            print "playing_dict:", playing_dict
            _playing.update(playing_dict)


    # Send last 10 songs
    sql = """SELECT id, id_type, date_played, title, episode_title,
                    string_agg(
                    to_char(time_played, 'YYYY-MM-DD HH24:MI:SS'), 
                    ','
                    ) AS times_played, 
                    string_agg(to_char(uh.uid, '999'), ',') AS uids,
                    string_agg(artist, ',' ORDER BY artist) AS artists,
                    netcast_name
             FROM users u, 
                  user_history uh
                  LEFT JOIN netcast_episodes ne ON uh.id_type = 'e' AND 
                                                   uh.id = ne.eid
                  LEFT JOIN files f ON uh.id_type = 'f' AND f.fid = uh.id
                  LEFT JOIN file_artists fa ON fa.fid = f.fid
                  LEFT JOIN artists a ON a.aid = fa.aid
                  LEFT JOIN netcasts n ON n.nid = ne.nid
             WHERE listening = true AND u.uid = uh.uid
             GROUP BY time_played, id, id_type, title, episode_title, 
                      date_played, netcast_name
             ORDER BY time_played DESC
             LIMIT 10"""

    res = cache_get_results_assoc(sql)
    history = []
    for h in res:
        history.append(dict(h))
    history.reverse()
    # Send currently playing
    

    # Send preload
    sql = """SELECT DISTINCT row_number() OVER (ORDER BY plid) AS pos, 
                             row_number() OVER ( 
                                PARTITION BY u.uid ORDER BY u.last_time_cued
                             ) AS pos_order,
                             p.plid, p.reason, f.fid,
                             f.fid AS id, 'f' AS id_type,
                             CASE reason 
                               WHEN 'From search' THEN 1
                               ELSE 2
                             END AS reason_order,
                             title,
                             string_agg(
                                artist, ',' ORDER BY artist
                             ) AS artists,
                             u.uid,
                             u.last_time_cued
             FROM preload p,
                  files f
                  LEFT JOIN file_artists fa ON fa.fid = f.fid
                  LEFT JOIN artists a ON a.aid = fa.aid,
                  users u
             WHERE p.fid = f.fid AND u.uid = p.uid
             GROUP BY p.plid, f.fid,  id, id_type, p.reason, u.uid, title, 
                      p.uid, u.last_time_cued
             ORDER BY reason_order, pos_order, last_time_cued, plid"""

    res = cache_get_results_assoc(sql)
    preload = []
    for p in res:
        _p = dict(p)
        last_time_cued = p.get('last_time_cued')
        if last_time_cued:
            _p['last_time_cued'] = "%s" % last_time_cued
        preload.append(dict(_p))

    sql = """SELECT pc.fid, pc.uid, pc.reason, f.title,
                    string_agg(artist, ',' ORDER BY artist) AS artists
             FROM preload_cache pc,
                  files f
                  LEFT JOIN file_artists fa ON fa.fid = f.fid
                  LEFT JOIN artists a ON a.aid = fa.aid
             WHERE pc.fid = f.fid
             GROUP BY pc.fid, pc.uid, pc.reason, f.title"""
    res = cache_get_results_assoc(sql)
    preload_cache = []
    for p in res:
        preload_cache.append(dict(p))

    # Send Netcasts
    sql = """SELECT DISTINCT ne.eid, ne.episode_title, ne.episode_url, 
                             ne.local_file, 'e' AS id_type, ne.eid AS id,
                             netcast_name AS artist, pub_date
             FROM users u,
                  netcasts n,
                  netcast_episodes ne
                  LEFT JOIN netcast_subscribers ns 
                            ON ns.nid = ne.nid
                  LEFT JOIN netcast_listend_episodes nle 
                            ON nle.eid = ne.eid AND
                               nle.uid = ns.uid
             WHERE nle.uid IS NULL AND
                   ns.nid = ne.nid AND
                   ns.uid = u.uid AND
                   ne.local_file IS NOT NULL AND
                   u.listening = true AND
                   n.nid = ne.nid
             ORDER BY pub_date DESC"""

    res = cache_get_results_assoc(sql)
    netcasts = []
    for r in res:
        _r = dict(r)
        pub_date = _r.get('pub_date')
        if pub_date:
            _r['pub_date'] = "%s" % pub_date
        netcasts.append(_r)

    sql = """SELECT uid, uname FROM users WHERE listening = true"""
    listeners = []
    res = cache_get_results_assoc(sql)
    for r in res:
        listeners.append(dict(r))

    print "/satellite"
    extended = get_extended()

    return json_dump({
        "history": history,
        "playing": extended,
        "preload": preload,
        "netcasts": netcasts,
        "listeners": listeners,
        "preload_cache": preload_cache,
        "users": users,
        "last_interaction": interaction_tracker.last_interaction
    })


cache_data = {}
def do_search(q, start, limit, filter_by, return_total=False):
    print "DO SEARCH"
    start_time = datetime.datetime.now()

    if not return_total:
        results = get_search_results(q, start=start, limit=limit, 
                                     filter_by=filter_by,
                                     return_total=return_total)
        total = len(results)
    else:
        results, total = get_search_results(q, start=start, limit=limit, 
                                            filter_by=filter_by,
                                            return_total=return_total)
    fixed_results = []
    already_present_fids = []
    for r in results:
        if r['fid'] in already_present_fids:
            continue
        already_present_fids.append(r['fid'])
        fixed_results.append(convert_res_to_dict(r))
    print "LOOPED THROUGH RESULTS"
    json_data = json_dump(fixed_results)
    print "="*20
    print "MADE IT TO RETURN"
    print "fetch time:",datetime.datetime.now() - start_time
    if not return_total:
        return json_data
    return json_data, total

def cache_some_results(q, start, limit, filter_by):
    return
    print "X"*100
    print "CACHE SOME RESULTS"
    for i in range(1, 20):
        print "-=="*20,"search",i
        cache_key = "q:%s s:%s l:%s filter_by:%s" % (q, start, limit, filter_by)
        print cache_key
        if cache_key not in cache_data:
            res = do_search(q, start, limit, filter_by)
        else:
            print "cached"
            res = True
        if not res:
            print "NO RES", cache_key
            break
        start = start+limit

@app.route('/search-data-new/', methods=['GET', 'POST'])
def search_data_new():
    headers = Headers()
    start_time = datetime.datetime.now()
    # convert_res_to_dict
    """
    HTTP/1.1 206 Partial Content
    Accept-Ranges: items
    Content-Range: 0-24/100
    Range-Unit: items
    Content-Type: application/json"""
    results = None
    q = request.args.get("q","")
    start, limit, end = get_start_limit(True)
    print "start:%s limit:%s end:%s" % (start, limit, end)
    filter_by=get_filter_by()
    status = 206
    mimetype = "application/json"
    cachetimout = 60

    print "LIMIT:%s" % limit
    fixed_results, total = do_search(q, start, limit, filter_by, 
                                     return_total=True)
    print "RUNNING TIME:", datetime.datetime.now() - start_time
    print "total:", total

    headers.add("Accept-Ranges", "items")
    headers.add('Content-Range','%s-%s/%s' % (str(start), str(end), str(total)) )
    headers.add("Range-Unit", "items")
    headers.add("Content-Type", mimetype)

    response = Response(fixed_results, status=status, 
                        mimetype=mimetype, headers=headers, 
                        direct_passthrough=True)
    response.cache_control.public = True
    response.cache_control.max_age = 0
    response.last_modified = int(time.time())
    response.expires=int( time.time() )
    response.make_conditional(request)

    print "MADE IT 2"

    return response


def get_start_limit(return_end=False):
    start = "%s" % request.args.get("s", "0")
    limit = "%s" % request.args.get("l", "10")

    if request.headers.has_key("Range"):
        ranges = re.findall(r"\d+", request.headers["Range"])
        start = int( ranges[0] )
        if len(ranges) > 1:
            end = int( ranges[1] )
            if end and end > start:
                limit = end - start + 1
    start = int(start)
    limit = int(limit)
    
    
    if not start:
        start = 0
    if not limit:
        limit = 10
    end = start + limit + 1

    if not return_end:
      return start, limit

    return start, limit, end

@app.route('/cue/', methods=['GET', 'POST'])
def cue():
    cache.clear()
    user = get_assoc("""SELECT uid
                        FROM users WHERE listening = true
                        LIMIT 1""")
    fid = request.args.get('fid')
    print "FID:", fid
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
            return file_info(fid)
        else:
            query("""DELETE FROM preload WHERE fid = %s""", (fid,))
            return file_info(fid)

def json_first(dta):
    if not dta:
        return json_dump(None)

    dta = convert_to_dict(dta)
    print "CONVERTED TO DICT:",dta
    return json_dump(dta[0])


@app.route("/rate/<usid>/<fid>/<uid>/<rating>", methods=['GET', 'POST', 'PUT'])
def rate(usid, fid, uid, rating):
    cache.clear()
    global playing
    print "RATE: usid:", usid, 'fid:', fid, 'uid', uid,'rating:', rating
    # playing.rate(uid=uid, rating=rafidting)
    if hasattr(playing, 'fid') and int(playing.fid) == int(fid):
        print "**************** RATING PLAYING FILE **************"
        dta = playing.rate(uid=uid, rating=rating)
        print "8"*100
        print "DTA:", dta
        return json_first([dta])
        
    dta = simple_rate(usid=usid, fid=fid, uid=uid, rating=rating)
    print "5"*100
    print "DTA:",dta
    cache.clear()
    return json_first([dta])

@app.route('/player/<cmd>', methods=['GET', 'POST', 'PUT'])
def player_command(cmd):
    global player
    cmd = cmd.lower();
    valid_commands = ['play', 'pause', 'next', 'prev', 'status']
    if cmd not in valid_commands:
        return playing_file()
    if cmd in ('play', 'pause'):
        player.pause()
    if cmd == "next":
        player.next()
    if cmd == "prev":
        player.prev()
    return status()


@app.route("/seek/<typ>/<val>", methods=["GET", "POST", "PUT"])
def seek(typ, val):
    global player
    if typ == 'nano':
        nano = int(val)
        if nano >= 0:
            player.seek_ns(nano)
    return json_dump({"value": player.pos_data["value"]})


@app.route("/playing/", methods=['GET', 'POST', 'PUT'])
def playing_file():
    global playing
    return json_dump(playing.to_full_dict())

@app.route("/playing/image.png", methods=["GET"])
def playing_image():
    global player
    output = StringIO.StringIO()
    img_data = ""
    if "image-raw" in player.tags:
        img_data = player.tags["image-raw"]
    elif "preview-image-raw" in player.tags:
        img_data = player.tags["preview-image-raw"]
    output.write(img_data)
    output.seek(0)
    return send_file(output, mimetype='image/png')

@app.route("/favicon.ico", methods=["GET"])
def favicon():
    return send_file("favicon.ico", mimetype='image/png')

@app.route("/volume/<new_val>", methods=['POST', 'PUT', 'GET'])
def volume(new_val):
    set_volume(new_val);
    return json_dump({"value": new_val})

@app.route("/history/", methods=['get'])
def history():
    json_results=history_data()
    extended=get_extended()
    return render_template("history.html", playing=playing, PLAYING=PLAYING,
                           results=json_results, player=player,
                           extended=extended, volume=get_volume())

@app.route('/history-data/', methods=['GET'])
def history_data():

    headers = Headers()
    start_time = datetime.datetime.now()
    # convert_res_to_dict
    """
    HTTP/1.1 206 Partial Content
    Accept-Ranges: items
    Content-Range: 0-24/100
    Range-Unit: items
    Content-Type: application/json"""
    results = None
    q = request.args.get("q","")
    start, limit, end = get_start_limit(True)
    print "start:%s limit:%s end:%s" % (start, limit, end)
    filter_by=get_filter_by()
    status = 206
    mimetype = "application/json"
    cachetimout = 60

    print "LIMIT:%s" % limit
    # string_agg(DISTINCT a.artist, ',') AS artists
    q = """SELECT f.fid, title, sha512, p.fid AS cued,
                  string_agg(
                      to_char(uh.time_played, 'YYYY-MM-DD HH24:MI:SS'), ','
                  ) AS uh_time_played2
           FROM files f 
                LEFT JOIN preload p ON p.fid = f.fid,
                user_history uh,
                users u
           WHERE uh.uid = u.uid AND 
                u.listening = true AND
                time_played IS NOT NULL AND 
                uh.id_type = 'f' AND
                uh.id = f.fid
           GROUP BY f.fid, title, sha512, cued, uh.time_played
           ORDER BY uh.time_played DESC
           LIMIT """+str(limit)+""" OFFSET """+str(start)
    # print "Q:<<<%s>>>" % q

    history_res = cache_get_results_assoc(q)

    sql = """SELECT count(DISTINCT uh.time_played) AS total
             FROM user_history uh,
                  users u,
                  files f
             WHERE uh.uid = u.uid AND 
                   u.listening = true AND
                   time_played IS NOT NULL AND 
                   uh.id_type = 'f' AND
                   uh.id = f.fid"""

    total = cache_get_assoc(sql)
    total = total['total']

    if history_res:
        results = []

    already_present_fids = []
    for p in history_res:
        # print "P:", p
        results.append(convert_res_to_dict(p))

    # fixed_results, total = do_search(q, start, limit, filter_by, return_total=True)
    print "RUNNING TIME:", datetime.datetime.now() - start_time
    print "total:", total
    print  'Content-Range','%s-%s/%s' % (start, end, total)
    headers.add("Accept-Ranges", "items")
    headers.add('Content-Range','%s-%s/%s' % (start, end, total) )
    headers.add("Range-Unit", "items")
    headers.add("Content-Type", mimetype)

    results_json = json_dump(results)

    response = Response(results_json, status=status, 
                        mimetype=mimetype, headers=headers, 
                        direct_passthrough=True)
    response.cache_control.public = True
    response.cache_control.max_age = 0
    response.last_modified = int(time.time())
    response.expires=int( time.time() )
    response.make_conditional(request)
    # print "MADE IT", 
    # print "results:", results
    # print "results_json:",results_json

    return response


@app.route('/real-history-data/', methods=['GET'])
def real_history_data():
    sql = """SELECT id, id_type, 
                    string_agg(
                      to_char(time_played, 'YYYY-MM-DD HH24:MI:SS'), 
                      ','
                    ) AS times_played,
                    string_agg(to_char(uh.uid, '999'), ',') AS uids,
                    to_char(date_played, 'YYYY-MM-DD') AS date_played_str
             FROM user_history uh, users u
             WHERE listening = true AND u.uid = uh.uid
             GROUP BY id, id_type, date_played 
             ORDER BY times_played DESC 
             LIMIT 10"""

    history = cache_get_results_assoc(sql)
    results = []
    for h in history:
        results.append(dict(h))
    return json_dump(results)


@cache.memoize(timeout=30)
def cache_get_results_assoc(sql, args=None):
    print "FETCHING"
    return get_results_assoc(sql, args)

@cache.memoize(timeout=30)
def cache_get_assoc(sql, args=None):
    print "FETCHING"
    return get_assoc(sql, args)


@app.route("/preload", methods=['GET', 'POST'])
def preload():
    headers = Headers()
    start_time = datetime.datetime.now()
    # convert_res_to_dict
    """
    HTTP/1.1 206 Partial Content
    Accept-Ranges: items
    Content-Range: 0-24/100
    Range-Unit: items
    Content-Type: application/json"""
    results = None
    q = request.args.get("q","")
    start, limit, end = get_start_limit(True)
    print "start:%s limit:%s end:%s" % (start, limit, end)
    filter_by=get_filter_by()
    status = 206
    mimetype = "application/json"
    cachetimout = 60

    order_by = "plid, artists, title"

    if request.args.get("o") == "plid":
        order_by = "plid"

    print "LIMIT:%s" % limit

    sql = """SELECT uid 
             FROM users 
             WHERE listening = true 
             ORDER BY last_time_cued"""


      # row_number()

    """
    SELECT row_number() OVER(ORDER BY plid) % 9 + 1 AS pos, * from preload;"""

    q = """SELECT DISTINCT row_number() OVER(ORDER BY plid) AS pos, 
                row_number() OVER ( PARTITION BY uid ORDER BY uid) AS pos_order,
                p.plid, p.reason, f.fid, title, sha512,
                           p.fid AS cued,
                           string_agg(DISTINCT a.artist, ',') 
                                        AS artists,
                           f.fid AS id, 'f' AS id_type,
                           CASE reason 
                               WHEN 'From search' THEN 1
                               ELSE 2
                           END AS reason_order
           FROM preload p,
                files f
                LEFT JOIN file_artists fa ON fa.fid = f.fid
                LEFT JOIN artists a ON a.aid = fa.aid
           WHERE p.fid = f.fid
           GROUP BY p.plid, f.fid, title, sha512, cued, id, id_type, p.reason, p.uid
           ORDER BY reason_order, pos_order, plid
           LIMIT """+str(limit)+""" OFFSET """+str(start)
   
    print "Q:<<<%s>>>" % q

    preload = get_results_assoc(q)

    print "made it 1"

    total = cache_get_assoc("""SELECT count(*) AS total
                               FROM preload p""")
    total = total['total']

    if preload:
        results = []

    already_present_fids = []
    for p in preload:
        print "P:", p
        results.append(convert_res_to_dict(p))


    # fixed_results, total = do_search(q, start, limit, filter_by, return_total=True)
    print "RUNNING TIME:", datetime.datetime.now() - start_time
    print "total:", total
    print  'Content-Range','%s-%s/%s' % (start, end, total)
    headers.add("Accept-Ranges", "items")
    headers.add('Content-Range','%s-%s/%s' % (start, end, total) )
    headers.add("Range-Unit", "items")
    headers.add("Content-Type", mimetype)

    results_json = json_dump(results)

    response = Response(results_json, status=status, 
                        mimetype=mimetype, headers=headers, 
                        direct_passthrough=True)
    response.cache_control.public = True
    response.cache_control.max_age = 10
    response.last_modified = int(time.time())
    response.expires=int( time.time() + 10 )
    response.make_conditional(request)
    print "MADE IT", 
    # print "results:", results
    # print "results_json:",results_json

    return response

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

@app.route('/set-title/', methods=['GET'])
def set_file_title():
    title = request.args.get('title')
    fid = request.args.get('fid')

    file_info = get_assoc("""UPDATE files 
                             SET title = %s 
                             WHERE fid = %s
                             RETURNING *""", (title, fid))

    if not file_info:
        return json_dump({"result": "failure"})

    reload_playing(fid)

    return json_dump({
      "result": "success",
      "file_info": dict(file_info)
    })

@app.route('/podcasts/', methods=['GET'])
def get_podcasts():
    podcasts = get_results_assoc("""SELECT * 
                                    FROM netcasts 
                                    ORDER BY netcast_name""")
    podcast_data = []
    for p in podcasts:
        podcast_data.append(dict(p))
    return json_dump(podcast_data)

@app.route("/add-rss-feed/", methods=['GET'])
def add_rss_feed():
    url = request.args.get("url")
    if not url:
      return json_dump({})
    netcast = Netcast(rss_url=url, insert=True)
    return get_episodes(netcast.nid)

@app.route("/feed-data/<nid>", methods=['GET'])
def get_episodes(nid):
    episodes = get_results_assoc("""SELECT *
                                    FROM netcast_episodes
                                    WHERE nid = %s
                                    ORDER BY pub_date DESC
                                    LIMIT 10""", (nid, ))

    subscribers = get_results_assoc("""SELECT u.uid, u.uname, ns.uid AS subscribed
                                       FROM users u
                                            LEFT JOIN netcast_subscribers ns ON
                                                      ns.uid = u.uid AND ns.nid = %s
                                       WHERE listening = true
                                       ORDER BY admin DESC, uname""", 
                                       (nid, ))

    res_data = {
        "episodes": [],
        "subscribers": [],
    }

    for s in subscribers:
      _s = dict(s)
      _s['subscribed'] = bool(s['subscribed'])
      res_data['subscribers'].append(_s)

    for ep in episodes:
      episode = dict(ep)
      heard_by = get_results_assoc("""SELECT DISTINCT nle.uid, u.uname
                                      FROM netcast_listend_episodes nle,
                                           users u
                                      WHERE u.uid = nle.uid AND
                                            nle.eid = %s
      """, (ep['eid'],))
      episode['heard_by'] = []
      for h in heard_by:
          episode['heard_by'].append(dict(h))
      res_data['episodes'].append(episode)

    return json_dump(res_data)

@app.route("/stream/<fid>/")
def stream(fid):
    print "STREAM:", fid
    
    locations = get_results_assoc("""SELECT dirname, basename
                                     FROM file_locations fl
                                     WHERE fid = %s""", (fid, ))

    print "LOCATIONS:",locations

    location = ""
    mimetype = "x-download"
    for l in locations:
        print "L:",l
        path = os.path.join(l['dirname'], l['basename'])
        print "path:", path
        root, ext = os.path.split(l['basename'])
        if os.path.exists(path):
            print "exists"
            location = path
            lext = ext.lower()
            if lext == '.mp3':
                mimetype = "audio/mpeg"
            

    return send_file(location, mimetype=mimetype, as_attachment=False,
                     attachment_filename=None, add_etags=False, 
                     cache_timeout=1, conditional=False)

@app.route('/stream-netcast/<eid>/')
def stream_netcast(eid):
    print "STREAM:", eid
    
    locations = get_results_assoc("""SELECT local_file, episode_url
                                     FROM netcast_episodes
                                     WHERE eid = %s""", (eid, ))

    print "LOCATIONS:",locations

    location = ""
    mimetype = "x-download"
    for l in locations:
        print "L:",l
        path = os.path.join(l['local_file'])
        print "path:", path
        root, ext = os.path.split(l['local_file'])
        if os.path.exists(path):
            print "exists"
            location = path
            lext = ext.lower()
            if lext == '.mp3':
                mimetype = "audio/mpeg"
            
    if not location:
        for l in locations:
            print "REDIRECTING"
            return redirect(l['episode_url'])

    return send_file(location, mimetype=mimetype, as_attachment=False,
                     attachment_filename=None, add_etags=False, 
                     cache_timeout=1, conditional=False)

@app.route("/stream-mp4/<fid>.mp4")
def stream_mp4(fid):
    print ("STERAM MP4", fid)
    location = "/home/erm/tmp/test-video/out.mp4"
    mimetype = "video/mp4"

    print ("HEADERS:", request.headers)

    return send_file(location, mimetype=mimetype, as_attachment=False,
                     attachment_filename=None, add_etags=False, 
                     cache_timeout=1, conditional=False)

@app.route("/subscribe/<nid>/<uid>/<subscribed>", methods=['GET'])
def subscribe(nid, uid, subscribed):
    nid = int(nid)
    uid = int(uid)
    subscribed = subscribed == 'true'

    print "nid:", nid
    print "uid:", uid
    print "subscribed:", subscribed

    if subscribed:
        q = """INSERT INTO netcast_listend_episodes (uid, eid)
                             SELECT '"""+str(uid)+"""', ne.eid
                             FROM netcast_episodes ne
                                  LEFT JOIN netcast_listend_episodes nle ON
                                            nle.eid = ne.eid AND nle.uid = %s
                             WHERE ne.nid = %s AND
                                   nle.eid IS NULL"""
        query(q, (uid, nid))
        query("""INSERT INTO netcast_subscribers (nid, uid) 
                 VALUES(%s, %s)""",
              (nid, uid))
    else:
        query("""DELETE FROM netcast_subscribers WHERE nid = %s AND uid = %s""",
              (nid, uid))
    query("COMMIT")

    return get_episodes(nid)
    return json_dump({
        "works": "ok",
        "nid": nid,
        "uid": uid,
        "subscribed": subscribed
    })


# users
@app.route("/users/", methods=['GET'])
def users():
    sql = """SELECT uid, uname, listening, selected, admin 
             FROM users
             ORDER BY admin DESC, uname"""
    users = get_results_assoc(sql)
    results = []
    for user in users:
       results.append(dict(user))
    return json_dump(results)

@app.route("/listening/<uid>/<state>/", methods=["GET"])
@app.route("/listening/<uid>/<state>", methods=["GET"])
def listening(uid, state):
    cache.clear()
    listening = False
    if state.lower() == 'true':
        listening = True

    uid = int(uid)
    sql = """UPDATE users SET listening = %s WHERE uid = %s"""
    query(sql, (listening, uid))
    if listening:
        sql = """INSERT INTO preload (fid, uid, reason)
                 SELECT pc.fid, pc.uid, string_agg(pc.reason, ',') 
                 FROM preload_cache pc
                      LEFT JOIN preload p ON pc.fid = p.fid
                 WHERE pc.uid = %s AND 
                       p.fid IS NULL
                 GROUP BY pc.fid, pc.uid"""
        query(sql, (uid,))
        sql = """DELETE FROM preload_cache WHERE uid = %s"""
        query(sql, (uid,))
    else:
        sql = """INSERT INTO preload_cache (fid, uid, reason)
                 SELECT p.fid, p.uid, p.reason
                 FROM preload p
                 WHERE p.uid = %s"""
        query(sql, (uid,))
        sql = """DELETE FROM preload WHERE uid = %s"""
        query(sql, (uid,))
    return users()

@app.route("/devices/", methods=["GET"])
@app.route("/devices", methods=["GET"])
@cache.cached(timeout=60)
def devices():
    update_devices()
    sql = """SELECT * 
             FROM devices 
             WHERE mounted = true 
             ORDER BY mounted_on"""

    devices = get_results_assoc(sql)
    results = []
    for device in devices:
        _device = dict(device)
        _device['writable'] = os.access(device['mounted_on'], os.W_OK)
        results.append(_device)
    return json_dump(results)

@app.route("/copy-to/<flid>/<device_id>/", methods=["GET"])
@app.route("/copy-to/<flid>/<device_id>", methods=["GET"])
def copy_to(flid, device_id):
    cache.clear()
    print "1"
    sql = """SELECT *
             FROM file_locations
             WHERE flid = %s"""
    location = get_assoc(sql, (flid, ))

    sql = """SELECT * 
             FROM devices
             WHERE device_id = %s"""

    device = get_assoc(sql, (device_id, ))
    if int(device_id) == int(location['device_id']):
        return json_dump({"result":"FAIL",
                          "error": "File already exists on %s" % (
                                    device['label'],)})


    dst_dir = device['mounted_on']
    if not os.access(dst_dir, os.W_OK):
        return json_dump({"result":"FAIL",
                          "error": "Unable to write to folder %s" % (
                                    dst_dir,)})

    src = os.path.join(location['dirname'], location['basename'])
    dst = os.path.join(dst_dir, location['basename'])
    print "dst:", dst
    print "%s => %s" % (src, dst)

    if os.path.exists(dst):
        print "3"
        locations = locations_for_fid(location['fid'])
        return json_dump({"result": "OK",
                          "locations": locations })

    shutil.copy2(src, dst)
    scan_file(filename=dst)
    locations = locations_for_fid(location['fid'])
    print "4"
    return json_dump({"result": "OK",
                      "locations": locations })

@app.route("/netcast-unlistened-episodes/", methods=["GET"])
@app.route("/netcast-unlistened-episodes", methods=["GET"])
def netcast_unlistened_episodes():

    sql = """SELECT DISTINCT ne.eid, ne.episode_title, ne.episode_url, 
                             ne.local_file
             FROM users u,
                  netcast_episodes ne
                  LEFT JOIN netcast_subscribers ns 
                            ON ns.nid = ne.nid
                  LEFT JOIN netcast_listend_episodes nle 
                            ON nle.eid = ne.eid AND
                               nle.uid = ns.uid
             WHERE nle.uid IS NULL AND
                   ns.nid = ne.nid AND
                   ns.uid = u.uid AND
                   u.listening = true"""

    res = cache_get_results_assoc(sql)
    results = []
    for r in res:
        results.append(dict(r))
    return json_dump(results)


def start_worker(*args):
    print "STARTING WORKER"
    socketio.run(app, port=5050, host="0.0.0.0")

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

last_time_response = {}

def on_time_status(player, pos_int, dur_int, left_int, decimal, 
                   pos_str, dur_str, left_str, percent):
    global last_time_response
    # <Player object at 0x7fcc41d8fe60 (player+Player at 0x2c34b00)>, 51219185000, 199365000000, 148145815000, 0.2569116193915682, '0:51', '3:19', '2:28', '25.69%'
    response = {
        "pos_int": pos_int,
        "dur_int": dur_int,
        "dur_str": dur_str,
        "left_str": left_str,
        "percent": percent,
        "decimal": decimal,
        "left_int": left_int,
        "pos_str": pos_str,
        "dur_str": dur_str,
    }
    if response == last_time_response:
        return
    last_time_response = response
    # print "on_time_status"
    socketio.emit('time-status', response, namespace="/fmp")

def emit_mark_as_played(update_data):
    """
    {
        "mark-as-played": percent_played,
        "res": res
    }"""
    socketio.emit('mark-as-played', update_data, namespace="/fmp")


def on_state_change(_player, state):
    response = "PAUSED"
    if state == PLAYING:
        response = "PLAYING"
    socketio.emit('state-changed', response,  namespace="/fmp")

def emit_status(_playing=None):
    print "emit_status:", _playing
    global playing, player
    # print "PLAYING",playing.to_dict()
    
    player_dict = player.to_dict()
    playing_dict = playing.to_full_dict()

    extended = deepcopy(player_dict)
    extended.update(deepcopy(playing_dict))

    extended['history'] = []
    if playing_dict.get('fid'):
      extended['history'] = file_history(playing_dict['fid'], 'f')
    elif playing_dict.get('eid'):
      extended['history'] = file_history(playing_dict['eid'], 'e')

    if not extended.get('artists'):
      extended['artists'] = [{'artist':extended['artist_title']}]

    if not extended.get('genres'):
      extended['genres'] = []

    extended = convert_res_to_dict(extended)

    socketio.emit('status', extended,  namespace="/fmp")

@socketio.on('status', namespace='/fmp')
def socket_status(*args, **kwargs):
    print "socket_status"
    emit_status()

def start_in_thread():
    print "START CALLED!"
    t = threading.Thread(target=start_worker, args=(0,))
    threads.append(t)
    t.start()
    _trigger_loop()
    player.connect("time-status", on_time_status)
    player.connect("state-changed", on_state_change)

def start():
    print "START()"
    start_worker()

def call_test():
    print "CALL TEST COMPLETED"

def quit():
    kill_threads()


if __name__ == "__main__":
    worker()
    # app.run(debug=False, host='0.0.0.0', port=5050)

