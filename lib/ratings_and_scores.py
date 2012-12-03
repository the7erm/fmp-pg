#!/usr/bin/env python
# -*- coding: utf-8 -*-
# ratings_and_scores.py -- Handles file ratings and scores.
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

from __init__ import *
import time
import math
from listeners import listeners

class RatingsAndScores:
    def __init__(self, fid=None, listening=None, uids=None):
        self.ratings_and_scores = None
        self.fid = fid
        self.listening = listening
        self.uids = None
        self.expires = 0
        self.last_percent_played = -1
        self.artists = []

        if uids is not None:
            self.uids = uids

        self.get_all(force=True)

    def get_all(self, force=False):
        if self.listening:
            return self.get_all_listening(force=force)
        if self.uids:
            return self.get_all_by_uids(force=force)

    def get_all_by_uids(self, force=False):
        if time.time() < self.expires and not force:
            return self.ratings_and_scores

        self.ratings_and_scores = get_results_assoc(
            """SELECT * FROM users u, user_song_info usi
               WHERE uid IN ("""+self.prepare_uids()+""") AND usi.uid = u.uid AND 
                     usi.fid = %s
               ORDER BY admin DESC, uname""", 
               self.fid)

    def prepare_uids(self):
        self.uids_str = []
        for u in self.uids:
            self.uids_str.append(pg_cur.mogrify("%s",u))

        self.uids_str = ", ".join(self.uids_str)
        return self.uids_str

    def get_all_listening(self, force=False):
        if time.time() < self.expires and not force:
            return self.ratings_and_scores

        self.expires = time.time() + 60
        self.ratings_and_scores = get_results_assoc(
            """SELECT * FROM users u, user_song_info usi
               WHERE listening = true AND usi.uid = u.uid AND usi.fid = %s
               ORDER BY admin DESC, uname""", 
               (self.fid,))

        return self.ratings_and_scores

    def rate(self, uid=None, rating=None, uname=None, selected=None):
        if rating < 0 or rating > 5:
            return

        updated = None
        if selected is not None and selected:
            updated = get_results_assoc("""UPDATE user_song_info 
                                           SET rating = %s, 
                                               true_score = (((%s * 2 * 10) + 
                                                              (score * 10) + 
                                                              percent_played)
                                                             / 3)
                                           WHERE fid = %s AND uid IN 
                                                (SELECT uid FROM users 
                                                 WHERE listening = true AND
                                                       selected = true)
                                           RETURNING *""",
                                           (rating, rating, self.fid,))
            

        if uid is not None:
            updated = get_results_assoc("""UPDATE user_song_info 
                                           SET rating = %s,
                                               true_score = (((%s * 2 * 10) +
                                                              (score * 10) +
                                                              percent_played)
                                                             / 3)
                                           WHERE fid = %s AND 
                                                 uid = %s RETURNING *""", 
                                           (rating, rating, self.fid, uid))

        if uname is not None:
            updated = get_results_assoc("""UPDATE user_song_info 
                                           SET rating = %s, 
                                               true_score = (((%s * 2 * 10) +
                                                              (score * 10) +
                                                              percent_played)
                                                             / 3)
                                           WHERE fid = %s AND uid IN
                                                 (SELECT uid FROM users
                                                  WHERE uname=%s)
                                           RETURNING *""",
                                           (rating, rating, self.fid, uname))

        if updated:
            self.update(updated)
        return updated

    def get_selected(self):
        self.get_all()
        for u in self.ratings_and_scores:
            if u['selected'] == True:
                return u

        selected = get_assoc("""SELECT * FROM users u, user_song_info usi
                                WHERE u.uid = usi.uid AND u.listening = true AND
                                      u.selected = true AND usi.fid = %s 
                                LIMIT 1""", (self.fid,))

        if not selected:
            query("UPDATE users SET selected = false")
            selected = get_assoc("""SELECT * FROM users u, user_song_info usi
                                    WHERE u.uid = usi.uid AND 
                                          u.listening = true AND
                                          usi.fid = %s
                                    ORDER BY admin DESC, uname
                                    LIMIT 1""", 
                                    (self.fid,))
            if selected:
                query("UPDATE users SET selected = true WHERE uid = %s",
                      (selected['uid'],))
                selected['selected'] = True
        self.update([selected])

        return selected

    def update(self, updated):
        if not updated:
            return
        for u in updated:
            if not u:
                continue
            # print "updated:", pp.pprint(dict(u))
            found = False
            for k, rs in enumerate(self.ratings_and_scores):
                if u['uid'] == rs['uid']:
                    if u.has_key('rating'):
                        self.ratings_and_scores[k]['rating'] = u['rating']
                    if u.has_key('score'):
                        self.ratings_and_scores[k]['score'] = u['score']
                    if u.has_key('true_score'):
                        self.ratings_and_scores[k]['true_score'] = u['true_score']
                    if u.has_key('percent_played'):
                        self.ratings_and_scores[k]['percent_played'] = u['percent_played']
                    if u.has_key('selected'):
                        self.ratings_and_scores[k]['selected'] = u['selected']
                    found = True
                    break

            if not found:
                self.ratings_and_scores.append(u)

    def inc_score(self):
        if self.listening:
            self.inc_listeners_scores()
        
    def inc_listeners_scores(self):
        updated = get_results_assoc("""UPDATE user_song_info
                                       SET ultp = NOW(), score = score + 1 
                                       WHERE fid = %s AND uid IN (
                                            SELECT DISTINCT uid 
                                            FROM users 
                                            WHERE listening = true)
                                       RETURNING *""", 
                                       (self.fid, ))

        self.update(updated)

        updated = get_results_assoc("""UPDATE user_song_info 
                                       SET score = 10 
                                       WHERE fid = %s AND score > 10 AND 
                                             uid IN (SELECT DISTINCT uid 
                                                     FROM users 
                                                     WHERE listening = true)
                                       RETURNING *""", 
                                       (self.fid,))

        self.update(updated)
        self.calculate_true_score()
        self.update_history(self.last_percent_played)
        

    def deinc_score(self):
        if self.listening:
            self.deinc_listeners_scores()

    def deinc_listeners_scores(self):
        updated = get_results_assoc("""UPDATE user_song_info
                                       SET ultp = NOW(), score = score - 1 
                                       WHERE fid = %s AND uid IN (
                                            SELECT DISTINCT uid 
                                            FROM users 
                                            WHERE listening = true)
                                       RETURNING *""", 
                                       (self.fid, ))

        self.update(updated)

        updated = get_results_assoc("""UPDATE user_song_info 
                                       SET score = 1 
                                       WHERE fid = %s AND score <= 0 AND 
                                             uid IN (SELECT DISTINCT uid 
                                                     FROM users 
                                                     WHERE listening = true)
                                       RETURNING *""", 
                                       (self.fid, ))

        self.update(updated)
        self.calculate_true_score()
        self.update_history(self.last_percent_played)

    def calculate_true_score(self):
        global listeners
        if not listeners.listeners or not self.listening:
            return
        updated = get_results_assoc(
              """UPDATE user_song_info 
                 SET true_score = (((rating * 2 * 10.0) + (score * 10) + 
                                     percent_played) / 3) 
                 WHERE fid = %s AND uid IN 
                        (SELECT uid FROM users WHERE listening = true)
                 RETURNING *""",
                 (self.fid,))
        self.update(updated)

    def mark_as_played(self,percent_played=0):
        updated = get_results_assoc("""UPDATE user_song_info 
                                       SET ultp = NOW(), percent_played = %s 
                                       WHERE fid = %s AND uid IN (
                                            SELECT DISTINCT uid 
                                            FROM users 
                                            WHERE listening = true)
                                       RETURNING *""",
                                       (percent_played, self.fid,))

        self.update(updated)
        
        self.calculate_true_score()
        ceil_percent_played = math.ceil(percent_played)

        if self.last_percent_played != ceil_percent_played:
            if listeners.recheck_listeners:
                self.update_user_artists_ltp()
                self.update_history(percent_played)

            self.last_percent_played = ceil_percent_played

    def update_user_artists_ltp(self):
        if not self.listening or not listeners.listeners:
            return

        updated_artists = get_results_assoc("""UPDATE user_artist_history uah 
                                               SET time_played = NOW(), 
                                                   date_played = NOW() 
                                               FROM user_song_info usi, 
                                                    file_artists fa 
                                               WHERE usi.uid IN (
                                                       SELECT uid FROM users 
                                                       WHERE listening = true
                                                     ) AND 
                                                     fa.fid = usi.fid AND 
                                                     uah.uid = usi.uid AND 
                                                     uah.aid = fa.aid AND 
                                                     usi.fid = %s AND 
                                                     uah.date_played = current_date 
                                               RETURNING uah.*""",
                                               (self.fid,))

        # pp.pprint(updated_artists)
        update_association = {}

        for ua in updated_artists:
            key = "%s-%s" % (ua['aid'], ua['uid'])
            update_association[key] = ua

        # pp.pprint(update_association)
        for l in listeners.listeners:
            found = False 
            for a in self.artists:
                key = "%s-%s" % (a['aid'], l['uid'])
                if not update_association.has_key(key):
                    try:
                        user_artist_history = get_assoc(
                            """INSERT INTO 
                                    user_artist_history (uid, aid, time_played, 
                                                         date_played) 
                               VALUES(%s, %s, NOW(), current_date)
                               RETURNING *""", 
                               (l['uid'], a['aid']))
                        update_association[key] = user_artist_history
                    except psycopg2.IntegrityError, err:
                        query("COMMIT;")
                        print "(artist) psycopg2.IntegrityError:",err

    def update_history(self, percent_played=0):
        global listeners
        if not self.listening or not listeners.listeners:
            return
        print "UPDATE HISTORY"
        updated = get_results_assoc("""UPDATE user_history uh 
                                       SET true_score = ufi.true_score, 
                                           score = ufi.score, 
                                           rating = ufi.rating, 
                                           percent_played = ufi.percent_played, 
                                           time_played = NOW(), 
                                           date_played = current_date 
                                       FROM user_song_info ufi 
                                       WHERE 
                                            ufi.uid IN (SELECT uid 
                                                        FROM users 
                                                        WHERE listening = true) AND 
                                            uh.uid = ufi.uid AND 
                                            ufi.fid = uh.id AND 
                                            uh.id_type = 'f' AND 
                                            uh.date_played = DATE(ufi.ultp) AND 
                                            uh.id = %s 
                                       RETURNING uh.*""",
                                       (self.fid,))

        for l in listeners.listeners:
            found = False
            for u in updated:
                if u['uid'] == l['uid']:
                    found = True

            if not found:
                try:
                    user_history = get_assoc("""INSERT INTO 
                                                    user_history (uid, id, id_type,
                                                                  percent_played, 
                                                                  time_played,
                                                                  date_played) 
                                                VALUES (%s, %s, %s, %s, NOW(), 
                                                        current_date) 
                                                RETURNING *""",
                                                (l['uid'], self.fid, 'f', 
                                                 percent_played))

                    updated_user = get_assoc("""UPDATE user_history uh
                                                SET true_score = ufi.true_score,
                                                    score = ufi.score,
                                                    rating = ufi.rating,
                                                    percent_played = ufi.percent_played, 
                                                    time_played = NOW(),
                                                    date_played = current_date 
                                                FROM user_song_info ufi
                                                WHERE ufi.uid = %s AND
                                                      uh.uid = ufi.uid AND
                                                      ufi.fid = uh.id AND
                                                      uh.id_type = 'f' AND
                                                      uh.date_played = 
                                                                 DATE(ufi.ultp) AND 
                                                      uh.id = %s RETURNING uh.*""", 
                                                (l['uid'], self.fid))

                    if updated_user:
                        updated.append(updated_user)

                except psycopg2.IntegrityError, err:
                    query("COMMIT;")
                    print "(file) psycopg2.IntegrityError:",err

        self.update(updated)

    def get_selected(self):
        self.get_all()
        for u in self.ratings_and_scores:
            if u['selected']:
                return u

        selected = get_assoc("""SELECT * 
                                FROM users u, user_song_info usi 
                                WHERE listening = true AND u.uid = usi.uid AND
                                      usi.fid = %s AND selected = true
                                ORDER BY admin DESC, uname
                                LIMIT 1""",(self.fid,))

        if selected:
            self.update([selected])
            return selected

        query("UPDATE users SET selected = false")
        selected = get_assoc("""SELECT * 
                                FROM users u, user_song_info usi 
                                WHERE listening = true AND u.uid = usi.uid AND
                                      usi.fid = %s
                                ORDER BY admin DESC, uname
                                LIMIT 1""",(self.fid,))

        selected['selected'] = True
        self.update([selected])
        query("UPDATE users SET selected = true WHERE uid = %s", 
              (selected['uid'],))

        return None









