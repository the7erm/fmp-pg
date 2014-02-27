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
from datetime import date

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

def calculate_true_score(fid):
    q = pg_cur.mogrify("""UPDATE user_song_info usi
                          SET true_score =  """+CALCULATE_TRUESCORE_FORMULA+"""
                          WHERE fid = %s AND uid IN 
                                (SELECT uid FROM users WHERE listening = true)
                          RETURNING *""",
                      (fid,))
    # print "q:",q
    res = get_results_assoc(q)
    for r in res:
        pprint.pprint(dict(r))
        test_true_score_calculation(r)
    return res

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

def calculate_true_score_for_selected(fid):
    res = get_results_assoc(
      """UPDATE user_song_info usi
         SET true_score = """+CALCULATE_TRUESCORE_FORMULA+"""
         WHERE fid = %s AND uid IN 
                (SELECT uid FROM users WHERE listening = true AND
                                             selected = true)
         RETURNING *""",
         (fid,))
    for r in res:
        test_true_score_calculation(r)
    return res


def calculate_true_score_for_uid(fid, uid):
    q = """UPDATE user_song_info usi
           SET true_score = """+CALCULATE_TRUESCORE_FORMULA+""" 
           WHERE fid = %s AND uid = %s
           RETURNING *"""
    
    mog = pg_cur.mogrify(q, (fid, uid))
    # print mog
    # res = get_results_assoc(mog)
    res = get_results_assoc(mog)
    for r in res:
      test_true_score_calculation(r)
    return res

def caclulate_true_score_for_usid(usid):
    res = get_results_assoc(
        """UPDATE user_song_info usi
           SET true_score = """+CALCULATE_TRUESCORE_FORMULA+"""
           WHERE usid = %s
           RETURNING *""",
           (usid,))
    for r in res:
        test_true_score_calculation(r)
    return res

def caclulate_true_score_for_uname(uname, fid):
    uinfo = get_assoc("""SELECT uid FROM users WHERE uname = %s""", (uname,))
    return calculate_true_score_for_uid(fid, uinfo['uid'])

def rate_selected(fid, rating):
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s, 
                                     true_score = """+RATE_TRUESCORE_FORMULA+"""
                                   WHERE fid = %s AND uid IN 
                                      (SELECT uid FROM users 
                                       WHERE listening = true AND
                                             selected = true)
                                   RETURNING *""",
                               (rating, rating, fid,))
    updated_again = calculate_true_score_for_selected(fid)
    return updated_again or updated or []

def rate_for_uid(fid, uid, rating):
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s,
                                       true_score = """+RATE_TRUESCORE_FORMULA+"""
                                   WHERE fid = %s AND 
                                         uid = %s RETURNING *""", 
                                   (rating, rating, fid, uid))
    updated_again = calculate_true_score_for_uid(fid, uid)
    return updated_again or updated or []

def rate_for_usid(usid, rating):
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET rating = %s,
                                       true_score = """+RATE_TRUESCORE_FORMULA+"""
                                   WHERE usid = %s RETURNING *""", 
                                   (rating, rating, usid))
    updated_again = caclulate_true_score_for_usid(usid)
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


def set_score_for_uid(fid, uid, score):
    updated = get_results_assoc("""UPDATE user_song_info usi
                                   SET score = %s
                                   WHERE fid = %s AND uid = %s
                                   RETURNING *""",
                                 (score, fid, uid))
    updated_again = calculate_true_score_for_uid(fid, uid)
    return updated_again or updated or []
