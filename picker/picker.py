#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# picker.py -- picks files for users
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
                          GLib, Gio, GdkPixbuf
GObject.threads_init()

import os
import sys

try:
    from db.db import *
except:
    sys.path.append("../")
    from db.db import *

from fobjs.fobj import get_fobj
from fobjs.misc import get_listeners, _listeners
from random import shuffle
from log_class import Log, logging
from time import time

logger = logging.getLogger(__name__)
log = logger
populate_preload_all_locked = False


DEFAULT_RATING = 6
DEFAULT_SCORE = 5
DEFAULT_TRUE_SCORE = (
                        (DEFAULT_RATING * 2 * 10) + 
                        (DEFAULT_SCORE * 10)
                     ) / 2.0
DEFAULT_PERCENT_PLAYED = 0

def wait():
    Gdk.threads_leave()
    return

def insert_missing_files_for_uid(uid):
    insert_spec = {
        'default_rating': DEFAULT_RATING,
        'default_score': DEFAULT_SCORE,
        'default_true_score': DEFAULT_TRUE_SCORE,
        'default_percent_played': DEFAULT_PERCENT_PLAYED,
        'uid': uid
    }
    insert_sql = """INSERT INTO user_song_info (uid, fid, rating, score, 
                                                true_score, percent_played) """

    sql = """SELECT DISTINCT %(uid)s AS uid, 
                    f.fid AS fid, 
                    %(default_rating)s AS rating, 
                    %(default_score)s AS score, 
                    %(default_true_score)s AS true_score,
                    %(default_percent_played)s AS percent_played
             FROM file_locations f LEFT JOIN user_song_info usi ON 
                                    usi.uid = %(uid)s AND
                                    usi.fid = f.fid
             WHERE usi.fid IS NULL"""

    results = get_results_assoc_dict(sql, insert_spec)
    for r in results:
        print "MISSING:", r

    print sql % insert_spec
    print "INSERTING"
    inserted = get_results_assoc_dict(insert_sql + sql + " RETURNING * ",
                                      insert_spec)
    for r in inserted:
        print "INSERTED:", r


def get_files_from_preload(listeners=None):
    logger.debug("get_files_from_preload()")
    listeners = _listeners(listeners)

    sql = """DELETE FROM preload p 
             WHERE fid IN (
                SELECT p.fid 
                FROM user_song_info usi, users u, preload p
                WHERE u.listening = true AND u.uid = usi.uid AND
                      usi.rating = 0 AND p.fid = usi.fid
            )"""
    query(sql)

    qued_sql = """SELECT *
                  FROM preload
                  WHERE uid = %(uid)s AND reason LIKE '%%FROM Search%%'
                  ORDER BY plid
                  LIMIT 1"""

    select_sql = """SELECT *
                    FROM preload
                    WHERE uid = %(uid)s
                    ORDER BY plid
                    LIMIT 1"""

    queries = [qued_sql, select_sql]
    delete_sql = """DELETE FROM preload 
                    WHERE plid = %(plid)s"""
    items = []
    for listener in listeners:
        for q in queries:
            dbInfo = get_assoc_dict(q, listener)
            if dbInfo and dbInfo != {}:
                query(delete_sql, dbInfo)
                print "+"*100
                print "get_file_from_preload:", dbInfo
                item = get_fobj(**dbInfo)
                print "ITEM:", item.filename
                items.append(item)
                break # for query in queries
    return items

def get_users():
    sql = """SELECT uid, uname, listening, admin
             FROM users
             ORDER BY admin DESC, uname"""

    return get_results_assoc_dict(sql)

def initial_picker():
    totals = totals_in_preload()
    run = False
    if not totals:
        run = True
    for total in totals:
        if total['total'] < target_preload_length:
            run = True

    if run:
        populate_preload()

def move_to_preload(uid):
    sql = """INSERT INTO
             preload (fid, uid, reason)
             SELECT fid, uid, reason
             FROM preload_cache
             WHERE fid NOT IN (SELECT DISTINCT fid FROM preload) AND
                   uid = %(uid)s"""
    query(sql, {'uid': uid})

    sql = """DELETE FROM preload_cache WHERE uid = %(uid)s"""
    query(sql, {'uid': uid})

