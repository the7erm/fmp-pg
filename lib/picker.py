#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# picker.py -- Pick songs.
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


import gtk
from __init__ import *
from random import shuffle
from local_file_fobj import Local_File
from local_file_fobj import sanity_check
from wait_util import wait
from excemptions import CreationFailed
import sys
import time
import traceback
from math import ceil, floor

global populate_locked, dont_pick_created
dont_pick_created = False
populate_locked = False

# CREATE TEMPORARY TABLE IF NOT EXISTS dont_pick (fid SERIAL);
# CREATE UNIQUE INDEX fid_index ON dont_pick (fid);
# CREATE RULE "dont_pick_on_duplicate_ignore" AS ON INSERT TO "dont_pick"
#  WHERE EXISTS(SELECT 1 FROM dont_pick 
#                WHERE (fid)=(NEW.fid))
#  DO INSTEAD NOTHING;
# INSERT INTO dont_pick (fid) SELECT fid FROM user_song_info WHERE rating = 0 AND uid = 1;
# DROP RULE "my_table_on_duplicate_ignore" ON "my_table";



def create_dont_pick():
    global dont_pick_created

    if dont_pick_created:
        # print "dont_pick_created:",dont_pick_created
        return

    dont_pick_created = True
    query("DROP TABLE dont_pick")
    query("""CREATE TABLE 
                IF NOT EXISTS 
                    dont_pick (fid SERIAL, reason text, reason_value text)""")
    query("CREATE UNIQUE INDEX dont_pick_fid_index ON dont_pick (fid)")
    query("""CREATE RULE "dont_pick_on_duplicate_ignore" AS ON 
                INSERT TO "dont_pick" 
                WHERE EXISTS(SELECT 1 FROM dont_pick WHERE (fid)=(NEW.fid)) 
                DO INSTEAD NOTHING;""")

def create_preload():
    # query("CREATE TABLE IF NOT EXISTS preload (fid SERIAL, uid SERIAL, reason text)")
    # query("CREATE UNIQUE INDEX preload_fid_index ON preload (fid)", ())
    # query('CREATE RULE "preload_on_duplicate_ignore" AS ON INSERT TO "preload"  WHERE EXISTS(SELECT 1 FROM preload WHERE (fid)=(NEW.fid)) DO INSTEAD NOTHING;', ())
    return

def associate_gernes():
    print "associate_gernes 1"
    undefined = get_assoc("SELECT * FROM genres WHERE genre = %s",('[undefined]',))
    if not undefined:
        print "associate_gernes 2"
        undefined = get_assoc("""INSERT INTO genres (genre, enabled) 
                                 VALUES(%s, true)
                                 RETURNING *""",("[undefined]",))
        print "associate_gernes 2.1"

    print "associate_gernes 3"
    query("""INSERT INTO file_genres (fid, gid) 
             SELECT f.fid, %s 
             FROM files f 
             LEFT JOIN file_genres fg ON fg.fid = f.fid 
             WHERE fg.fid IS NULL""",(undefined['gid'],))

def insert_duplicate_files_into_dont_pick():
  query("""INSERT INTO dont_pick (fid, reason) 
                 SELECT DISTINCT fid, 'sha512 already in preload'
                 FROM files 
                 WHERE sha512 IN (SELECT sha512 
                                  FROM files f, preload p 
                                  WHERE p.fid = f.fid)""")

