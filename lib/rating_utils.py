#!/usr/bin/env python2
# lib/rating_utils.py -- Standard functions for rating files.
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
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
import time
import math
from listeners import listeners
import fobj
from datetime import date, datetime
from pytz import utc
import pprint

# OLD, but keeping it around because what I'm doing is an experiment.
CALCULATE_TRUESCORE_FORMULA = """(
    (
      (rating * 2 * 10.0) + 
      (score * 10.0) + 
      percent_played
    ) / 3
)"""

CALCULATE_TRUESCORE_FORMULA = """
(((usi.rating * 2 * 10.0) + 
               (usi.score * 10.0) + 
               (usi.percent_played) + 
(SELECT CASE WHEN avg(percent_played) IS NOT NULL THEN
           avg(percent_played)
        ELSE
          50
        END
 FROM user_history uh 
 WHERE uhid IN (
     SELECT uhid 
     FROM user_history uh2
     WHERE uh2.uid = usi.uid AND 
          uh2.id = usi.fid AND 
          uh2.id_type = 'f' AND
          usi.uid = 1 AND
          percent_played > 0
     ORDER BY CASE WHEN time_played IS NULL THEN 0 ELSE 1 END,
              time_played DESC
     LIMIT 5
 )) 
) / 4)
"""

# OLD, but keeping it around because what I'm doing is an experiment.
RATE_TRUESCORE_FORMULA = """(
  (
      (%s * 2 * 10.0) +
      (score * 10.0) + 
      percent_played
  ) / 3
)"""

RATE_TRUESCORE_FORMULA = """
(((%s * 2 * 10.0) + 
               (usi.score * 10.0) + 
               (usi.percent_played) + 
(SELECT CASE WHEN avg(percent_played) IS NOT NULL THEN
           avg(percent_played)
        ELSE
          50
        END
 FROM user_history uh 
 WHERE uhid IN (
     SELECT uhid 
     FROM user_history uh2
     WHERE uh2.uid = usi.uid AND 
          uh2.id = usi.fid AND 
          uh2.id_type = 'f' AND
          usi.uid = 1 AND
          percent_played > 0
     ORDER BY CASE WHEN time_played IS NULL THEN 0 ELSE 1 END,
              time_played DESC
     LIMIT 5
 )) 
) / 4)
"""

def calculate_true_score_for_fid_uid(fid, uid):

    # Get the last 5 plays
    print "calculate_true_score_for_fid_uid", fid, uid
    print "1"*100
    averages = get_results_assoc("""SELECT percent_played
                                  FROM user_history
                                  WHERE id = %s AND uid = %s AND 
                                        id_type = 'f' AND percent_played > 0
                                  ORDER BY time_played DESC
                                  LIMIT 5""",
                              (fid, uid))

    if not averages:
        average = 50
    else:
        total = 0
        cnt = 0
        for a in averages:
          total += float(a['percent_played'])
          cnt += 1
        average = (total / cnt)
    print "2"*100
    q = """UPDATE user_song_info 
           SET true_score = ((
              (rating * 2 * 10.0) + 
              (score * 10.0) +
              (percent_played) +
              """+str(average)+"""
           ) / 4) 
           WHERE uid = %s AND fid = %s
           RETURNING *"""

    res = get_assoc(q, (uid, fid))
    title = "%s%s%s" % ("-"*10,"--[true score]--","-"*10)
    print title
    print "uid:", uid
    print "averages:", averages
    print "average:", average
    print "true score:",
    if res:
        pprint.pprint(dict(res))
    else:
        print "NO RES"
    print "-"*len(title)
    print "3x"*50
    return res


def calculate_true_score(fid):
    # Get all the listeners.
    listeners = get_results_assoc("""SELECT uid 
                                     FROM users 
                                     WHERE listening = true""")

    results = []
    for l in listeners:
        res = calculate_true_score_for_fid_uid(fid, l['uid'])
        if res:
          results.append(res)

    return results


def test_true_score_calculation(res):
    return
    history = get_results_assoc("""SELECT *
                                   FROM user_history
                                   WHERE uid = %s AND 
                                         id = %s AND
                                         id_type = 'f' AND
                                         percent_played > 0
                                   ORDER BY CASE WHEN time_played IS NULL THEN 0 ELSE 1 END,
                                            time_played DESC
                                   LIMIT 5""",
                                (res['uid'], res['fid']))
    if not history:
        return
    total_percent_played = 0
    for h in history:
        total_percent_played += h['percent_played']
    average = float(total_percent_played) / len(history)
    if not total_percent_played:
        total_percent_played = 50
    true_score = ((res['rating'] * 10 * 2) + 
                  (res['score'] * 10) + 
                  res['percent_played'] + 
                  average) / 4
    print "res['true_score']:", res['true_score'], "true_score:",true_score