def move_to_preload_cache(uid):
    sql = """INSERT INTO
             preload_cache (fid, uid, reason)
             SELECT fid, uid, reason
             FROM preload
             WHERE fid NOT IN (SELECT DISTINCT fid FROM preload_cache) AND
                   uid = %(uid)s"""
    query(sql, {'uid': uid})

    sql = """DELETE FROM preload WHERE uid = %(uid)s"""
    query(sql, {'uid': uid})

def populate_preload_for_all_users():
    global populate_preload_all_locked
    if populate_preload_all_locked:
        return True
    populate_preload_all_locked = True
    try:
        populate_preload()
    except Exception as e:
      log.error("Exception:%s" % e)
      print sys.exc_info()[0]

    populate_preload_all_locked = False
    return True


def populate_preload(uid=None, listeners=None):
    wait()
    print "populate_preload:", uid
    totals = totals_in_preload()
    listeners = _listeners(listeners)

    if uid is None:
        start = time()
        for l in listeners:
            populate_preload(l['uid'], listeners)
        users = get_users()
        for u in users:
            populate_preload(u['uid'], [u])
            if u['listening']:
                move_to_preload(u['uid'])
            else:
                move_to_preload_cache(u['uid'])
        logger.debug("populate_preload outer loop running_time:%s" % 
                     (time() - start))
        return True

    for total in totals:
        if total['uid'] == uid and total['total'] >= target_preload_length:
            return True

    populate_pick_from(listeners)
    wait()
    true_scores = make_true_scores_list()
    wait()
    uname = ""
    for u in listeners:
        if u['uid'] == uid:
            uname = u['uname']

    out_of = []
    for true_score in true_scores:
        wait()
        dbInfos = get_random_unplayed(uid=uid, uname=uname)
        for dbInfo in dbInfos:
            wait()
            insert_into_preload(dbInfo, listeners)
            wait()
            remove_from_pick_from(**dbInfo)
            wait()

        if true_score in out_of:
            continue
        dbInfos = get_files_for_true_score(uid=uid, true_score=true_score, 
                                           uname=uname)
        if not dbInfos:
            out_of.append(true_score)

        for dbInfo in dbInfos:
            wait()
            insert_into_preload(dbInfo, listeners)
            wait()
            remove_from_pick_from(**dbInfo)
            wait()

        


    return True

def get_files_for_true_score(uid, true_score, convert_to_fobj=False,
                             limit=1, uname="", remove=True):
    log.debug("get_files_for_true_score uid:%s true_score:%s "
              "convert_to_fobj:%s limit:%s uname:%s" % 
              (uid, true_score, convert_to_fobj, limit, uname))
    sql = """SELECT *
             FROM user_song_info usi,
                  pick_from pf
             WHERE pf.fid = usi.fid AND
                   usi.uid = %(uid)s AND
                   true_score >= %(true_score)s
             ORDER BY ultp NULLS FIRST, RANDOM()
             LIMIT {limit}""".format(limit=limit)
    sql_args = {
        'uid': uid,
        'true_score': true_score
    }
    log.debug("get_files_for_true_score:%s", mogrify(sql, sql_args))
    dbInfos = get_results_assoc_dict(sql, sql_args)
    sample = []
    if limit == 1:
        sample = get_files_for_true_score(uid, true_score, convert_to_fobj=False,
                                          limit=10, uname=uname, remove=False)
        log.debug("== Samples for %s %s ==" % (uname, true_score))
        for s in sample:
            sql = """SELECT basename 
                     FROM file_locations 
                     WHERE fid = %(fid)s
                     LIMIT 1"""
            r = get_assoc_dict(sql, s)
            log.debug("sample: %s %s" % (s['ultp'], r['basename'], ))


    for dbInfo in dbInfos:
        dbInfo['reason'] = 'chosen for %s true_score >= %s' % (
            uname, true_score)
        if limit == 1:
            sql = """SELECT basename 
                         FROM file_locations 
                         WHERE fid = %(fid)s
                         LIMIT 1"""
            r = get_assoc_dict(sql, dbInfo)
            log.debug("sample PICKED: %s %s %s" % (
                true_score, dbInfo['ultp'], r['basename'], ))
        if remove:
            remove_from_pick_from(**dbInfo)

    if not convert_to_fobj:
        return dbInfos
    fobjs = []
    for dbInfo in dbInfos:
        fobj = get_fobj(**dbInfo)
        if fobJ:
            fobjs.append(fobj)
    return fobjs