def populate_dont_pick():
    associate_gernes()
    query("TRUNCATE dont_pick")
    query("""INSERT INTO dont_pick (fid, reason) 
                SELECT fid, 'already in preload' 
                FROM preload""")
    # insert all disabled genres into dont_pick
    query("""INSERT INTO dont_pick (fid, reason) 
                SELECT DISTINCT(f.fid), 'disabled genre' 
                FROM files f LEFT JOIN dont_pick dp ON dp.fid = f.fid, 
                     genres g, 
                     file_genres fg 
                WHERE fg.gid = g.gid AND 
                      g.enabled = false AND 
                      f.fid = fg.fid AND 
                      dp.fid IS NULL""")
    # remove all 'enabled' genres from dont_pick
    query("""DELETE FROM dont_pick WHERE fid IN (
                SELECT DISTINCT (f.fid) 
                FROM files f, genres g, file_genres fg, dont_pick dp
                WHERE f.fid = fg.fid AND 
                      fg.gid = g.gid AND
                      dp.fid = f.fid AND
                      g.enabled = true)""")

    insert_duplicate_files_into_dont_pick()
    sql = """SELECT uid 
             FROM users 
             WHERE listening = true"""
    listeners = get_results_assoc(sql, ())

    if listeners:
        total_to_remove = get_assoc(
            """SELECT FLOOR(count(DISTINCT fid) * 0.01) AS total 
               FROM file_genres fg, genres g 
               WHERE g.gid = fg.gid AND g.enabled = true""")

        total_artists_to_remove = get_assoc(
            """SELECT FLOOR(count(DISTINCT aid) * 0.01) AS total 
               FROM file_artists fa, file_genres fg, genres g 
               WHERE g.gid = fg.gid AND g.enabled = true AND fa.fid = fg.fid""")

        if total_to_remove.has_key('total'):
            total_to_remove = str(total_to_remove['total'])
        else:
            total_to_remove = "0"
        
        if total_artists_to_remove.has_key('total'):
            total_artists_to_remove = str(total_artists_to_remove['total'])
        else:
            total_artists_to_remove = "0"

        for l in listeners:
            query("""INSERT INTO dont_pick (fid, reason, reason_value) 
                        SELECT DISTINCT fid, 'rated 0', uid 
                        FROM user_song_info 
                        WHERE rating = 0 AND uid = %s""",
                     (l['uid'],))

            # Add recently played files.
            query("""INSERT INTO dont_pick (fid, reason, reason_value) 
                        SELECT DISTINCT fid, 'recently played', ultp 
                        FROM user_song_info 
                        WHERE uid = %s AND ultp IS NOT NULL 
                        ORDER BY ultp DESC LIMIT """+total_to_remove, 
                     (l['uid'],))

            # Add recently played artists
            # Don't add aid column
            query("""INSERT INTO dont_pick (fid, reason) 
                     SELECT DISTINCT fid, 'Recently played artist' 
                     FROM file_artists 
                     WHERE aid IN (SELECT aid 
                                   FROM file_artists fa, user_song_info u 
                                   WHERE fa.fid = u.fid AND ultp IS NOT NULL AND 
                                         u.uid = %s 
                                   ORDER BY ultp DESC 
                                   LIMIT """+total_artists_to_remove+")", 
                     (l['uid'],))

    query("""INSERT INTO dont_pick (fid, reason) 
                SELECT DISTINCT fid, 'artist in preload' 
                FROM file_artists 
                WHERE aid IN (SELECT DISTINCT aid 
                              FROM file_artists fa 
                              WHERE fid IN (SELECT DISTINCT fid 
                                            FROM preload 
                                            WHERE fid NOT IN (SELECT fid 
                                                              FROM dont_pick)
                                           )
                             )""")
    # for r in dont_pick:
    #    print "don't pick:",r

    sql = """SELECT fid FROM preload"""
    fids = get_results_assoc(sql)
    for fid in fids:
        print "INSERTING"
        insert_into_dont_pick(fid['fid'])

    time.sleep(2)


def remove_missing_files_from_preload():
  files = get_results_assoc("""SELECT p.fid, dirname, basename, p.uid
                               FROM preload p, file_locations fl
                               WHERE fl.fid = p.fid""")

  found_fids = []
  missing_fids = []

  for f in files:
      if not os.path.exists(os.path.join(f['dirname'], f['basename'])):
          # print "!"*20,"MISSING","!"*20
          # print "MISSING:", f['fid']
          # query("""DELETE FROM preload WHERE fid = %s""", (f['fid'],))
          missing_fids.append(f['fid'])
      else:
        found_fids.append(f['fid'])

  for fid in missing_fids:
      if fid not in found_fids:
          print "!"*20,"MISSING","!"*20
          print "MISSING:", fid
          query("""DELETE FROM preload WHERE fid = %s""", (fid,))


def populate_preload(uid=None, min_amount=0, max_cue_time=10):
    remove_duplicates_from_preload()
    remove_missing_files_from_preload()
    if not uid or uid is None:
        sql = """SELECT uid FROM users WHERE listening = true"""
        listeners = get_results_assoc(sql, ())
        len_listeners = len(listeners)
        max_cue_time = 10 / len_listeners
        for l in listeners:
            populate_preload(l['uid'], min_amount, max_cue_time)
        return
    # populate_preload_for_uid(uid, min_amount)
    try:
        populate_preload_for_uid(uid, min_amount, max_cue_time)
    except Exception as err:
        print "ERROR!!!! COULD NOT POPULATE PRELOAD"
        print err
        global populate_locked
        populate_locked = False
        traceback.print_exc()
        # populate_preload_for_uid(uid, min_amount)

