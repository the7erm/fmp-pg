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

from __init__ import *
from flask import Flask
from flask import request
from flask import redirect
from flask import session
from flask import jsonify
from flask import send_file

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
import os
from copy import deepcopy

# from bson import json_util
import json

from lib.player import PLAYING

import threading
import time

from flask import render_template
import lib.fobj as fobj
from lib.rating_utils import rate as simple_rate
from lib.local_file_fobj import get_words_from_string, Local_File

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

def get_extended():
    global player, playing
    extended = player.to_dict()
    extended.update(playing.to_full_dict())
    return extended;

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

    result = get_results_assoc("""SELECT artist 
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
        result = get_results_assoc("""SELECT genre 
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
        result = get_results_assoc("""SELECT basename 
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

    result = get_results_assoc("""SELECT aid, artist 
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

    result = get_results_assoc("""SELECT gid, genre 
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

    result = get_results_assoc("""SELECT alid, album_name 
                                  FROM albums 
                                  WHERE album_name ~* %s
                                  ORDER BY album_name
                                  LIMIT 10""", (q,))
    response = []
    for r in result:
        response.append({"alid": r['alid'], "album_name": r['album_name']})

    return json.dumps(response)

def file_history(_id, id_type):
    history_res = get_results_assoc("""SELECT uh.*, uname
                                   FROM user_history uh, users u
                                   WHERE uh.uid = u.uid AND 
                                         u.listening = true AND
                                         time_played IS NOT NULL AND
                                         uh.id = %s AND 
                                         uh.id_type = %s
                                   ORDER BY time_played DESC, 
                                            admin DESC, uname""",
                                   (_id, id_type))
    results = []
    for h in history_res:
        h = dict(h)
        h['time_played'] = h['time_played'].isoformat()
        h['date_played'] = h['date_played'].isoformat()
        results.append(h)
    return results

@app.route("/status/")
def status():
    print "STATUS"
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

def listeners_info_for_fid(fid):
    query = """SELECT uname, usi.*, f.sha512
               FROM user_song_info usi, users u, files f
               WHERE usi.fid = %s AND u.uid = usi.uid AND u.listening = true AND
                     f.fid = usi.fid
               ORDER BY admin DESC, uname ASC
    """
    # print "query:%s" % query
    return convert_to_dict(get_results_assoc(query, (fid,)))

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

def get_search_results(q="", start=0, limit=20, filter_by="all"):
    start = int(start)
    limit = int(limit)
    # print "Q:",q
    """
    SELECT DISTINCT f.fid, dirname, basename, title,
                                        sha512, artist, p.fid AS cued,
                                        f.fid AS id, 'f' AS id_type
                        FROM files f 
                             LEFT JOIN preload p ON p.fid = f.fid
                             LEFT JOIN file_artists fa ON fa.fid = f.fid
                             LEFT JOIN artists a ON a.aid = fa.aid,
                             file_locations fl
                        WHERE fl.fid = f.fid
                        ORDER BY artist, title"""
    no_words_query = """SELECT DISTINCT f.fid, title, sha512, p.fid AS cued,
                                        f.fid AS id, 'f' AS id_type, artist
                        FROM files f 
                             LEFT JOIN preload p ON p.fid = f.fid
                             LEFT JOIN file_artists fa ON fa.fid = f.fid
                             LEFT JOIN artists a ON a.aid = fa.aid
                        ORDER BY artist, title"""

    no_words_rating_query = """SELECT DISTINCT f.fid, title, sha512,  
                                               f.fid, p.fid AS cued, artist,
                                               f.fid AS id, 'f' AS id_type
                               FROM files f 
                                    LEFT JOIN preload p ON p.fid = f.fid
                                    LEFT JOIN file_artists fa ON fa.fid = f.fid
                                    LEFT JOIN artists a ON a.aid = fa.aid,
                                    user_song_info usi
                               WHERE rating = %s AND usi.fid = f.fid AND
                                     usi.uid IN (SELECT uid 
                                                 FROM users 
                                                 WHERE listening = true)
                               ORDER BY artist, title"""


    query = """SELECT DISTINCT f.fid, title, sha512, artist,
                               p.fid AS cued, ts_rank(tsv, query),
                               f.fid AS id, 'f' AS id_type
               FROM files f
                    LEFT JOIN preload p ON p.fid = f.fid
                    LEFT JOIN file_artists fa ON fa.fid = f.fid
                    LEFT JOIN artists a ON a.aid = fa.aid,
                    keywords kw,
                    plainto_tsquery('english', %s) query
               WHERE kw.fid = f.fid AND
                     tsv @@ query
               ORDER BY ts_rank DESC, artist, title"""

    rating_query = """SELECT DISTINCT f.fid, title, sha512, artist,
                               p.fid AS cued, ts_rank(tsv, query),
                               f.fid AS id, 'f' AS id_type
                      FROM files f
                           LEFT JOIN preload p ON p.fid = f.fid
                           LEFT JOIN file_artists fa ON fa.fid = f.fid
                           LEFT JOIN artists a ON a.aid = fa.aid,
                           keywords kw,
                           plainto_tsquery('english', %s) query,
                           user_song_info usi,
                      WHERE kw.fid = f.fid AND tsv @@ query AND 
                            usi.rating = %s AND
                            f.fid = usi.fid AND
                            usi.uid IN (SELECT uid 
                                        FROM users 
                                        WHERE listening = true)
                      ORDER BY ts_rank DESC, artist, title"""

    rating_re = re.compile("rating\:(\d+)")
    rating_match = rating_re.match(q)
    rating = -1
    if rating_match:
        rating = rating_match.group(1)
        q = q.replace("rating:%s" % rating, "").strip()


    if not q:
        query = no_words_query
        if rating != -1:
            query = no_words_rating_query

    # """+limit+""" OFFSET """+offset
    query = "%s LIMIT %d OFFSET %d" % (query, limit, start)
    # print "QUERY:%s" % query
    results = []
    
    try:
        args = (q,)
        if rating != -1:
            if q:
                args = (q, rating)
                query = rating_query
            else:
                args = (rating,)
        for r in get_results_assoc(query, args):
            # f = fobj.get_fobj(**r)
            #fd = f.to_dict()
            # fd.cued = r.cued
            rdict = dict(r)
            results.append(rdict)
    except psycopg2.IntegrityError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.IntegrityError:",err
    except psycopg2.InternalError, err:
        query("COMMIT;")
        print "(flask_server) psycopg2.InternalError:",err
    return results

def locations_for_fid(fid):
    locations = get_results_assoc("""SELECT dirname, basename
                                     FROM file_locations
                                     WHERE fid = %s
                                     ORDER BY dirname, basename""", (fid,))

    results = []
    for l in locations:
        path = os.path.join(l['dirname'], l['basename'])
        if os.path.exists(path):
            results.append({
                "dirname": l['dirname'],
                "basename": l['basename'],
            })

    return results



def convert_res_to_dict(r):
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
    rdict['dups'] = []
    if r['sha512']:
        dups = get_results_assoc("""SELECT DISTINCT f.fid, dirname, basename, title,
                                     sha512, p.fid AS cued
                                    FROM files f 
                                         LEFT JOIN preload p ON p.fid = f.fid,
                                         file_locations fl
                                    WHERE f.sha512 = %s AND f.fid != %s AND
                                          fl.fid = f.fid""", 
                                    (r['sha512'], fid))
        for d in dups:
            rdict['dups'].append(convert_res_to_dict(d))

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
    

def json_dump(obj):
    return json.dumps(obj, default=json_obj_handler) or "{};"

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
    results = get_search_results(q, start=start, limit=limit, filter_by=filter_by)
    print "end:", time.time() - start_time
    return json_dump(results)

# 

cache_data = {}
def do_search(q, start, limit, filter_by):
    print "DO SEARCH"
    start_time = datetime.datetime.now()
    results = get_search_results(q, start=start, limit=limit, filter_by=filter_by)
    fixed_results = []
    already_present_fids = []
    for r in results:
        if r['fid'] in already_present_fids:
            continue
        already_present_fids.append(r['fid'])
        fixed_results.append(convert_res_to_dict(r))

    json_data = json_dump(fixed_results)
    print "="*20
    print "fetch time:",datetime.datetime.now() - start_time
    return json_data

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
    start_time = datetime.datetime.now()
    # convert_res_to_dict
    results = None
    q = request.args.get("q","")
    start, limit = get_start_limit()
    filter_by=get_filter_by()

    print "LIMIT:%s" % limit
    fixed_results = do_search(q, start, limit, filter_by)
    #t = threading.Thread(target=cache_some_results, args=(q, int(start)+int(limit), 
    #                                                  limit, filter_by))
    # threads.append(t)
    # t.start()
    print "RUNNING TIME:", datetime.datetime.now() - start_time
    return fixed_results


def get_start_limit():
    start = "%s" % request.args.get("s", "0")
    limit = "%s" % request.args.get("l", "10")
    start = int(start)
    limit = int(limit)
    if not start:
        start = 0
    if not limit:
        limit = 10
    return start, limit

@app.route('/cue/', methods=['GET', 'POST'])
def cue():
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
    print "dta:",dta
    return json_dump(dta[0])


@app.route("/rate/<usid>/<fid>/<uid>/<rating>", methods=['GET', 'POST', 'PUT'])
def rate(usid, fid, uid, rating):
    global playing
    print "RATE:", usid, fid, uid, rating
    # playing.rate(uid=uid, rating=rafidting)
    if hasattr(playing, 'fid') and int(playing.fid) == int(fid):
        print "**************** RATING PLAYING FILE **************"
        dta = playing.rate(uid=uid, rating=rating)
        return json_first(dta)
        
    dta = simple_rate(usid=usid, fid=fid, uid=uid, rating=rating)
    return json_first(dta)

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
    start, limit = get_start_limit()
    offset = "%d" % start
    limit = "%d" % limit
    # LIMIT %d OFFSET %d

    """
                        SELECT DISTINCT f.fid, dirname, basename, title,
                                        sha512, artist, p.fid AS cued,
                                        f.fid AS id, 'f' AS id_type
                        FROM files f 
                             LEFT JOIN preload p ON p.fid = f.fid
                             LEFT JOIN file_artists fa ON fa.fid = f.fid
                             LEFT JOIN artists a ON a.aid = fa.aid,
                             file_locations fl
                        WHERE fl.fid = f.fid
                        ORDER BY artist, title"""
    history_res = get_results_assoc("""SELECT uh.*, uname,
                                              f.fid, title,
                                              sha512,
                                              p.fid AS cued
                                       FROM user_history uh,
                                            users u,
                                            files f
                                            LEFT JOIN preload p ON p.fid = f.fid
                                       WHERE uh.uid = u.uid AND 
                                             u.listening = true AND
                                             time_played IS NOT NULL AND 
                                             uh.id_type = 'f' AND
                                             uh.id = f.fid
                                       ORDER BY uh.time_played DESC, admin DESC, uname
                                       LIMIT """+limit+""" OFFSET """+offset)

    results = []
    for h in history_res:
        results.append(convert_res_to_dict(h))

    return json_dump(results)

@app.route("/preload", methods=['GET', 'POST'])
def preload():
    start, limit = get_start_limit()
    start = int(start)
    limit = int(limit)
    end = start + limit
    preload = get_results_assoc("""SELECT DISTINCT f.fid, artist, title,
                                        sha512, p.fid AS cued, artist,
                                        f.fid AS id, 'f' AS id_type
                                   FROM files f
                                        LEFT JOIN file_artists fa ON fa.fid = f.fid
                                        LEFT JOIN artists a ON a.aid = fa.aid,
                                        preload p
                                   WHERE p.fid = f.fid
                                   ORDER BY artist, title""")
    results = []
    already_present_fids = []
    idx = -1;
    for p in preload:
        if p['fid'] in already_present_fids:
            print "ALREADY PROCESSED", p['fid']
            continue
        idx += 1
        if idx < start or idx > end:
            continue
        already_present_fids.append(p['fid'])
        results.append(convert_res_to_dict(p))

    return json_dump(results)

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

