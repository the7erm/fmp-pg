#!/usr/bin/env python2
# clean-db.py -- main file.
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


import os
import sys
from lib.__init__ import *
import lib.fobj
from lib.ratings_and_scores import calculate_true_score_for_uid
from genres_v1 import genres_v1

def exeq(q, args=None):
    qm = pg_cur.mogrify(q, args)
    if testing:
        print "TESTING:", qm
    else:
        print "RUNNING:", qm
        query(qm)

def get_results_assoc_update(q, args=None):
    if testing:
        print "TESTING:", q, args
    else:
        print "RUNNING", q, args
        get_results_assoc(q, args)

def insert_assoc(q, args=None):
    qm = pg_cur.mogrify(q, args)
    if testing:
        print "TESTING:", qm
    else:
        print "RUNNING", qm
        get_assoc(qm)

def pf(arg):
    # .format(object, context, maxlevels, level)
    return ppr.pformat(arg)

def pp(arg):
    ppr.pprint(arg)

def find_master(files, must_exist=True):
    has_history = {}
    has_rating = {}
    exists = {}
    final_score = {}
    tally = {}
    file_info = {}
    for d in files:
        d = dict(d)
        dup_filename = os.path.join(d['dir'], d['basename'])
        if os.path.exists(dup_filename):
            tally[d['fid']] = 1
            file_info[d['fid']] = d
            exists[d['fid']] = d
            history, ratings = get_scores(d['fid'])
            print "history:",history
            print "ratings:",ratings
            if not history in has_history:
                has_history[history] = []
            has_history[history].append(d)
            if not ratings in has_rating:
                has_rating[ratings] = []
            has_rating[ratings].append(d)


    for total, items in has_history.iteritems():
        for d in items:
            fid = int(d['fid'])
            tally[fid] = tally[fid] + int(total)

    for total, items in has_rating.iteritems():
        for d in items:
            print "D:",d
            fid = int(d['fid'])
            tally[fid] = tally[fid] + int(total)

    for fid, total in tally.iteritems():
        key = "%04d" % int(total)
        if key not in final_score:
            final_score[key] = []
        final_score[key].append(file_info[fid])

    pp(final_score)
    if len(final_score) > 0:
        keys = final_score.keys()
        print "KEYS:", pf(keys)
        keys.sort(reverse=True)
        print "/KEYS:", pf(keys)
        master_key = keys[0]
        master = final_score[master_key][0]
        print "MASTER:", master
        return master
    return None

def where_did_it_go(f):
    dups = get_dups(f)
    return find_master(dups)

def get_scores(fid):
    total = get_history_count(fid)
    history = "%05d" % total['total']
    total = get_played_and_rated_count(fid)
    ratings = "%05d" % total['total']
    return history, ratings

def get_played_and_rated_count(fid):
    return get_assoc("""SELECT count(*) AS total
                        FROM user_song_info usi 
                        WHERE usi.fid = %s AND rating != 6 AND
                              ultp IS NOT NULL""", (fid,))
    # SELECT count(*) FROM user_song_info WHERE rating NOT IN (0,6) AND ultp IS NOT NULL;

def get_history_count(fid):
    return get_assoc("""SELECT count(*) AS total
                        FROM user_history uh
                        WHERE uh.id = %s AND id_type = 'f'""", (fid,))


def whos_the_boss(src, dst):
    src_history, src_ratings = get_scores(src['fid'])
    dst_history, dst_ratings = get_scores(dst['fid'])
    src_score = int(src_history) + int(src_ratings)
    dst_score = int(src_history) + int(dst_ratings)
    if src_score >= dst_score:
        return src, dst
    return dst, src

def reassociate(src, dst):
    master, slave = whos_the_boss(src, dst)
    reassociate_ratings(master, slave)
    reassociate_user_history(master, slave)

    # src to dst
    copy_artists(src['fid'], dst['fid'])
    copy_genres(src['fid'], dst['fid'])
    copy_albums(src['fid'], src['fid'])

    # dst to src
    copy_artists(dst['fid'], src['fid'])
    copy_genres(dst['fid'], src['fid'])
    copy_albums(dst['fid'], src['fid'])