def fix_bad_scores(uid):
    too_high = get_results_assoc("""SELECT * 
                                    FROM user_song_info 
                                    WHERE true_score > %s AND uid = %s 
                                    LIMIT 1""",(MAX_TRUE_SCORE, uid))

    if too_high:

        q = pg_cur.mogrify("""UPDATE user_song_info 
                              SET true_score = %s, score = %s, rating = %s,
                                  percent_played = %s
                              WHERE true_score > %s AND uid = %s""",
                              (DEFAULT_TRUE_SCORE, DEFAULT_SCORE, DEFAULT_RATING,
                               DEFAULT_PERCENT_PLAYED, MAX_TRUE_SCORE, uid))

        print "q:",q
        query(q)

    
def insert_missing_songs(uid):
    print "inserting missing songs"
    m = pg_cur.mogrify("""SELECT f.fid FROM files f 
                              LEFT JOIN user_song_info usi ON usi.fid = f.fid AND 
                                        usi.uid = %s 
                          WHERE usi.fid IS NULL""", (uid,))

    q = """INSERT INTO user_song_info (fid, uid, rating, score, percent_played, 
                                       true_score) 
                SELECT f.fid, '%s', '%s', '%s', '%s', 
                       '%s' 
                FROM files f 
                WHERE f.fid IN (%s)""" % (uid, DEFAULT_RATING, DEFAULT_SCORE, 
                                          DEFAULT_PERCENT_PLAYED, 
                                          DEFAULT_TRUE_SCORE, m)
    query(q)

def get_true_score_sample(uid, true_score):
    return get_results_assoc(
      """SELECT u.fid, title, true_score, ultp 
         FROM files f, user_song_info u 
              LEFT JOIN dont_pick dp ON dp.fid = u.fid 
         WHERE dp.fid IS NULL AND u.uid = %s AND 
               true_score >= %s AND u.fid = f.fid
         ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                ultp, random() 
         LIMIT 10""", (uid, true_score))

def get_single_from_true_score(uid, true_score):
    return get_assoc(
      """SELECT u.fid, true_score, ultp 
         FROM user_song_info u 
              LEFT JOIN dont_pick dp ON dp.fid = u.fid 
         WHERE dp.fid IS NULL AND u.uid = %s AND 
               true_score >= %s
         ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                ultp, random() 
         LIMIT 1""", (uid, true_score))

def make_true_scores_list():
    scores = [0,5,10,15,20,25,30,35,40,45,50,55,60,65,70,75,80,85,85,90,90,
              95,95]

    # shuffle(scores)

    true_scores = []

    for true_score in scores:
        iter_count = int(ceil((true_score * 0.1) * .5 ))
        if iter_count <= 0:
            iter_count = 1
        print "true_score:", true_score, "iter_count:", iter_count
        for i in range(0, iter_count):
            true_scores.append(str(true_score))

    print "true_scores:", true_scores
    shuffle(true_scores)

    return true_scores

def insert_preload_history_data(preload_data):
    print "PRELOAD DATA:", preload_data
    if preload_data is None:
        return
    """
                                              Table "public.preload_history"
           Column    |           Type           |                            Modifiers                             
        -------------+--------------------------+------------------------------------------------------------------
         phid        | integer                  | not null default nextval('preload_history_phid_seq'::regclass)
         fid         | integer                  | not null default nextval('preload_history_fid_seq'::regclass)
         uid         | integer                  | not null default nextval('preload_history_uid_seq'::regclass)
         reason      | integer                  | not null default nextval('preload_history_reason_seq'::regclass)
         date_qued   | timestamp with time zone | 
         date_played | timestamp with time zone | 
         uhids       | bigint[]                 | 
         plid        | integer                  | not null default nextval('preload_history_plid_seq'::regclass)

    """
    preload_history_data = get_assoc("""INSERT INTO 
                                        preload_history (fid, uid, reason, plid, date_qued)
                                        VALUES          (%s,  %s,  %s,   %s,   NOW())
                                        RETURNING *""",
                                        (preload_data['fid'], 
                                         preload_data['uid'], 
                                         preload_data['reason'], 
                                         preload_data['plid']))
    print "preload_history_data:",
    pprint.pprint(preload_history_data)


def insert_into_preload(msg, fid, uid, reason):
    print msg, get_assoc("SELECT * FROM files WHERE fid = %s",(fid,))
    print "INSERT INTO PRELOAD fid:%s uid:%s reason:%s"  % (fid, uid, reason)
    query("""INSERT INTO preload (fid, uid, reason)
             VALUES (%s, %s, %s)""",
           (fid, uid, reason))
    preload_data = get_assoc("""SELECT *
                                FROM preload
                                WHERE fid = %s AND uid = %s AND reason = %s""", 
                            (fid, uid, reason))
    insert_preload_history_data(preload_data)