def get_random_unplayed(uid, convert_to_fobj=False,
                        limit=1, uname=""):
    log.debug("get_random_unplayed uname:%s" % uname)
    sql = """SELECT *
             FROM user_song_info usi,
                  pick_from pf
             WHERE pf.fid = usi.fid AND
                   usi.uid = %(uid)s AND
                   usi.ultp IS NULL
             ORDER BY RANDOM()
             LIMIT {limit}""".format(limit=limit)
    sql_args = {
        'uid': uid,
    }
    dbInfos = get_results_assoc_dict(sql, sql_args)
    for dbInfo in dbInfos:
        dbInfo['reason'] = 'chosen for %s random unplayed' % (
            uname)
        remove_from_pick_from(**dbInfo)
    return dbInfos

def remove_from_pick_from(fid, **kwargs):
    log.debug("remove_from_pick_from:%s", fid)
    sql_args = {'fid': fid}
    sql = """DELETE FROM pick_from WHERE fid = %(fid)s"""
    # It's IMPORTANT to EXPLICITLY remove the fid, because 
    # not all files have an artist.
    query(sql, sql_args)


    sql = """DELETE FROM pick_from 
             WHERE fid IN (
                     SELECT fid
                     FROM file_artists
                     WHERE aid IN (
                             SELECT aid 
                             FROM file_artists
                             WHERE fid = %(fid)s
                    )
             )"""
    logger.debug("remove_from_pick_from:%s" % mogrify(sql, sql_args))
    query(sql, sql_args)

def populate_pick_from(listeners=None):
    logger.debug("populate_pick_from()")
    listeners = _listeners(listeners)
    clear_pick_from()
    listeners = _listeners(listeners)
    for l in listeners:
        insert_missing_files_for_uid(l['uid'])

    sql = """INSERT INTO pick_from (fid)
             SELECT fid FROM files"""
    query(sql)
    remove_rated_zero(listeners)
    remove_recently_played(listeners)
    remove_preload_from_pick_from(listeners)
    remove_disabled_genres_from_pick_from()
    remove_artists_already_in_preload()
    remove_missing_files_from_pick_from()
    logger.debug("/populate_pick_from()")

def remove_artists_already_in_preload():
    log.debug("remove_artists_already_in_preload()")
    sql = """DELETE FROM pick_from 
             WHERE fid IN (
                     SELECT fid
                     FROM file_artists
                     WHERE aid IN (
                             SELECT aid 
                             FROM file_artists
                             WHERE fid IN (
                                    SELECT fid
                                    FROM preload
                             )
                     )
             )"""
    query(sql)

def remove_missing_files_from_pick_from():
    log.debug("remove_missing_files_from_pick_from()")
    sql = """DELETE FROM pick_from
             WHERE fid IN (
                        SELECT DISTINCT fid 
                        FROM pick_from 
                        WHERE fid NOT IN (
                            SELECT DISTINCT fid FROM file_locations
                        )
                   )"""
    query(sql)
    log.debug("done")

def clear_pick_from():
    sql = """TRUNCATE pick_from"""
    query(sql)

def remove_rated_zero(listeners=None):
    log.debug("remove_rated_zero()")
    listeners = _listeners(listeners)

    for listener in listeners:
        sql = """DELETE FROM pick_from 
                 WHERE fid IN (SELECT fid 
                               FROM user_song_info 
                               WHERE rating = 0 AND
                                     uid = %(uid)s)"""
        query(sql, listener)

def count_files():
    sql = """SELECT count(*) AS total FROM files"""
    return get_assoc_dict(sql)['total']

