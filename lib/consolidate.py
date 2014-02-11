#!/usr/bin/env python
# consolidate.py -- consolidate files to use local files.
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
import os

class Consolidateor:
    def __init__(self):
        self.testing = False
        self.users = get_results_assoc("""SELECT * FROM users ORDER BY uid""")
        self.simlar = get_results_assoc("""SELECT fingerprint, 
                                                  count(*) AS total 
                                           FROM files 
                                           GROUP BY fingerprint HAVING count(fingerprint) > 1 
                                           ORDER BY total""")


        for fingerprint_data in self.simlar:
            fids = self.get_fids_for_fingerprint(fingerprint_data['fingerprint'])
            master_fid = fids[0]
            other_fids = fids[1:]
            master_file_info = self.get_file_info(master_fid)
            print master_file_info['fid'], master_file_info['basename']
            self.consolidate_locations(master_fid, fingerprint_data['fingerprint'])
            self.consolidate_artists(master_fid, other_fids)
            self.consolidate_geners(master_fid, other_fids)
            self.consolidate_albums(master_fid, other_fids)
            self.consolidate_user_history(master_fid, other_fids)
            self.consolidate_keywords(master_fid, other_fids)
            self.consolidate_user_song_info(master_fid, other_fids)
            self.remove_other_fids(other_fids)

    def remove_other_fids(self, other_fids):
        if self.testing:
            return
        str_fids = ",".join(str(x) for x in other_fids)
        query("""DELETE FROM file_locations WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM file_artists WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM file_genres WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM album_files WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM user_history WHERE id_type = 'f' AND id IN ("""+str_fids+""")""")
        query("""DELETE FROM keywords WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM user_song_info WHERE fid IN ("""+str_fids+""")""")
        query("""DELETE FROM files WHERE fid IN ("""+str_fids+""")""")


    def consolidate_locations(self, fid, fingerprint):
        query("""UPDATE file_locations SET fid = %s
                 WHERE fingerprint = %s""",(fid, fingerprint))

    def consolidate_keywords(self, master_fid, other_fids):
        keywords = self.get_keywords(master_fid)
        for fid in other_fids:
            keywords += self.get_keywords(fid)
        keywords = list(set(keywords))
        keywords.sort()
        print "keywords:", keywords
        query("""UPDATE keywords 
                 SET txt = %s 
                 WHERE fid = %s""",
        (" ".join(keywords), master_fid,))
        return

    def get_keywords(self, fid):
        keywords = []
        res = get_assoc("""SELECT txt
                           FROM keywords 
                           WHERE fid = %s
                           LIMIT 1""",
                        (fid,))
        if not res:
            return []
        return res['txt'].split(" ")

    def consolidate_user_song_info(self, master_fid, other_fids):
        all_fids = [master_fid] + other_fids
        str_fids = ",".join(str(x) for x in all_fids)
        for user in self.users:
            most_recent = self.get_most_recently_played(all_fids, user['uid'])
            if not most_recent:
                most_recent = self.get_most_recently_played(all_fids, user['uid'], False)
            if not most_recent:
                continue
            print "most_recent:", most_recent
            query("""UPDATE user_song_info
                     SET rating = %s, score = %s, percent_played = %s,
                         ultp = %s, true_score = %s
                     WHERE uid = %s AND fid IN ("""+str_fids+""")""",
                 (most_recent['rating'], most_recent['score'], most_recent['percent_played'],
                  most_recent['ultp'], most_recent['true_score'],
                  user['uid']))
        return

    def get_most_recently_played(self, fids, uid, skip_null=True):
        str_fids = ",".join(str(x) for x in fids)
        print "uid: %s str_fids:" % (uid,), str_fids
        if skip_null:
            query = """SELECT *
                       FROM user_song_info
                       WHERE ultp IS NOT NULL AND 
                             uid = %s AND 
                             fid IN ("""+str_fids+""")
                       ORDER BY ultp DESC
                       LIMIT 1"""
        else:
            query = """SELECT *
                       FROM user_song_info
                       WHERE uid = %s AND 
                             fid IN ("""+str_fids+""")
                       ORDER BY ultp DESC
                       LIMIT 1"""
        return get_assoc(query,(uid,))



    def consolidate_user_artist_history(self, master_fid, other_fids):
        # NOT NEEDED aid is carried over.
        return

    def consolidate_user_history(self, master_fid, other_fids):
        master_history = self.get_user_history(master_fid)
        other_histories = []
        for fid in other_fids:
            other_histories += self.get_user_history(fid)
        for h in other_histories:
            self.associate_user_history(master_fid, h)
        return

    def associate_user_history(self, fid, history):
        """
        \d user_history
                                       Table "public.user_history"
             Column     |           Type           |                          Modifiers                          
        ----------------+--------------------------+-------------------------------------------------------------
         uhid           | integer                  | not null default nextval('user_history_uhid_seq'::regclass)
         uid            | integer                  | not null
         id             | integer                  | not null
         percent_played | integer                  | 
         time_played    | timestamp with time zone | 
         date_played    | date                     | 
         id_type        | character varying(2)     | 
         true_score     | double precision         | not null default 0
         score          | integer                  | not null default 0
         rating         | integer                  | not null default 0
        """
        try:
            query("""INSERT INTO user_history (uid, id, percent_played,
                                               time_played, date_played,
                                               id_type, true_score, score, 
                                               rating)
                      VALUES(%s, %s, %s,
                             %s, %s,
                             %s, %s, %s,
                             %s)""",
                 (history['uid'], history['id'], history['percent_played'],
                  history['time_played'], history['date_played'],
                  history['id_type'], history['true_score'], history['score'],
                  history['rating']))
        except psycopg2.IntegrityError:
            pg_conn.commit()
            pass

    def get_user_history(self, fid):
        return get_results_assoc("""SELECT *
                                    FROM user_history
                                    WHERE id_type = 'f' AND id = %s""",
                                (fid,))

    def consolidate_albums(self, master_fid, other_fids):
        master_alids = self.get_alids_for_fid(master_fid)
        other_alids = []
        for fid in other_fids:
            other_alids += self.get_alids_for_fid(fid)

        other_alids = list(set(other_alids))
        for alid in other_alids:
            if alid not in master_alids:
                self.associate_album(master_fid, alid)
        return

    def get_alids_for_fid(self, fid):
        alids = []
        res = get_results_assoc("""SELECT alid
                                   FROM album_files
                                   WHERE fid = %s""",
                               (fid,))
        for r in res:
            alids.append(r['alid'])
        return alids

    def consolidate_geners(self, master_fid, other_fids):
        master_gids = self.get_gids_for_fid(master_fid)
        other_gids = []
        for fid in other_fids:
            other_gids += self.get_gids_for_fid(fid)

        other_gids = list(set(other_gids))
        for gid in other_gids:
            if gid not in master_gids:
                self.associate_genre(master_fid, gid)
        return

    def get_gids_for_fid(self, fid):
        gids = []
        res = get_results_assoc("""SELECT gid
                                   FROM file_genres
                                   WHERE fid = %s""",(fid,))
        for r in res:
            gids.append(r['gid'])

        return gids

    def consolidate_artists(self, master_fid, other_fids):
        
        master_aids = self.get_aids_for_fid(master_fid)
        other_aids = []
        for fid in other_fids:
            other_aids += self.get_aids_for_fid(fid)

        other_aids = list(set(other_aids))
        for aid in other_aids:
            if aid not in master_aids:
                self.associate_artist(master_fid, aid)
        return

    def get_file_info(self, fid):
        return get_assoc("""SELECT *
                            FROM files 
                            WHERE fid = %s""",
                        (fid,))

    def get_artist(self, aid):
        return get_assoc("""SELECT *
                            FROM artists
                            WHERE aid = %s
                            LIMIT 1""",
                        (aid,))

    def associate_artist(self, fid, aid):
        artist = self.get_artist(aid)
        if not artist:
            return
        print "associating fid (%s) => aid (%s) %s" % (fid, aid, artist['artist'])
        if self.testing:
            return
        query("""INSERT INTO file_artists (fid, aid)
                 VALUES(%s,%s)""", 
                (fid, aid))

    def associate_genre(self, fid, gid):
        genre = self.get_genre(gid)
        if not genre:
            return
        print "associating fid (%s) => gid (%s) %s" % (fid, gid, genre['genre'])
        if self.testing:
            return
        query("""INSERT INTO file_genres (fid, gid)
                 VALUES(%s,%s)""", 
              (fid, gid))

    def associate_album(self, fid, alid):
        album = self.get_album(alid)
        if not album:
            return
        print "associating fid (%s) => alid (%s) %s" % (fid, alid, album['album_name'])
        if self.testing:
            return
        query("""INSERT INTO album_files (fid, alid)
                 VALUES(%s, %s)""", 
              (fid, alid))

    def get_album(self, alid):
        return get_assoc("""SELECT *
                            FROM albums
                            WHERE alid = %s
                            LIMIT 1""",(alid,))

    def get_aids_for_fid(self, fid):
        aids = []
        res = get_results_assoc("""SELECT aid
                                   FROM file_artists 
                                   WHERE fid = %s""",
                                (fid,))
        for r in res:
            aids.append(r['aid'])
        return aids

    def get_fids_for_fingerprint(self, fingerprint):
        fids = []
        res = get_results_assoc("""SELECT fid
                                   FROM files 
                                   WHERE fingerprint = %s""",
                                (fingerprint,))
        for r in res:
            fids.append(r['fid'])

        res = get_results_assoc("""SELECT fid
                                   FROM file_locations
                                   WHERE fingerprint = %s""", (fingerprint,))

        for r in res:
            fids.append(r['fid'])

        fids = list(set(fids))
        return fids

    def get_genre(self, gid):
        return get_assoc("""SELECT *
                            FROM genres
                            WHERE gid = %s
                            LIMIT 1
                            """,
                        (gid,))


if __name__ == '__main__':
    consolidateor = Consolidateor()