def insert_fid_into_preload(fid, uid, reason):
    # seq_info = is_sequential(fid)
    wait()
    seq_info = None
    if seq_info is None:
        insert_into_preload("adding:", fid, uid, reason)
        return

    if 'aid' in seq_info:
        next_file = get_next_file_in_artist_series(seq_info['aid'], uid)
        if next_file:
            fid = next_file['fid']
            reason += " is sequential artist"

    if 'gid' in seq_info:
        print("*****"*20, "GID")
        next_file = get_next_file_in_genre_series(seq_info['gid'], uid)
        if next_file:
          print "NEXT FILE DETECTED"
          fid = next_file['fid']
          reason += " is sequential genre"
        print "NEXT_FILE:", next_file
    insert_into_preload("adding sequential:", fid, uid, reason)
    insert_artists_in_preload_into_dont_pick()
    insert_duplicate_files_into_dont_pick()

def get_next_file_in_artist_series(aid, uid):
    next_file = None  
    # Get the last file played by that artist
    q = """SELECT dirname, basename, ultp
           FROM file_locations fl,
                file_artists fa,
                user_song_info usi
           WHERE usi.fid = fl.fid AND
                 fa.fid = fl.fid AND
                 fa.aid = %s AND
                 usi.uid = %s
           ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END,
                    ultp DESC
           LIMIT 1"""
    last_file = get_assoc(q, (aid, uid))
    if last_file:
        # Get the next artist in the series
        next_file = get_assoc("""SELECT dirname, basename, fl.fid
                                 FROM file_artists fa,
                                      file_locations fl
                                 WHERE dirname >= %s AND
                                       basename > %s AND
                                       fl.fid = fa.fid AND
                                       fa.aid = %s
                                 ORDER BY dirname, basename
                                 LIMIT 1""",
                                 (last_file['dirname'], last_file['basename'],
                                  aid))
        if next_file:
            print "NEXT FILE:", next_file
            return next_file
    # If it's empty, get the first file in the series.
    return get_assoc("""SELECT dirname, basename, ultp, fl.fid
                        FROM file_artists fa,
                             user_song_info usi,
                             file_locations fl
                        WHERE usi.fid = fl.fid AND
                              fa.fid = fl.fid AND
                              fa.aid = %s AND
                              usi.uid = %s
                        ORDER BY dirname, basename
                        LIMIT 1""", (aid, uid))


def get_next_file_in_genre_series(gid, uid):
    insert_artists_in_preload_into_dont_pick()
    print "="*20,"=============================", "="*20
    print "="*20,"GET NEXT FILE IN GENRE SERIES", "="*20
    print "="*20,"=============================", "="*20
    next_file = None
    # Get the last file played in that genre
    print "g1"
    q = """SELECT dirname, basename, ultp
           FROM file_locations fl,
                file_genres fg,
                user_song_info usi
           WHERE usi.fid = fl.fid AND
                 fg.fid = fl.fid AND
                 fg.gid = %(gid)s AND
                 usi.uid = %(uid)s AND
                 usi.fid = fg.fid
           ORDER BY CASE WHEN ultp IS NULL THEN 1 ELSE 0 END,
                    ultp DESC, dirname, basename 
           LIMIT 1"""
    last_file = get_assoc(q, {"gid": gid, "uid": uid})
    print "last_file:", 
    try:
      pprint.pprint(dict(last_file))
    except:
      print last_file

    if last_file is None:
        return None

    print "g2", pg_cur.mogrify(q, {"gid": gid, "uid": uid})
    if last_file:
        print "g2.1 LAST_FILE:", pprint.pprint(last_file)
        # Get the next artist in the series
        q = """SELECT dirname, basename, fl.fid
               FROM file_locations fl,
                    file_genres fg
               WHERE basename > %s AND
                     fl.fid = fg.fid AND
                     fg.gid = %s
               ORDER BY dirname, basename
               LIMIT 1"""
        next_file = get_assoc(q, (last_file['basename'], gid))
        print "g2.2"
        print pg_cur.mogrify(q, (last_file['basename'], gid))
        if next_file:
            print "NEXT FILE:",next_file
            return next_file
    print "g3"
    # If it's empty, get the first file in the series.
    return get_assoc("""SELECT dirname, basename, ultp, fl.fid
                        FROM file_locations fl,
                             file_genres fg,
                             user_song_info usi
                        WHERE usi.fid = fl.fid AND
                              fg.fid = fl.fid AND
                              fg.gid = %s AND
                              usi.uid = %s
                        ORDER BY dirname, basename
                        LIMIT 1""", (gid, uid))