def remove_recently_played(listeners=None):

    listeners = _listeners(listeners)
    total = count_files()
    limit = int(total * 0.01)
    for listener in listeners:
        log.debug("remove_recently_played:%s" % listener)
        sql = """DELETE FROM pick_from 
                 WHERE fid IN (
                           SELECT uh.fid
                           FROM user_history uh
                           WHERE uh.uid = %(uid)s AND
                                 time_played IS NOT NULL AND
                                 uh.fid IS NOT NULL
                           ORDER BY time_played DESC
                           LIMIT {limit}
                       )""".format(limit=limit)
        log.debug('recently_played:%s' % listener)
        log.debug(mogrify(sql, listener))
        query(sql, listener)

def remove_preload_from_pick_from(listeners=None):

    listeners = _listeners(listeners)

    for listener in listeners:
        log.debug("remove_preload_from_pick_from:%s" % listener)
        sql = """DELETE FROM pick_from 
                 WHERE fid IN (
                        SELECT fid 
                        FROM preload 
                        WHERE uid = %(uid)s
                 )"""
        query(sql, listener)

def get_preload(convert_to_fobj=False):
    sql = """SELECT *
             FROM preload
             ORDER BY plid, uid"""
    results = get_results_assoc_dict(sql)
    if not convert_to_fobj:
        return results
    fobj_results = []
    for r in results:
        fobj = get_fobj(**r)
        if fobj:
            fobj_results.append(fobj)
    return fobj_results

def gen_true_score_list(scores, whole=True):
    true_scores = []
    for true_score in scores:
        if whole:
            iter_count = int(round((true_score * 0.1)))
        else:
            iter_count = int(round((true_score * 0.1) * .5 ))
        if iter_count <= 0:
            iter_count = 1
        for i in range(0, iter_count):
            true_scores.append(str(true_score))

    return true_scores

def make_true_scores_list():

    by_tens = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 120]
    by_fives = []

    # shuffle(scores)

    true_scores = (gen_true_score_list(by_tens, True) +
                   gen_true_score_list(by_fives, False))
    
    shuffle(true_scores)
    # print "true_scores:", true_scores
    return true_scores

def insert_into_preload(dbInfo, listeners=None):
    listeners = _listeners(listeners)
    table = 'preload_cache'
    for l in listeners:
        if l['uid'] == dbInfo['uid']:
          table = 'preload'

    sql = """INSERT INTO {table} (fid, uid, reason)
             VALUES(%(fid)s, %(uid)s, %(reason)s)""".format(table=table)
    query(sql, dbInfo)

def totals_in_preload():
    """ Table "public.preload_cache"
     Column |  Type   | Modifiers 
    --------+---------+-----------
     fid    | integer | not null
     uid    | integer | not null
     reason | text    | 
    """
    sql = """SELECT uid, count(*) as total FROM preload GROUP BY uid"""
    totals1 = get_results_assoc_dict(sql)
    sql = """SELECT uid, count(*) as total FROM preload_cache GROUP BY uid"""
    totals2 = get_results_assoc_dict(sql)

    totals = totals1 + totals2
    print "TOTALS:"
    pprint(totals)
    listeners = _listeners()
    for l in listeners:
        found = False
        for t in totals:
            if t['uid'] == l['uid']:
                found = True
        if not found:
            total_data = {
                'uid': l['uid'],
                'total': 0
            }
            totals.append(total_data)
    print "TOTALS:"
    pprint(totals)
    return totals

def clear_preload():
    sql = """TRUNCATE preload"""
    query(sql)

def remove_disabled_genres_from_pick_from():
    sql = """DELETE FROM pick_from 
             WHERE fid IN (
                SELECT fid 
                FROM genres g, file_genres fg 
                WHERE enabled = false AND fg.gid = g.gid
             )"""
    query(sql)

true_scores = make_true_scores_list()
target_preload_length = len(true_scores)

if __name__ == "__main__":

    # clear_preload()
    sql = """DELETE FROM preload WHERE uid = 1"""
    query(sql)
    populate_preload()
    preload = get_preload(True)
    for p in preload:
        print p.filename