def get_album_files(fid):
    return get_results_assoc("""SELECT *
                                FROM album_files
                                WHERE fid = %s""", (fid,))

def get_file_genres(fid):
    return get_results_assoc("""SELECT *
                                FROM file_genres 
                                WHERE fid = %s""", (fid,))


def get_file_artists(fid):
    return get_results_assoc("""SELECT *
                                FROM file_artists
                                WHERE fid = %s""", (fid,))


def copy_albums(src_fid, dst_fid):
    album_files = get_album_files(src_fid)
    for af in album_files:
        present = get_assoc("""SELECT * FROM album_files WHERE fid = %s AND alid = %s""",
                            (dst_fid, af['alid']))
        if present:
            continue
        q = pg_cur.mogrify("""INSERT INTO 
                                album_files (fid, alid) VALUES(%s, %s)
                                RETURNING *""", 
                              (dst_fid, af['alid']))
        insert_assoc(q)

def copy_genres(src_fid, dst_fid):
    file_genres = get_file_genres(src_fid)
    for fg in file_genres:
        present = get_assoc("""SELECT * FROM file_genres WHERE fid = %s AND gid = %s""",
                            (dst_fid, fg['gid']))
        if present:
            continue
        q = pg_cur.mogrify("""INSERT INTO 
                                file_genres (fid, gid) VALUES(%s, %s)
                                RETURNING *""", 
                              (dst_fid, fg['gid']))
        insert_assoc(q)

def copy_artists(src_fid, dst_fid):
    file_artists = get_file_artists(src_fid)
    for fa in file_artists:
        present = get_assoc("""SELECT * FROM file_artists WHERE fid = %s AND aid = %s""",
                            (dst_fid, fa['aid']))
        if present:
            continue
        q = pg_cur.mogrify("""INSERT INTO 
                                file_artists (fid, aid) VALUES(%s, %s) 
                                RETURNING *""",
                              (dst_fid, fa['aid']))
        insert_assoc(q)

def get_history(fid):
    return get_results_assoc("""SELECT *
                                FROM user_history uh
                                WHERE id = %s AND id_type = 'f'""",
                                (fid,))


def merge_history(history, fid):
    for h in history:
        try:
            insert_assoc("""INSERT INTO user_history 
                                (id, id_type, uid, percent_played, 
                                 time_played, date_played, true_score,
                                 score, rating)
                                VALUES(%s, %s, %s, %s, 
                                       %s, %s, 
                                       %s, %s, %s)
                            RETURNING *""",
                            (fid, 'f', h['uid'], h['percent_played'], 
                             h['time_played'], h['date_played'], h['true_score'],
                             h['score'], h['rating']))
        except psycopg2.IntegrityError, e:
            query("COMMIT")


def reassociate_user_history(master, slave):
    master_history = get_history(master['fid'])
    slave_history = get_history(slave['fid'])
    merge_history(master_history, slave['fid'])
    merge_history(slave_history, master['fid'])

def get_artists(fid):
    return get_results_assoc("""SELECT DISTINCT a.aid 
                                FROM artists a, file_artists fa 
                                WHERE a.aid = fa.aid AND fa.fid = %s""",
                                (fid,))


def get_ratings(fid):
    return get_results_assoc("""SELECT *
                                FROM user_song_info usi
                                WHERE fid = %s""",
                                (fid,))