def is_sequential_artist(fid):
    return get_assoc("""SELECT a.aid
                        FROM file_artists fa, artists a 
                        WHERE fid = %s AND 
                              a.aid = fa.aid AND
                              a.seq = true
                        ORDER BY random()
                        LIMIT 1""", 
                        (fid,))


def is_sequential_genre(fid):
    return get_assoc("""SELECT g.gid
                        FROM file_genres fg, genres g 
                        WHERE fg.fid = %s AND 
                              g.gid = fg.gid AND
                              g.seq_genre = true
                        ORDER BY random()
                        LIMIT 1""", 
                        (fid,))


def is_sequential(fid):
    print "is_sequential 1"
    artist_info = is_sequential_artist(fid)
    if artist_info:
        print "*"*60,"ARTIST","*"*60
        return {
            'aid': artist_info['aid']
        }
    print "is_sequential 2"
    genre_info = is_sequential_genre(fid)
    if genre_info:
        print "*"*60,"GENRE","*"*60
        print genre_info
        return {
          'gid': genre_info['gid']
        }
    print "is_sequential 3"
    return None

def insert_artists_in_preload_into_dont_pick():
    sql = """INSERT INTO dont_pick (fid, reason) 
             SELECT DISTINCT fid, 'artist in preload' 
             FROM file_artists 
             WHERE aid IN (SELECT DISTINCT aid 
                           FROM file_artists fa 
                           WHERE fid IN (SELECT DISTINCT p.fid 
                                         FROM preload p 
                                              LEFT JOIN dont_pick dp ON 
                                                        dp.fid = p.fid
                                         WHERE dp.fid IS NULL
                                        )
                          )"""
    query(sql)
    wait()


def get_random_unplayed_sample(uid):
    sql = """SELECT u.fid, u.true_score, ultp 
             FROM user_song_info u  
                  LEFT JOIN dont_pick dp ON dp.fid = u.fid
             WHERE dp.fid IS NULL AND 
                   u.uid = %s AND
                   u.ultp IS NULL
             ORDER BY random() 
             LIMIT 10"""
    return get_results_assoc(sql, (uid,))

def get_single_random_unplayed(uid):
    return get_assoc("""SELECT u.fid, u.true_score, ultp 
                        FROM user_song_info u  
                             LEFT JOIN dont_pick dp ON dp.fid = u.fid
                        WHERE dp.fid IS NULL AND 
                              u.uid = %s AND
                              u.ultp IS NULL
                        ORDER BY random() 
                        LIMIT 1""", 
                        (uid,))


def get_existing_file(uid, true_score):
    file_info = None
    while not file_info:
        file_info = get_single_from_true_score(uid, true_score)

        if not file_info:
            print "nothing for:",true_score
            wait()
            return None
        wait()
        attrs = dict(file_info)
        attrs['insert'] = False
        print "get_existing_file attrs:",attrs
        try:
            fobj = Local_File(**attrs)
            wait()
        except CreationFailed, e:
            print "get_existing_file CreationFailed:",e
            print "file_info:", attrs
            wait()
            sanity_check(file_info['fid'])
            file_info = None
            wait()
            continue

        if not fobj.is_readable:
          print "*"*20,"NOT READABLE","*"*20
          print "NOT READABLE:", fobj.filename
          file_info = None
          wait()
          continue

        if not fobj.exists:
          print "*"*20,"MISSING","*"*20
          print "MISSING:", fobj.filename
          file_info = None
          wait()
        print "GOT:", fobj, "FOR", true_score
    return file_info

def insert_into_dont_pick(fid):
    sql = """INSERT INTO dont_pick (fid, reason) 
             VALUES(%s, 'fid in preload')"""
    query(sql, (fid, ))  # this must be done every time because sometimes
                         # files don't have artists, and the filename
                         # is not Artist - Title.ext
    sql = """SELECT fa.fid, fa.aid 
             FROM file_artists fa LEFT JOIN dont_pick dp ON dp.fid = fa.fid
             WHERE fa.fid = %s AND dp.fid IS NULL"""

    artists = get_results_assoc(sql, (fid, ))
    already_processed_artist = []
    already_processed_basename = []
    alread_processed_fid = []
    insert_location_into_dont_pick(fid, already_processed_basename)
    for a in artists:
        sql = """SELECT fa.fid, fa.aid 
                 FROM file_artists fa
                      LEFT JOIN dont_pick dp ON dp.fid = fa.fid
                 WHERE aid = %s AND dp.fid IS NULL"""
        if a['aid'] in already_processed_artist:
            continue
        already_processed_artist.append(a['aid'])
        files = get_results_assoc(sql, (a['aid'],))
        for f in files:
            print "file for aid:", a['aid'], f['fid']
            sql = """INSERT INTO dont_pick (fid, reason)
                     VALUES (%s, 'artist already inserted')"""

            if f['fid'] not in alread_processed_fid:
                query(sql, (f['fid'],))

            alread_processed_fid.append(f['fid'],)
            insert_location_into_dont_pick(f['fid'], 
                                           already_processed_basename)

