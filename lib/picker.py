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
    query("INSERT INTO dont_pick (fid, reason) SELECT fid, 'already in preload' FROM preload")
    insert_duplicate_files_into_dont_pick()
    listeners = get_results_assoc("SELECT uid FROM users WHERE listening = true", ())

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


def remove_missing_files_from_preload():
  files = get_results_assoc("""SELECT p.fid, dirname, basename, p.uid
                               FROM preload p, file_locations fl
                               WHERE fl.fid = p.fid""")

  for f in files:
      if not os.path.exists(os.path.join(f['dirname'], f['basename'])):
          print "!"*20,"MISSING","!"*20
          print "MISSING:", f['fid']
          query("""DELETE FROM preload WHERE fid = %s""", (f['fid'],))


def populate_preload(uid=None, min_amount=0):
    remove_duplicates_from_preload()
    remove_missing_files_from_preload()
    if not uid or uid is None:
        listeners = get_results_assoc("SELECT uid FROM users WHERE listening = true", ())
        for l in listeners:
            populate_preload(l['uid'], min_amount)
        return
    populate_preload_for_uid(uid, min_amount)
    try:
        populate_preload_for_uid(uid, min_amount)
    except:
        print "ERROR!!!! COULD NOT POPULATE PRELOAD"
        global populate_locked
        populate_locked = False
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

    q = """INSERT INTO user_song_info (fid, uid, rating, score, percent_played, true_score) 
                SELECT f.fid, '%s', '%s', '%s', '%s', '%s' 
                FROM files f 
                WHERE f.fid IN (%s)""" % (uid, DEFAULT_RATING, DEFAULT_SCORE, 
                                          DEFAULT_PERCENT_PLAYED, 
                                          DEFAULT_TRUE_SCORE, m)
    query(q)

def get_true_score_sample(uid, true_score):
    return get_results_assoc("""SELECT u.fid, true_score, ultp 
                                FROM user_song_info u, genres g, file_genres fg 
                                     LEFT JOIN dont_pick dp ON dp.fid = fg.fid 
                                WHERE dp.fid IS NULL AND u.uid = %s AND 
                                      u.fid = fg.fid AND 
                                      g.enabled = true AND 
                                      g.gid = fg.gid AND 
                                      true_score >= %s 
                                ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                                       ultp, random() 
                                LIMIT 10""", (uid, true_score))

def get_single_from_true_score(uid, true_score):
    return get_assoc("""SELECT u.fid, true_score, ultp 
                         FROM user_song_info u, genres g, file_genres fg 
                              LEFT JOIN dont_pick dp ON dp.fid = fg.fid 
                         WHERE dp.fid IS NULL AND u.uid = %s AND 
                               u.fid = fg.fid AND g.enabled = true AND 
                               g.gid = fg.gid AND true_score >= %s 
                         ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                                  ultp, random() 
                         LIMIT 1""", 
                         (uid, true_score))

def make_true_scores_list():
    scores = [0,10,20,30,40,50,60,70,80,90,100]

    shuffle(scores)

    true_scores = []

    for true_score in scores:
        iter_count = int(true_score * 0.1)
        if iter_count <= 0:
            iter_count = 1
        for i in range(0, iter_count):
            true_scores.append(true_score)

    shuffle(true_scores)

    return true_scores

def insert_fid_into_preload(fid, uid, reason):
    seq_info = is_sequential(fid)
    if seq_info is None:
        print "adding:", get_assoc("SELECT * FROM files WHERE fid = %s",(fid,))
        query("""INSERT INTO preload(fid,uid,reason) VALUES(%s,%s,%s)""",
                 (fid, uid, reason))
        return

    if 'aid' in seq_info:
        next_file = get_next_file_in_artist_series(seq_info['aid'], uid)
        if next_file:
            fid = next_file['fid']
            reason += " is sequential artist"

    if 'gid' in seq_info:
        next_file = get_next_file_in_genre_series(seq_info['gid'], uid)
        if next_file:
          fid = next_file['fid']
          reason += " is sequential genre"
    print "adding sequential:", get_assoc("SELECT * FROM files WHERE fid = %s",(fid,))
    query("""INSERT INTO preload(fid,uid,reason) VALUES(%s,%s,%s)""",
             (fid, uid, reason))

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
           ORDER BY CASE WHEN ultp IS NULL THEN 1 ELSE 0 END,
                    ultp DESC, dirname, basename
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
    next_file = None
    # Get the last file played in that genre
    print "g1"
    q = """SELECT dirname, basename, ultp
           FROM file_locations fl
                LEFT JOIN dont_pick dp ON dp.fid = fl.fid, 
                file_genres fg,
                user_song_info usi
           WHERE usi.fid = fl.fid AND
                 fg.fid = fl.fid AND
                 fg.gid = %s AND
                 usi.uid = %s AND
                 dp.fid IS NULL
           ORDER BY CASE WHEN ultp IS NULL THEN 1 ELSE 0 END,
                    ultp DESC, dirname, basename
           LIMIT 1"""
    last_file = get_assoc(q, (gid, uid))

    print "g2",pg_cur.mogrify(q, (gid, uid))
    if last_file:
        print "g2.1 LAST_FILE:", last_file
        # Get the next artist in the series
        q = """SELECT dirname, basename, fl.fid
               FROM file_locations fl,
                    file_genres fg
               WHERE dirname >= %s AND
                     basename > %s AND
                     fl.fid = fg.fid AND
                     fg.gid = %s
               ORDER BY dirname, basename
               LIMIT 1"""
        next_file = get_assoc(q, (last_file['dirname'], last_file['basename'], gid))
        print "g2.2"
        print pg_cur.mogrify(q, (last_file['dirname'], last_file['basename'], gid))
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
    query("""INSERT INTO dont_pick (fid, reason) 
             SELECT DISTINCT fid, 'artist in preload' 
             FROM file_artists WHERE aid IN (SELECT DISTINCT aid 
                                             FROM file_artists fa 
                                             WHERE fid IN (SELECT DISTINCT fid 
                                                           FROM preload))""")