def set_user_song_info_to_master(master, slave):
    
    slave_data = get_assoc("""SELECT * 
                              FROM user_song_info 
                              WHERE fid = %s AND uid = %s""",
                              (slave['fid'], master['uid']))
    print "MASTER:    ",master
    print "SLAVE DATA:",slave_data
    print "SLAVE:",slave
    if not slave_data:
        insert_assoc("""INSERT INTO user_song_info 
                            (uid, fid, rating, 
                             score, percent_played, 
                             ultp, true_score)
                             VALUES(%s, %s, %s, 
                                    %s, %s, 
                                    %s, %s)
                        RETURNING *""",
                            (master['uid'], slave['fid'], master['rating'], 
                             master['score'], master['percent_played'], 
                             master['ultp'], master['true_score'])
        )
        return
    """
    ----------------+--------------------------+---------------------------------------------------------------
     usid           | integer                  | not null default nextval('user_song_info_usid_seq'::regclass)
     uid            | integer                  | not null
     fid            | integer                  | not null
     rating         | integer                  | default 6
     score          | integer                  | default 5
     percent_played | double precision         | default 50.00
     ultp           | timestamp with time zone | 
     true_score     | double precision         | default 50.00
    """

    keys = ['rating', 'score', 'percent_played', 'ultp', 'true_score']
    something_set = False
    for k in keys:
        if master[k]:
            if master[k] == slave_data[k]:
                continue
            if k == 'rating' and master['rating'] == 6:
                continue
            if k == 'score' and master['score'] == DEFAULT_SCORE:
                continue
            if k == 'percent_played' and master['percent_played'] == DEFAULT_PERCENT_PLAYED:
                continue
            if k == 'true_score' and master['true_score'] == DEFAULT_TRUE_SCORE:
                continue
            something_set = True
            insert_assoc("""UPDATE user_song_info
                            SET """+k+""" = %s
                            WHERE fid = %s AND uid = %s RETURNING *""", 
                            (master[k], slave['fid'], master['uid']))
    
    if not testing and something_set:
        calculate_true_score_for_uid(master['uid'], slave['fid'])

def reassociate_ratings(master, slave):
    master_ratings = get_ratings(master['fid'])
    if not master_ratings:
        print "THIS IF FUCKED UP HOW CAN IT BE THE MASTER IF IT DOESN'T EXIST?!"
        sys.exit()
    for master in master_ratings:
        set_user_song_info_to_master(master, slave)


def get_dups(f):
    return get_results_assoc("""SELECT *
                                FROM files f 
                                WHERE f.fid != %s AND sha512 = %s""",
                                (f['fid'], f['sha512']))


def get_non_unique_file_genres():
    return get_results_assoc("""SELECT fid, count(gid) 
                                FROM file_genres 
                                GROUP BY fid, gid HAVING count(gid) > 1 ORDER BY count(gid)""")

#### START OF MAIN PROGRAM ####

ppr = pprint.PrettyPrinter(indent=4)

testing = True
if "--test" in sys.argv:
    testing = True
if "--no-test" in sys.argv:
    testing = False


def clean_dup_file_genres():
    non_unique = get_non_unique_file_genres()
    for f in non_unique:
        query("""DELETE FROM file_genres WHERE fgid IN (
                    SELECT fgid FROM  file_genres where fid = %s OFFSET 1)""", (f['fid'],))

clean_dup_file_genres();
print "Locating missing files..."
files = get_results_assoc("""SELECT * FROM files f ORDER BY dir, basename""")
for f in files:
    f = dict(f)
    filename = os.path.join(f['dir'], f['basename'])
    if not os.path.exists(filename):
        print "MISSING:",f
        moved_to = where_did_it_go(f)
        if moved_to is None:
            print "NO DUPS:",filename
            exeq("""DELETE FROM files f WHERE fid = %s""", (f['fid'],))
        else:
            reassociate(f, moved_to)
            exeq("""DELETE FROM files f WHERE fid = %s""", (f['fid'],))


print "Cleaning album associations..."
deleted_albums = get_results_assoc("""SELECT *
                                      FROM album_files af 
                                           LEFT JOIN files f ON f.fid = af.fid
                                      WHERE f.fid IS NULL""")

for d in deleted_albums:
    d = dict(d)
    print "DELETING album file info:",d
    exeq("""DELETE FROM album_files WHERE alfid = %s""", (d['alfid'],))


