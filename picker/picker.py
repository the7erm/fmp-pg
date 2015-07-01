
import os
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from fobjs.fobj import get_fobj
from fobjs.misc import get_listeners, _listeners
from random import shuffle

def wait():
    return

def get_files_from_preload(listeners=None):
    listeners = _listeners(listeners)

    sql = """SELECT *
             FROM preload
             WHERE uid = %(uid)s
             ORDER BY plid
             LIMIT 1"""

    items = []
    for listener in listeners:
        dbInfo = get_assoc_dict(sql, listener)
        if dbInfo != {}:
            sql = """DELETE FROM preload 
                     WHERE plid = %(plid)s"""
            query(sql, dbInfo)
            print "get_file_from_preload:", dbInfo
            items.append(get_fobj(**dbInfo))
    return items

def get_users():
    sql = """SELECT uid, uname, listening, admin
             FROM users
             ORDER BY admin DESC, uname"""

    return get_results_assoc_dict(sql)

def initial_picker():
    totals = totals_in_preload()
    run = False
    for total in totals:
        if total['total'] < target_preload_length:
            run = True

    if run:
        populate_preload()

def populate_preload(uid=None, listeners=None):
    wait()
    print "populate_preload:", uid
    totals = totals_in_preload()
    listeners = _listeners(listeners)

    if uid is None:
        users = get_users()
        for u in users:
            populate_preload(u['uid'], users)
        return True

    for total in totals:
        if total['uid'] == uid and total['total'] >= target_preload_length:
            return True

    populate_pick_from(listeners)
    true_scores = make_true_scores_list()
    uname = ""
    for u in listeners:
        if u['uid'] == uid:
            uname = u['uname']
    for true_score in true_scores:
        dbInfos = get_files_for_true_score(uid=uid, true_score=true_score, 
                                           uname=uname)
        for dbInfo in dbInfos:
            insert_into_preload(dbInfo)
            remove_from_pick_from(**dbInfo)

    return True

def get_files_for_true_score(uid, true_score, covert_to_fobj=False,
                             limit=1, uname=""):
    sql = """SELECT *
             FROM user_song_info usi,
                  pick_from pf
             WHERE pf.fid = usi.fid AND
                   usi.uid = %(uid)s AND
                   true_score >= %(true_score)s
             ORDER BY ultp
             LIMIT {limit}""".format(limit=limit)
    sql_args = {
        'uid': uid,
        'true_score': true_score
    }
    dbInfos = get_results_assoc_dict(sql, sql_args)

    for dbInfo in dbInfos:
        dbInfo['reason'] = 'chosen for %s true_score >= %s' % (
            uname, true_score)

    return dbInfos

def remove_from_pick_from(fid, reason="", **kwargs):
    sql = """DELETE FROM pick_from WHERE fid = %(fid)s"""
    query(sql, {'fid': fid, 'reason': reason})

def populate_pick_from(listeners=None):
    listeners = _listeners(listeners)
    clear_pick_from()
    listeners = _listeners(listeners)
    sql = """INSERT INTO pick_from (fid)
             SELECT fid FROM files"""
    query(sql)
    remove_rated_zero(listeners)
    remove_recently_played(listeners)
    remove_preload_from_pick_from(listeners)
    

def clear_pick_from():
    sql = """TRUNCATE pick_from"""
    query(sql)

def remove_rated_zero(listeners=None):
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
        sql = """DELETE FROM pick_from 
                 WHERE fid IN (
                           SELECT uh.id
                           FROM user_history uh
                           WHERE uh.uid = %(uid)s AND
                                 time_played IS NOT NULL AND
                                 uh.id_type = 'f'
                           ORDER BY time_played DESC
                           LIMIT {limit}
                       )""".format(limit=limit)
        query(sql, listener)

def remove_preload_from_pick_from(listeners=None):
    listeners = _listeners(listeners)

    for listener in listeners:
        sql = """DELETE FROM pick_from 
                 WHERE fid IN (
                        SELECT fid 
                        FROM preload 
                        WHERE uid = %(uid)s
                 )"""
        query(sql, listener)

def get_preload():
    sql = """SELECT *
             FROM preload
             ORDER BY plid, uid"""
    return get_results_assoc_dict(sql)

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

    by_tens = [0, 10, 20, 30, 40, 50, 60, 70]
    by_fives = [80, 85, 90, 95]

    # shuffle(scores)

    true_scores = (gen_true_score_list(by_tens, True) +
                   gen_true_score_list(by_fives, False))
    
    shuffle(true_scores)
    # print "true_scores:", true_scores
    return true_scores

def insert_into_preload(dbInfo):
    sql = """INSERT INTO preload (fid, uid, reason)
             VALUES(%(fid)s, %(uid)s, %(reason)s)"""
    query(sql, dbInfo)

def totals_in_preload():
    sql = """SELECT uid, count(*) as total FROM preload GROUP BY uid"""
    return get_results_assoc_dict(sql)

def clear_preload():
    sql = """TRUNCATE preload"""
    query(sql)

true_scores = make_true_scores_list()
target_preload_length = len(true_scores)

if __name__ == "__main__":
    # clear_preload()
    populate_preload()
    preload = get_preload()
    for p in preload:
        print p