def get_random_unplayed_sample(uid):
    return get_results_assoc("""SELECT u.fid, true_score, ultp 
                                FROM user_song_info u, genres g, file_genres fg 
                                     LEFT JOIN dont_pick dp ON 
                                               dp.fid = fg.fid 
                                WHERE dp.fid IS NULL AND u.uid = %s AND 
                                      u.fid = fg.fid AND 
                                      g.enabled = true AND 
                                      g.gid = fg.gid 
                                ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                                         ultp, 
                                         random() 
                                LIMIT 10""", 
                                (uid,))

def get_single_random_unplayed(uid):
    return get_assoc("""SELECT u.fid, true_score, ultp 
                        FROM user_song_info u, genres g, file_genres fg 
                             LEFT JOIN dont_pick dp ON dp.fid = fg.fid 
                        WHERE dp.fid IS NULL AND u.uid = %s AND 
                              u.fid = fg.fid AND g.enabled = true AND 
                              g.gid = fg.gid 
                        ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                                 ultp, random() 
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
    return file_info

def populate_preload_for_uid(uid, min_amount=0):
    gtk.gdk.threads_leave()
    print "populate_preload_for_uid 1"
    total = get_assoc("SELECT COUNT(*) as total FROM preload WHERE uid = %s", (uid,))
    if total['total'] > min_amount:
        print "uid: %s preload total: %s>%s :min_amount" % (uid, total['total'], min_amount)
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

    true_scores = make_true_scores_list()

    empty_scores = []

    for true_score in true_scores:
        wait()
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

        f = get_existing_file(uid, true_score)

        if not f:
            print "nothing for:",true_score
            empty_scores.append(true_score)
            continue
        wait()

        insert_fid_into_preload(f['fid'], uid, "true_score >= %s" % (true_score, ))
        insert_artists_in_preload_into_dont_pick()
        insert_duplicate_files_into_dont_pick()

    for i in range(0,10):
        sample = get_random_unplayed_sample(uid)

        if not sample:
            break;
        for f in sample:
            print "sample2:", f

        f = get_single_random_unplayed(uid)

        insert_fid_into_preload(f['fid'], uid, "random unplayed")
        insert_artists_in_preload_into_dont_pick()
        insert_duplicate_files_into_dont_pick()

    preload = get_preload()

    for p in preload:
        print "p:",p

    populate_locked = False

def get_preload():
    return get_results_assoc("""SELECT uid, basename 
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
    if uid:
        f = get_assoc("""SELECT * 
                            FROM preload p, files f 
                            WHERE f.fid = p.fid AND 
                                  reason = 'From search'
                            ORDER BY plid LIMIT 1""")
        if f:
          return f
        return get_assoc("""SELECT * 
                            FROM preload p, files f 
                            WHERE f.fid = p.fid AND uid = %s 
                            ORDER BY random() LIMIT 1""", 
                            (uid,))

    f = get_assoc("""SELECT * 
                     FROM preload p, files f 
                     WHERE f.fid = p.fid AND reason = 'From search'
                     ORDER BY plid
                     LIMIT 1""")
    if f:
      return f

    return get_assoc("""SELECT * 
                        FROM preload p, files f 
                        WHERE f.fid = p.fid 
                        ORDER BY random() 
                        LIMIT 1""")

def remove_fid_from_preload(fid):
    query("DELETE FROM preload WHERE fid = %s",(fid,))

def get_song_from_preload():
    remove_songs_in_preload_for_users_who_are_not_listening()
    cue_for = get_cue_for()
    if cue_for:
        set_last_time_cued(cue_for['uid'])
        f = get_single_from_preload(cue_for['uid'])
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