deleted_albums = get_results_assoc("""SELECT al.*
                                      FROM albums al 
                                           LEFT JOIN album_files af ON af.alid = al.alid
                                      WHERE alfid IS NULL""")

for d in deleted_albums:
    d = dict(d)
    print "DELETING album:",d
    exeq("""DELETE FROM albums al
                WHERE alid = %s""",(d['alid'],))

print "Cleaning albums that have no associations..."
deleted_artists = get_results_assoc("""SELECT *
                                      FROM file_artists fa
                                           LEFT JOIN files f ON f.fid = fa.fid
                                      WHERE f.fid IS NULL""")
for d in deleted_artists:
    d = dict(d)
    print "DELETING artist:",d
    exeq("""DELETE FROM file_artists WHERE faid = %s""", (d['faid'],))

print "Cleaning genre associations..."
deleted_genres = get_results_assoc("""SELECT *
                                      FROM file_genres fg
                                           LEFT JOIN files f ON f.fid = fg.fid
                                      WHERE f.fid IS NULL""")
for d in deleted_genres:
    d = dict(d)
    print "DELETING file genre info:",d
    exeq("""DELETE FROM file_genres WHERE fgid = %s""", (d['fgid'],))



possible_deleted_genres = get_results_assoc("""SELECT * 
                                               FROM genres g
                                                    LEFT JOIN file_genres fg ON fg.gid = g.gid
                                               WHERE fg.gid IS NULL""")


for g in possible_deleted_genres:
    if g['genre'] in genres_v1:
        print "v1 genre:",g['genre']
        continue
    exeq("""DELETE FROM genres WHERE gid = %s""",(g['gid'], ))


# TODO DELETE all user_artist_history that has been removed.

removed_history = get_results_assoc("""SELECT uh.*
                                       FROM user_history uh
                                            LEFT JOIN files f ON f.fid = uh.id 
                                            AND uh.id_type = 'f'
                                       WHERE f.fid IS NULL AND 
                                             uh.id_type = 'f'""")
for d in removed_history:
    exeq("""DELETE FROM user_history WHERE uhid = %s""",(d['uhid'],))


removed_artists_history = get_results_assoc("""SELECT uah.*
                                               FROM user_artist_history uah 
                                                    LEFT JOIN artists a ON a.aid = uah.aid
                                               WHERE a.aid IS NULL""")

for r in removed_artists_history:
    exeq("""DELETE FROM user_artist_history WHERE uahid = %s""", (r['uahid'],))

print "Cleaning user song info..."
print "Cleaning user song info removing deleted user info..."
deleted_users_song_info = get_results_assoc("""SELECT usi.* 
                                               FROM user_song_info usi
                                                    LEFT JOIN users u ON 
                                                              u.uid = usi.uid
                                               WHERE u.uid IS NULL""")

for d in deleted_users_song_info:
    d = dict(d)
    print "DELETING usi (missing user):",d
    exeq("""DELETE FROM user_song_info usi WHERE usi.usid = %s""",(d['usid'],))

print "Cleaning user song info removing data for missing files..."
deleted_file_info = get_results_assoc("""SELECT usi.*
                                         FROM user_song_info usi
                                              LEFT JOIN files f ON 
                                                        f.fid = usi.fid
                                         WHERE f.fid IS NULL""")
for d in deleted_file_info:
    d = dict(d)
    print "DELETING usi missing file:",d
    exeq("""DELETE FROM user_song_info usi WHERE usi.usid = %s""",(d['usid'],))

missing_fid = get_results_assoc("""SELECT p.*
                                   FROM preload p
                                        LEFT JOIN files f ON p.fid = f.fid
                                   WHERE f.fid IS NULL""")

for p in missing_fid:
    exeq("""DELETE FROM preload WHERE plid = %s""",(p['plid'],))

print "inserting missing songs"
users = get_results_assoc("""SELECT * FROM users WHERE listening = true""")
for u in users:
    print "inserting missing songs for %s"  % u['uname']
    uid = u['uid']
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