def insert_location_into_dont_pick(fid, already_processed_basename):
    sql = """SELECT fid, basename
             FROM file_locations
             WHERE fid = %s"""
    locations = get_results_assoc(sql, (fid,))
    for l in locations:
        if '-' not in l['basename']:
            continue
        artist, title = l['basename'].split('-', 1)
        artist = artist.strip()
        print "basename:", l['basename']
        
        dont_pick_artist_basename(artist, already_processed_basename)

        underscore_artist = artist.replace(" ", "_")
        dont_pick_artist_basename(underscore_artist, 
                                  already_processed_basename)

        space_artist = artist.replace("_", " ")
        dont_pick_artist_basename(space_artist, 
                                  already_processed_basename)

def dont_pick_artist_basename(artist, already_processed_basename):
    insert_basename_into_dont_pick(artist, already_processed_basename)
    

def insert_basename_into_dont_pick(artist, already_processed_basename):
    wait()
    artist = artist.lower()
    if not artist or artist in already_processed_basename:
        return
    already_processed_basename.append(artist)
    _artist = "%s%%-%%" % artist
    sql = """INSERT INTO dont_pick 
             SELECT DISTINCT fl.fid, 
                             'basename matches',
                             ''
             FROM file_locations fl LEFT JOIN dont_pick dp ON 
                                              dp.fid = fl.fid
             WHERE basename ILIKE %s AND 
                   dp.fid IS NULL"""
    print "SQL:", pg_cur.mogrify(sql, (_artist, ))

    query(sql,(_artist,))
    wait()
    _artist = "%% %s%%-%%" % artist
    print "SQL:", pg_cur.mogrify(sql, (_artist, ))
    query(sql,(_artist,))
    wait()
    sql = """INSERT INTO dont_pick 
             SELECT DISTINCT fl.fid, 
                             'basename matches',
                             ''
             FROM file_locations fl LEFT JOIN dont_pick dp ON 
                                              dp.fid = fl.fid
             WHERE basename ILIKE %s AND 
                   basename NOT ILIKE %s AND
                   dp.fid IS NULL"""

    _artist = "%%{_}%s%%-%%" % artist
    __artist = "%%-%%%s%%-%%" % artist
    sql = pg_cur.mogrify(sql, (_artist, __artist))
    sql = sql.format(_="\_")
    print "SQL:", sql
    query(sql)
    wait()

def get_something_for_everyone(users, true_score):
    # Goal
    sql = """SELECT usi1.uid AS usi1_uid, 
                    usi1.ultp AS usi1_ultp,
                    usi1.true_score AS usi1_true_score,
                    usi2.uid AS usi2_uid, 
                    usi2.ultp AS usi2_ultp,
                    usi2.true_score AS usi2_true_score
              FROM user_song_info usi1
                   LEFT JOIN dont_pick dp ON dp.fid = usi1.fid, 
                   user_song_info usi2 
              WHERE usi1.true_score >= 85 AND 
                    usi2.true_score >= 85 AND 
                    usi1.fid = usi2.fid AND
                    usi1.uid = 1 AND
                    usi2.uid = 2 AND
                    dp.fid IS NULL
              ORDER BY CASE WHEN usi1.ultp IS NULL THEN 0 ELSE 1 END,
                       usi1.ultp,
                       CASE WHEN usi2.ultp IS NULL THEN 0 ELSE 1 END,
                       usi2.ultp,
                       random()
              LIMIT 10"""


    selects = []
    froms = []
    wheres = ["dp.fid IS NULL"]
    orders = []
    uids = []
    for user in users:
        uids.append(user['uid'])

    for user in users:
        _user = dict(user)
        _user['true_score'] = true_score
        fmt = """usi{uid}.uid AS usi{uid}_uid,
                 usi{uid}.ultp AS usi{uid}_ultp,
                 usi{uid}.true_score AS usi{uid}_true_score"""
        if user['uid'] == uids[0]:
            fmt += """,
                      usi{uid}.fid"""
        selects.append(fmt.format(**_user))

        if user['uid'] == uids[0]:
            fmt = """user_song_info usi{uid}
                        LEFT JOIN dont_pick dp ON dp.fid = usi{uid}.fid"""
        else:
            fmt = """user_song_info usi{uid}"""

        froms.append(fmt.format(**_user))

        fmt = """usi{uid}.true_score >= {true_score} AND
                 usi{uid}.uid = {uid}"""
        wheres.append(fmt.format(**_user))

        for uid in uids:
            if uid == user['uid']:
                continue
            fmt = """usi{uid1}.fid = usi{uid2}.fid"""
            wheres.append(fmt.format(
                uid1=uid,
                uid2=user['uid']
            ))

        fmt = """CASE WHEN usi{uid}.ultp IS NULL THEN 0 ELSE 1 END,
                       usi{uid}.ultp"""
        orders.append(fmt.format(**_user))

    orders.append("random()")

    sql = """SELECT {selects}
              FROM {froms}
              WHERE {wheres}
              ORDER BY {orders}
              LIMIT 1"""

    sql = sql.format(selects=",\n                    ".join(selects),
                     froms=",\n                   ".join(froms),
                     wheres=" AND\n                    ".join(wheres),
                     orders=",\n                       ".join(orders))

    print "EVERYONE SQL:", sql

    return get_assoc(sql)