def get_selected_listener():
    q = """SELECT uid 
           FROM users 
           WHERE listening = true AND selected = true
           LIMIT 1"""
    listener = get_assoc(q)
    if not listener:
        q = """SELECT uid
               FROM users 
               WHERE listening = true LIMIT 1"""
        listener = get_assoc(q)

    return listener

def calculate_true_score_for_selected(fid):
    listener = get_selected_listener()
    if not listener:
        return

    return calculate_true_score_for_uid(fid, uid)


def calculate_true_score_for_uid(fid, uid):
    return calculate_true_score_for_fid_uid(fid, uid)

def calculate_true_score_for_usid(usid):
    q = """SELECT fid, uid FROM user_song_info WHERE usid = %s"""
    usi = get_assoc(q, (usid,))
    return calculate_true_score_for_uid(usi['fid'], usi['uid'])

def calculate_true_score_for_uname(uname, fid):
    uinfo = get_assoc("""SELECT uid FROM users WHERE uname = %s""", (uname,))
    return calculate_true_score_for_uid(fid, uinfo['uid'])

def rate_selected(fid, rating):
    listener = get_selected_listener()
    if not listener:
        return

    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s
                                   WHERE fid = %s AND uid = %s
                                   RETURNING *""",
                               (rating, fid, listener['uid']))
    updated_again = calculate_true_score_for_uid(fid, listener['uid'])
    return updated_again or updated or []

def rate_for_uid(fid, uid, rating):
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s
                                   WHERE fid = %s AND 
                                         uid = %s 
                                   RETURNING *""", 
                                   (rating, fid, uid))
    updated_again = calculate_true_score_for_uid(fid, uid)
    return updated_again or updated or []

def rate_for_usid(usid, rating):
    print "rate_for_usid:", usid, rating
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s
                                   WHERE usid = %s RETURNING *""", 
                                   (rating, usid))
    print "updated:", updated
    updated_again = calculate_true_score_for_usid(usid)
    print "4"*100
    print "updated_again:", updated_again
    print "--made it."
    return updated_again or updated or []


def rate_for_uname(fid, uname, rating):
    uinfo = get_assoc("""SELECT uid FROM users WHERE uname = %s""", (uname, ))
    if not uinfo:
        return []

    return rate_for_uid(fid, uinfo['uid'], rating)


def rate(usid=None, uid=None, fid=None, rating=None, selected=None, uname=None):
    print "rate: usid:", usid, "uid:", uid, "fid:", fid, "rating:", rating, \
          "selected:", selected, "uname:", uname
    try:
        rating = int(rating)
    except:
        return []
    if rating < 0 or rating > 6:
        return []

    if selected is not None and selected:
        return rate_selected(fid, rating)

    if usid is not None:
        return rate_for_usid(usid, rating)

    if uid is not None and fid is not None:
        return rate_for_uid(fid, uid, rating)

    if uname is not None and fid is not None:
        return rate_for_uname(fid, uname, rating)

    return []

def get_time():
    local_offset = time.timezone
    if time.daylight:
        local_offset = time.altzone
    return time.time() + local_offset

def set_score_for_uid(fid, uid, score):
    print "set_score_for_uid"
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET score = %s
                                   WHERE fid = %s AND uid = %s
                                   RETURNING *""",
                                 (score, fid, uid))
    updated_again = calculate_true_score_for_uid(fid, uid)
    print "/set_score_for_uid"
    return updated_again or updated or []


def convert_when_to_dt(when):
    if when is None:
        when = datetime.now()

    if isinstance(when, (str, unicode)):
        when = datetime.now()

    if isinstance(when, float):
        year_of_seconds = 365 * 60 * 60 * 24
        if when <= year_of_seconds:
            # The time is off because the mp3 player didn't connect
            # to a wifi so use the current time - when
            when = get_time() - when
        when = datetime.fromtimestamp(when)
        print "when from float:", when, when.tzinfo

    if when.tzinfo is None:
        when = when.replace(tzinfo=utc)
        print "when with replaced tzinfo:", when, when.tzinfo

    return when

