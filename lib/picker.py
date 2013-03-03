#!/usr/bin/env python
# -*- coding: utf-8 -*-
# picker.py -- Pick songs.
#    Copyright (C) 2012 Eugene Miller <theerm@gmail.com>
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

def wait():
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)

def create_dont_pick():
    global dont_pick_created

    if dont_pick_created:
        # print "dont_pick_created:",dont_pick_created
        return

    dont_pick_created = True
    query("DROP TABLE dont_pick")
    query("CREATE TABLE IF NOT EXISTS dont_pick (fid SERIAL, reason text, reason_value text)")
    query("CREATE UNIQUE INDEX dont_pick_fid_index ON dont_pick (fid)")
    query('CREATE RULE "dont_pick_on_duplicate_ignore" AS ON INSERT TO "dont_pick" WHERE EXISTS(SELECT 1 FROM dont_pick WHERE (fid)=(NEW.fid)) DO INSTEAD NOTHING;')

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
                                 VALUES(%s, true)""",("[undefined]",))
        print "associate_gernes 2.1"

    print "associate_gernes 3"
    query("""INSERT INTO file_genres (fid, gid) 
             SELECT f.fid, %s 
             FROM files f 
             LEFT JOIN file_genres fg ON fg.fid = f.fid 
             WHERE fg.fid IS NULL""",(undefined['gid'],))

def populate_dont_pick():
    associate_gernes()
    query("TRUNCATE dont_pick")
    query("INSERT INTO dont_pick (fid, reason) SELECT fid, 'already in preload' FROM preload")
    listeners = get_results_assoc("SELECT uid FROM users WHERE listening = true", ())

    if listeners:
        total_to_remove = get_assoc("SELECT FLOOR(count(DISTINCT fid) * 0.01) AS total FROM file_genres fg, genres g WHERE g.gid = fg.gid AND g.enabled = true")

        total_artists_to_remove = get_assoc("SELECT FLOOR(count(DISTINCT aid) * 0.01) AS total FROM file_artists fa, file_genres fg, genres g WHERE g.gid = fg.gid AND g.enabled = true AND fa.fid = fg.fid")

        if total_to_remove.has_key('total'):
            total_to_remove = str(total_to_remove['total'])
        else:
            total_to_remove = "0"
        
        if total_artists_to_remove.has_key('total'):
            total_artists_to_remove = str(total_artists_to_remove['total'])
        else:
            total_artists_to_remove = "0"

        for l in listeners:
            query("INSERT INTO dont_pick (fid, reason, reason_value) SELECT DISTINCT fid, 'rated 0', uid FROM user_song_info WHERE rating = 0 AND uid = %s",(l['uid'],))

            # Add recently played files.
            query("INSERT INTO dont_pick (fid, reason, reason_value) SELECT DISTINCT fid, 'recently played', ultp  FROM user_song_info WHERE uid = %s AND ultp IS NOT NULL ORDER BY ultp DESC LIMIT "+total_to_remove, (l['uid'],))

            # Add recently played artists
            # Don't add aid column
            query("INSERT INTO dont_pick (fid, reason) SELECT DISTINCT fid, 'Recently played artist' FROM file_artists WHERE aid IN (SELECT aid FROM file_artists fa, user_song_info u WHERE fa.fid = u.fid AND ultp IS NOT NULL AND u.uid = %s ORDER BY ultp DESC LIMIT "+total_artists_to_remove+")",(l['uid'],))

    query("INSERT INTO dont_pick (fid, reason) SELECT DISTINCT fid, 'artist in preload' FROM file_artists WHERE aid IN (SELECT DISTINCT aid FROM file_artists fa WHERE fid IN (SELECT DISTINCT fid FROM preload WHERE fid NOT IN (SELECT fid FROM dont_pick)))")
    # for r in dont_pick:
    #    print "don't pick:",r


def populate_preload(uid=None, min_amount=0):

    if not uid or uid is None:
        listeners = get_results_assoc("SELECT uid FROM users WHERE listening = true", ())
        for l in listeners:
            populate_preload(l['uid'], min_amount)
        return

    try:
        populate_preload_for_uid(uid, min_amount)
    except:
        print "ERROR!!!! COULD NOT POPULATE PRELOAD"
        global populate_locked
        populate_locked = False
        # populate_preload_for_uid(uid, min_amount)


def populate_preload_for_uid(uid, min_amount=0):
    print "populate_preload_for_uid 1"
    total = get_assoc("SELECT COUNT(*) as total FROM preload WHERE uid = %s",(uid,))
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

    default_rating = 6
    default_score = 5
    default_percent_played = 50.0
    default_true_score = ((default_rating * 2 * 10.0) + \
                                    (default_score * 10.0) + \
                                    (default_percent_played) / 3)

    m = pg_cur.mogrify("SELECT fid FROM user_song_info WHERE uid = %s", (uid,))
    q = """INSERT INTO user_song_info (fid, uid, rating, score, percent_played, true_score) 
                SELECT f.fid, '%s', '%s', '%s', '%s', '%s' 
                FROM files f 
                WHERE f.fid NOT IN (%s)""" % (uid, default_rating, default_score, 
                                              default_percent_played, 
                                              default_true_score, m)
    query(q)
    print "populate_preload_for_uid 5"

    scores = [0,10,20,30,40,50,60,70,80,90,100]

    shuffle(scores)

    true_scores = []

    for true_score in scores:
        iter_count = int(true_score * 0.1)
        if iter_count <= 0:
            iter_count = 1
        for i in range(0, iter_count):
            true_scores.append(true_score)

    empty_scores = []

    for true_score in true_scores:
        wait()
        if true_score in empty_scores:
            print "skipping empty score:", true_score
            continue

        sample = get_results_assoc("SELECT u.fid, true_score, ultp FROM user_song_info u, genres g, file_genres fg LEFT JOIN dont_pick dp ON dp.fid = fg.fid WHERE dp.fid IS NULL AND u.uid = %s AND u.fid = fg.fid AND g.enabled = true AND g.gid = fg.gid AND true_score >= %s ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, ultp, random() LIMIT 10", (uid, true_score))
        if not sample:
            print "nothing for:",true_score
            empty_scores.append(true_score)
            continue

        for f in sample:
            print "sample :",true_score, f

        f = get_assoc("SELECT u.fid, true_score, ultp FROM user_song_info u, genres g, file_genres fg LEFT JOIN dont_pick dp ON dp.fid = fg.fid WHERE dp.fid IS NULL AND u.uid = %s AND u.fid = fg.fid AND g.enabled = true AND g.gid = fg.gid AND true_score >= %s ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, ultp, random() LIMIT 1", (uid, true_score))
        if not f:
            print "nothing for:",true_score
            empty_scores.append(true_score)
            continue
        wait()
        print "adding:", get_assoc("SELECT * FROM files WHERE fid = %s",(f['fid'],))
        query("INSERT INTO preload(fid,uid,reason) VALUES(%s,%s,%s)",(f['fid'], uid, "true_score >= %s" % (true_score,)))
        query("INSERT INTO dont_pick (fid, reason) SELECT DISTINCT fid, 'artist in preload' FROM file_artists WHERE aid IN (SELECT DISTINCT aid FROM file_artists fa WHERE fid IN (SELECT DISTINCT fid FROM preload))")

    for i in range(0,10):
        sample = get_results_assoc("SELECT u.fid, true_score, ultp FROM user_song_info u, genres g, file_genres fg LEFT JOIN dont_pick dp ON dp.fid = fg.fid WHERE dp.fid IS NULL AND u.uid = %s AND u.fid = fg.fid AND g.enabled = true AND g.gid = fg.gid ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, ultp, random() LIMIT 10", (uid,))

        if not sample:
            break;
        for f in sample:
            print "sample2:", f

        f = get_assoc("SELECT u.fid, true_score, ultp FROM user_song_info u, genres g, file_genres fg LEFT JOIN dont_pick dp ON dp.fid = fg.fid WHERE dp.fid IS NULL AND u.uid = %s AND u.fid = fg.fid AND g.enabled = true AND g.gid = fg.gid ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, ultp, random() LIMIT 1", (uid,))

        query("INSERT INTO preload(fid,uid,reason) VALUES(%s,%s,%s)",(f['fid'], uid, "random unplayed"))
        query("INSERT INTO dont_pick (fid, reason) SELECT DISTINCT fid, 'artist in preload' FROM file_artists WHERE aid IN (SELECT DISTINCT aid FROM file_artists fa WHERE fid IN (SELECT DISTINCT fid FROM preload))")

    preload = get_results_assoc("SELECT uid, basename FROM preload p, files f WHERE f.fid = p.fid ORDER BY basename")

    for p in preload:
        print "p:",p

    populate_locked = False

def get_song_from_preload():
    query("DELETE FROM preload p WHERE uid NOT IN (SELECT uid FROM users WHERE listening = true)")
    cue_for = get_assoc("SELECT uid, last_time_cued FROM users WHERE listening = true ORDER BY CASE WHEN last_time_cued IS NULL THEN 0 ELSE 1 END, last_time_cued LIMIT 1")

    if cue_for:
        f = get_assoc("SELECT * FROM preload p, files f WHERE f.fid = p.fid AND uid = %s ORDER BY random() LIMIT 1", (cue_for['uid'],))
        query("UPDATE users SET last_time_cued = NOW() WHERE uid = %s",(cue_for['uid'],))
        if not f:
            populate_preload(cue_for['uid'])
            f = get_assoc("SELECT * FROM preload p, files f WHERE f.fid = p.fid AND uid = %s ORDER BY random() LIMIT 1", (cue_for['uid'],))
            if not f:
                f = get_assoc("SELECT * FROM preload p, files f WHERE f.fid = p.fid ORDER BY random() LIMIT 1")

    else:
        f = get_assoc("SELECT * FROM preload p, files f WHERE f.fid = p.fid ORDER BY random() LIMIT 1")
    
    if not f:
        populate_preload()
        f = get_assoc("SELECT * FROM preload p, files f WHERE f.fid = p.fid ORDER BY random() LIMIT 1")

    if f:
        query("DELETE FROM preload WHERE fid = %s",(f['fid'],))

    return f