def populate_preload_for_uid(uid, min_amount=0, max_cue_time=10):
    gtk.gdk.threads_leave()
    print "populate_preload_for_uid 1"
    sql = """SELECT COUNT(*) as total 
             FROM preload 
             WHERE uid = %s"""
    total = get_assoc(sql, (uid,))
    if total['total'] > min_amount:
        print "uid: %s preload total: %s>%s :min_amount" % (
          uid, total['total'], min_amount)
        return
    print "populate_preload_for_uid 2"
    global populate_locked
    print "populate_preload_for_uid 2.1"

    if populate_locked:
        print "populate_locked"
        print "populate_preload_for_uid 2.5"
        return
    populate_locked = True
    print "populate_preload_for_uid 2.75"
    associate_gernes()
    print "populate_preload_for_uid 3"
    populate_dont_pick()
    print "populate_preload_for_uid 4"
    fix_bad_scores(uid)
    print "populate_preload_for_uid 5"
    insert_missing_songs(uid)
    empty_scores = []
    empty_for_everyone = []

    sql = """SELECT uname, preload_true_scores FROM users WHERE uid = %s"""
    user = get_assoc(sql, (uid,))
    uname = user['uname']
    true_scores_str = user['preload_true_scores']
    if not true_scores_str:
        true_scores = make_true_scores_list()
    else:
        true_scores = true_scores_str.split(",")

    print "TRUE_SCORES BEFORE:", len(true_scores)

    out_of_random_unplayed = False
    max_cue_time = int(ceil(max_cue_time))
    if max_cue_time < 5:
        max_cue_time = 5
    start_time = time.time()
    print "max_cue_time:", max_cue_time

    users = get_results_assoc("""SELECT uid 
                                 FROM users 
                                 WHERE listening = true""")
    print "USERS:", users
    user_len = len(users)
    while time.time() - start_time < max_cue_time:
        wait()
        if not true_scores or len(true_scores) == 0:
            print "making true score list"
            true_scores = make_true_scores_list()
        true_score = true_scores.pop()
        print "empty_scores:", empty_scores
        print "true_scores:", true_scores
        if true_score in empty_scores:
            print "skipping empty score:", true_score
            continue

        sample = get_true_score_sample(uid, true_score)
        
        if not sample:
            print "nothing for:",true_score
            empty_scores.append(true_score)
            continue

        for f in sample:
            print "sample :",true_score, f

        if user_len > 1 and true_score not in empty_for_everyone and \
           int(true_score) >= 70:
            f = get_something_for_everyone(users, true_score)
            if not f:
                print "EMPTY FOR EVERYONE", true_score
                empty_for_everyone.append(true_score)
            else:
                insert_fid_into_preload(
                    f['fid'], uid, 
                    "everyone true_score >= %s" % (true_score, ))


        f = get_existing_file(uid, true_score)

        if not f:
            print "nothing for:",true_score
            empty_scores.append(true_score)
            continue
        wait()

        insert_fid_into_preload(
          f['fid'], uid, "%s true_score >= %s" % (uname, true_score, ))
        insert_into_dont_pick(f['fid'])

        preload = get_preload()

        for p in preload:
            print "p:", p
        
        if not out_of_random_unplayed:
          f = get_single_random_unplayed(uid)
          if not f:
            out_of_random_unplayed = True
            continue
        wait()

        insert_fid_into_preload(f['fid'], uid, "random unplayed for %s" % (uname,))
        insert_into_dont_pick(f['fid'])

    sql = """SELECT count(*) as total 
             FROM preload 
             WHERE uid = %s"""

    preload = get_preload()

    for p in preload:
        print "p:", p

    sql = """UPDATE users 
             SET preload_true_scores = %s 
             WHERE uid = %s
             RETURNING *"""

    user = get_assoc(sql, (",".join(true_scores), uid))
    print "TRUE_SCORES:",user['preload_true_scores']
    print "TRUE_SCORES AFTER:", len(true_scores)
    populate_locked = False