def update_user_history(update_data):

    sql = """SELECT uhid, id, id_type
             FROM user_history
             WHERE uid = %(uid)s
             ORDER BY time_played DESC
             LIMIT 1"""

    last_file_played = get_assoc(sql, update_data)
    uhid = -1
    if last_file_played and \
       last_file_played['id'] == update_data.get('id') and \
       last_file_played['id_type'] == update_data.get('id_type'):
        uhid = last_file_played['uhid']

    if uhid == -1:
        sql = """INSERT INTO user_history 
                   (uid, id, id_type,
                    percent_played,
                    time_played,
                    date_played,
                    reason)
                 VALUES (%(uid)s, %(id)s, %(id_type)s, 
                         %(percent_played)s, 
                         %(time_played)s, 
                         %(date_played)s, 
                         %(reason)s) RETURNING *"""
        try:
            inserted = get_assoc(sql, update_data)
            uhid = inserted['uhid']
            print "- user_history inserted"
        except psycopg2.IntegrityError, err:
            print "IntegrityError:", err
            query("COMMIT;")
            sql = """SELECT uhid, id, id_type
                     FROM user_history
                     WHERE uid = %(uid)s AND
                           date_played = %(when_date)s AND
                           id = %(id)s AND
                           id_type = %(id_type)s
                     ORDER BY time_played DESC
                     LIMIT 1"""
            todays_data = get_assoc(sql, update_data)
            if todays_data:
                uhid = todays_data['uhid']
    id_type = update_data.get("id_type")
    if id_type == 'f':
        sql = """UPDATE user_history uh
                 SET true_score = ufi.true_score,
                     score = ufi.score,
                     rating = ufi.rating,
                     percent_played = %(percent_played)s,
                     time_played = %(when)s
                 FROM user_song_info ufi
                 WHERE uhid = %(uhid)s AND
                       fid = %(fid)s"""
    else:
        sql = """UPDATE user_history uh
                 SET percent_played = %(percent_played)s,
                     time_played = %(when)s
                 WHERE uhid = %(uhid)s"""
    fid = update_data.get('id')
    uid = update_data.get('uid')
    try:
        update_data['uhid'] = uhid
        print pg_cur.mogrify(sql, update_data)
        query(sql, update_data)
        print "- user_history updated"
    except psycopg2.IntegrityError, err:
        print "IntegrityError:", err
        query("COMMIT;")

    if id_type == 'f':
        
        calculate_true_score_for_fid_uid(fid, uid)
        try:
            print pg_cur.mogrify(sql, update_data)
            query(sql, update_data)
            print "- user_history updated 2"
        except psycopg2.IntegrityError, err:
            print "IntegrityError:", err
            query("COMMIT;")

def mark_as_played(fid, uid, when, percent_played, reason="", *args, **kwargs):
    print "mark_as_played"
    print "when:",type(when), when
    when = convert_when_to_dt(when)

    update_data = {
      'uid': uid,
      'id': fid,
      'fid': fid,
      'id_type': 'f',
      'percent_played': percent_played,
      'time_played': when,
      'date_played': when.date(),
      'reason': reason,
      'ltp': when,
      'when': when,
      'when_date': when.date()
    }

    sql = """UPDATE files 
             SET ltp = %(when)s
             WHERE fid = %(id)s"""
    query(sql, update_data)
    print "- files updated"

    sql = """UPDATE artists a SET altp = %(when)s
             FROM file_artists fa 
             WHERE fa.aid = a.aid AND 
                   fa.fid = %(id)s"""
    query(sql, update_data)
    print "- artists updated"

    
    sql = """UPDATE user_song_info 
             SET ultp = %(when)s, percent_played = %(percent_played)s 
             WHERE fid = %(id)s AND uid = %(uid)s"""
    query(sql, update_data)
    print "- user_song_info updated"

    sql = """SELECT * FROM file_artists fa WHERE fid = %(id)s"""
    artists = get_results_assoc(sql, update_data)

    for a in artists:
        print "a:",a['aid']
        sql = """INSERT INTO user_artist_history (time_played, date_played, 
                                                  uid, aid)
                 VALUES(%(when)s, %(when_date)s, %(uid)s, %(aid)s)"""
        try:
            update_data['aid'] = a['aid']
            query(sql, update_data)
            print "- user_artist_history inserted"
        except psycopg2.IntegrityError, err:
            print "IntegrityError:", err
            query("COMMIT;")
        except Exception, err:
            print "- user_artist_history ERROR", err
            

    sql =  """UPDATE user_artist_history uah
              SET time_played = %(when)s,
                  date_played = %(when_date)s
              FROM user_song_info usi,
                   file_artists fa
              WHERE usi.uid = %(uid)s AND
                    fa.fid = usi.fid AND
                    uah.uid = usi.uid AND
                    uah.aid = fa.aid AND
                    usi.fid = %(id)s AND 
                    uah.date_played = %(when_date)s"""
    try:
        query(sql, update_data)
        print "- user_artist_history updated"
    except psycopg2.IntegrityError, err:
        print "IntegrityError:", err
        query("COMMIT;")

    update_user_history(update_data)

    print "-- done"
    