def get_preload():
    return get_results_assoc("""SELECT flid, p.fid, uid, basename, reason
                                FROM preload p, file_locations fl
                                WHERE fl.fid = p.fid
                                ORDER BY basename""")


def remove_songs_in_preload_for_users_who_are_not_listening():
    query("""DELETE FROM preload p WHERE uid NOT IN (SELECT uid 
                                                     FROM users 
                                                     WHERE listening = true)""")

def remove_duplicates_from_preload():
    duplicates = get_results_assoc("""SELECT count(f.sha512) AS total, f.sha512 
                                      FROM files f, preload p 
                                      WHERE f.fid = p.fid AND (f.sha512 != ''
                                        OR f.sha512 IS NOT NULL)
                                      GROUP BY f.sha512 
                                      HAVING count(f.sha512) > 1""")
    for d in duplicates:
      files = get_results_assoc("""SELECT p.fid, p.uid
                                   FROM files f, preload p
                                   WHERE f.fid = p.fid AND sha512 = %s""",
                                   (d['sha512'],))
      for f in files[1:]:
        query("""DELETE FROM preload WHERE fid = %s AND uid = %s""",
              (f['fid'], f['uid']))

def get_cue_for():
    return get_assoc("""SELECT uid, last_time_cued 
                        FROM users 
                        WHERE listening = true 
                        ORDER BY CASE WHEN last_time_cued IS NULL THEN 0 ELSE 1 END, 
                                 last_time_cued 
                        LIMIT 1""")

def set_last_time_cued(uid):
    query("""UPDATE users SET last_time_cued = NOW() WHERE uid = %s""",
             (uid,))

def get_single_from_preload(uid=None):
    sql = """SELECT * 
                 FROM preload p, files f 
                 WHERE f.fid = p.fid AND 
                       reason = 'From search'
                 ORDER BY plid 
                 LIMIT 1"""
    f = get_assoc(sql)
    if f:
      return f

    if uid:
        sql = """SELECT * 
                 FROM preload p, files f 
                 WHERE f.fid = p.fid AND uid = %s 
                 ORDER BY plid 
                 LIMIT 1"""
        f = get_assoc(sql, (uid,))
        if f:
          return f

    return get_assoc("""SELECT * 
                        FROM preload p, files f 
                        WHERE f.fid = p.fid 
                        ORDER BY plid
                        LIMIT 1""")

def remove_fid_from_preload(fid):
    query("DELETE FROM preload WHERE fid = %s",(fid,))

def get_song_from_preload():
    remove_songs_in_preload_for_users_who_are_not_listening()
    cue_for = get_cue_for()
    if cue_for:
        set_last_time_cued(cue_for['uid'])
        f = get_single_from_preload(cue_for['uid'])
        print "get_single_from_preload:", f
        if not f:
            populate_preload(cue_for['uid'])
            f = get_single_from_preload(cue_for['uid'])
            if not f:
                f = get_single_from_preload()
    else:
        f = get_single_from_preload()

    if not f:
        populate_preload()
        f = get_single_from_preload()

    if f:
        remove_fid_from_preload(f['fid'])

    return f


if __name__ == "__main__":
    print("DELETE FROM PRELOAD")
    query("""DELETE FROM preload""")
    query("""DELETE FROM dont_pick""")
    populate_preload()
    sys.exit()
    genres = get_results_assoc("""SELECT * 
                                  FROM genres 
                                  WHERE seq_genre = true""")

    # insert_fid_into_preload()
    uid = 1
    for g in genres:
        f = get_next_file_in_genre_series(g['gid'], uid)
        if not f:
          continue
        pprint.pprint(f)
        insert_fid_into_preload(f['fid'], uid, "test")
        f = get_next_file_in_genre_series(g['gid'], uid)
        if not f:
          continue
        insert_fid_into_preload(f['fid'], uid, "test")
        pprint.pprint(f)



