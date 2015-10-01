#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# local_file_fobj.py -- Netcast file obj
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

from __init__ import *
import fobj
import math
import time
from listeners import listeners
import pprint
import re
import os
from excemptions import CreationFailed
from ratings_and_scores import RatingsAndScores
from datetime import date
from datetime import datetime
from datetime import timedelta
import hashlib
import sys
import genres_v1
import copy
from wait_util import wait
from file_location import FileLocation

numeric = re.compile("^[0-9]+$")

class Local_File(fobj.FObj):
    def __init__(self, dirname=None, basename=None, fid=None, filename=None, 
                 insert=False, silent=False, sha512=None, must_match=False, 
                 get_dups=True, fingerprint=None, plid=None, **kwargs):
        if 'dir' in kwargs and dirname is None:
            dirname = kwargs['dir']
        print "FID:", fid
        print "DIRNAME:", dirname
        print "BASNEAME", basename
        print "FILENAME:", filename
        self.can_rate = True
        self.db_info = None
        db_info = None
        self.locations = None
        self.artists = []
        self.albums = []
        self.genres = []
        self.dups = []
        self.sha_dups = []
        self.tags_easy = None
        self.tags_hard = None
        self.mark_as_played_when_time = datetime.now()
        self.mark_as_played_when_percent = 0
        self.last_percent_played = 0
        self.mark_as_played_lock = False
        self.last_time_marked_as_played = datetime.now()
        self.edited = False
        self.rating_callback = None
        self.plid = plid
        self.process_tags_lock = False

        self.init_db_info(fid=fid, sha512=sha512, fingerprint=fingerprint, 
                          dirname=dirname, basename=basename, 
                          filename=filename, insert=insert)
        
        self.set_paths_from_locations()

        fobj.FObj.__init__(self, filename=self.filename, dirname=self.dirname, 
                           basename=self.basename, **kwargs)

        self.integrity_check(insert)

        self.set_attribs()
        self.can_rate = True
        self.ratings_and_scores = RatingsAndScores(fid=self.db_info['fid'], 
                                                   listening=True, 
                                                   plid=self.plid,
                                                   **kwargs)

        ok_to_hash = kwargs.get('hash', True)

        if ok_to_hash and (not self.db_info['sha512'] or self.mtime_changed()):
            self.update_hash()

        if get_dups and self.db_info["sha512"]:
            self.prepare_dups(must_match=must_match)

    def integrity_check(self, insert):
        if not self.is_audio and not self.is_video:
            raise CreationFailed("File is not an audio or video file:%s" % self.filename)

        if not self.exists:
            print "MISSING:", self.filename
            if not get_dups or not self.use_dup():
                raise CreationFailed("File must exist on local drive:%s" % self.filename)

        if self.filename and self.filename.startswith(cache_dir):
            raise CreationFailed("File is in cache_dir:%s", (self.filename,))

        if not self.db_info and insert:
            self.insert()
        elif not self.db_info:
            raise CreationFailed("File is not in database:%s", (self.filename,))

    def init_db_info(self, fid=None, sha512=None, fingerprint=None, dirname=None,
                    basename=None, filename=None, insert=False):
        if fid is not None:
            self.db_info = self.get_db_info_from_fid(fid)
            if self.db_info:
                print "FROM FID:", dict(self.db_info)
                return
            else:
                print "FAILED %s: FROM FID:" % (fid), db_info

        if sha512 is not None:
            self.db_info = self.get_db_info_from_sha512(sha512)
            if self.db_info:
                print "FROM sha512:", dict(self.db_info)
                return

        if fingerprint is not None:
            self.db_info = self.get_db_info_from_fingerprint(fingerprint)
            if self.db_info:
                print "FROM sha512:", dict(self.db_info)
                return
        
        self.db_info = self.get_db_info_from_filename_dirname_basename(
            filename=filename, dirname=dirname, basename=basename,
            insert=insert)

        if self.db_info:
            print "FROM filename:", dict(self.db_info)
            return

        if not insert:
            self.db_info = None
            raise CreationFailed(
                "Unable to find file information based on:\n" +
                "   fid:%s\n" % fid +
                "   filename:%s\n" % filename +
                "   dirname:%s\n" % dirname +
                "   basename:%s\n" % basename
            )
        
        self.insert()

    @property
    def is_readable(self):
        if not self.locations:
            return False
        for l in self.locations:
            if l.exists and l.is_readable:
                return True
        return False

    def get_paths_from_locations(self):
        if not self.locations:
            self.db_info = None
            raise CreationFailed(
                "No locations:\n" 
            )
        filename = None
        dirname = None
        basename = None
        for l in self.locations:
            print "L:", 
            pp.pprint(dict(l.db_info))
            if l.exists and l.is_readable:
                self.exists = l.exists
                filename = l.filename
                dirname = l.dirname
                basename = l.basename
                print "L (exists & readable):",
                pp.pprint(dict(l.db_info))
                break
        return filename, dirname, basename

    def get_db_info_from_filename_dirname_basename(
            self, filename=None, dirname=None, basename=None, insert=False):
        if not filename and not dirname and not basename:
            return None
        db_info = None
        try:
            location = FileLocation(filename=filename, dirname=dirname, 
                                    basename=basename, insert=insert)
            self.exists = location.exists
            db_info = self.get_db_info_from_fid(location.fid)
            if not db_info:
                db_info = self.get_db_info_from_fingerprint(location.fingerprint)
        except CreationFailed:
            pass
        return db_info

    def get_db_info_from_sha512(self, sha512):
        if sha512 is None:
            return None
        return get_assoc("""SELECT * 
                            FROM files 
                            WHERE sha512 = %s 
                            LIMIT 1""",
                        (sha512,))

    def get_db_info_from_fid(self, fid):
        if fid is None:
            return None
        return get_assoc("""SELECT * 
                            FROM files 
                            WHERE fid = %s 
                            LIMIT 1""",
                            (fid,))

    def get_db_info_from_fingerprint(self, fingerprint):
        if fingerprint is None:
            return None
        return get_assoc("""SELECT * 
                            FROM files 
                            WHERE fingerprint = %s 
                            LIMIT 1""",
                            (fingerprint,))


    def get_locations(self, fid=None, fingerprint=None, insert=False):
        print "GET LOCATIONS"
        print self.db_info
        locations = []
        res_locations = []
        if fingerprint and not locations:
            locations = get_results_assoc("""SELECT *
                                             FROM file_locations
                                             WHERE fingerprint = %s""", 
                                         (fingerprint,))
            print "GET LOCATIONS 1", locations
        
        if fid and not locations:
            locations = get_results_assoc("""SELECT *
                                             FROM file_locations
                                             WHERE fid = %s""", 
                                         (fid,))
            print "GET LOCATIONS 2", locations

        for l in locations:
            try:
                args = dict(l)
                args['insert'] = insert
                loc = FileLocation(**args)
                if loc.fingerprint == self.db_info['fingerprint']:
                    res_locations.append(loc)
            except CreationFailed:
                pass

        return res_locations

    def print_locations(self):
        print "print_locations"
        for l in self.locations:
            print "location exists:%s is_readable:%s %s" % (l.exists, 
                                                            l.is_readable, 
                                                            l.filename)


    def set_db_keywords(self):

        self.process_tags()

        keywords = []
        print "filename:", os.path.join(self.dirname, self.basename)
        root, ext = os.path.splitext(self.basename)
        if self.db_info['sha512']:
            keywords += [self.db_info['sha512']]
        keywords += get_words_from_string(self.basename)
        keywords += get_words_from_string(root)
        
        keywords += get_words_from_string(ext)
        
        for a in self.artists:
            keywords += get_words_from_string(a['artist'])

        for a in self.albums:
            keywords += get_words_from_string(a['album_name'])

        for g in self.genres:
            keywords += get_words_from_string(g['genre'])

        keywords += get_words_from_string(self.db_info['title'])

        keywords = list(set(keywords))
        for i, k in enumerate(keywords):
            keywords[i] = k.strip()
        keywords = list(set(keywords))
        print "BEFORE:",keywords
        txt = " ".join(keywords) 
        keywords = list(set(txt.split()))
        if keywords.count("-"):
            keywords.remove("-")
        keywords = sorted(keywords, key=str.lower)
        print "AFTER:",keywords

        present = get_assoc("""SELECT * 
                               FROM keywords 
                               WHERE fid = %s""",
                            (self.fid,))

        txt = " ".join(keywords)

        if not present:
            query("""INSERT INTO keywords (fid, txt) VALUES(%s, %s)""",
                  (self.fid, txt))
        elif present['txt'] != txt:
            print "update:",txt
            query("""UPDATE keywords SET txt = %s WHERE fid = %s""",
                  (txt, self.fid))

    def update_hash(self):
        print "UPDATE HASH"
        self.db_info['sha512'] = self.hash_file()
        query("""UPDATE files 
                 SET sha512 = %s, mtime = %s 
                 WHERE fid = %s""",
                 (self.db_info['sha512'], self.mtime, self.db_info['fid']))

    def prepare_dups(self, must_match=False):
        dups = self.get_dups(must_match=must_match)
        for d in dups:
            try:
                dup = Local_File(get_dups=False, insert=False, fid=d['fid'])
            except CreationFailed:
                continue
            self.dups.append(dup)
            if dup.db_info["sha512"] == self.db_info["sha512"]:
                self.sha_dups.append(dup)

    def use_dup(self, *args, **kwargs):
        if not self.db_info or self.is_stream:
            return False

        dups = self.get_dups(must_match=True)
        found = False

        for dup in dups:
            filename = os.path.join(dup['dir'], dup['basename'])
            if os.path.exists(filename):
                self.db_info = dup
                self.set_attribs()
                fobj.FObj.__init__(self, filename=filename, **kwargs)
                found = True
                break

        return found

    def get_possible_dups(self):
        return []
        if self.db_info['title']:
            # SELECT * FROM sometable WHERE UPPER(textfield) LIKE (UPPER('value') || '%')
            return get_results_assoc("""SELECT f.fid
                                        FROM files f 
                                        WHERE fid != %s AND 
                                              sha512 != %s AND
                                              (
                                                UPPER(title) LIKE UPPER(%s) OR 
                                                UPPER(basename) LIKE UPPER(%s)
                                              )""",
                                        (self.db_info["fid"], 
                                         self.db_info["sha512"], 
                                         self.db_info['title'], 
                                         self.db_info['basename']))
        
        return get_results_assoc("""SELECT f.fid
                                    FROM files f 
                                    WHERE fid != %s AND 
                                          sha512 != %s AND
                                          UPPER(basename) LIKE UPPER(%s)""",
                                        (self.db_info["fid"], 
                                         self.db_info["sha512"],
                                         self.db_info['basename']))


    def get_dups(self, must_match=False):
        results = []
        fids = []
        return results
        
        dups = get_results_assoc("""SELECT fid
                                    FROM files f
                                    WHERE sha512 = %s AND fid != %s""",
                                    (self.db_info["sha512"], 
                                     self.db_info["fid"]))
        for d in dups:
            fids.append(d['fid'])
            results.append(d)
        print "SHA DUPS:",
        pp.pprint(results)
        if must_match:
            return results

        possible_dups = self.get_possible_dups()

        for d in possible_dups:
            if d['fid'] in fids:
                continue
            dup = Local_File(get_dups=False, insert=False, fid=d['fid'])
            if not self.artists:
                # In this case the basename or title match, and since the
                # current file has no artists consider it a match
                fids.append(d['fid'])
                results.append(dup)
                continue
            
            for a1 in self.artists:
                is_dup = False
                for a2 in dup.artists:
                    if a1['artist'].lower() == a2['artist'].lower():
                        # At least 1 of the artists match, and 
                        # the basename or title matches so call it a dup.
                        is_dup = True
                        break
                if not is_dup:
                    continue
                fids.append(d['fid'])
                results.append(dup)

        print "POSSIBLE DUPES:",
        pp.pprint(results)

        return results

    def get_title(self):
        if not self.tags_combined:
            try:
                self.get_tags()
            except KeyError, e:
                print "KeyError:",e

        if self.tags_combined:
            if 'title' in self.tags_combined and self.tags_combined['title']:
                self.db_info = get_assoc("""UPDATE files SET title = %s
                                            WHERE fid = %s 
                                            RETURNING *;""",
                                            (self.tags_combined['title'][0], 
                                             self.db_info['fid'],))
                print "SET TITLE:%s" % self.tags_combined['title'][0]

    def calculate_true_score(self):
        self.ratings_and_scores.calculate_true_score()

    def hash_file(self):
        if not self.exists:
            return ""
        h = hashlib.sha512()
        fsize = os.path.getsize(self.filename)

        fp = open(self.filename,"rb")
        while fp.tell() < (fsize - 1):
            h.update(fp.read(102400))
        print "SHA512:", h.hexdigest()
        fp.close()
        return h.hexdigest()
        

    def check_recently_played(self, uid=None):
        print "****************************"
        print "Local_File:check_recently_played()"
        self.ratings_and_scores.check_recently_played(uid=None)
        for d in self.dups:
            d.ratings_and_scores.check_recently_played(uid=None)

    def mark_as_played(self, percent_played=0):
        if self.mark_as_played_lock:
            print "="*10, "[mark_as_played_lock]", "="*10
            print "WORKS mark_as_played_lock", percent_played
            return
        self.mark_as_played_lock = True
        now = datetime.now()

        if self.mark_as_played_when_percent > percent_played and \
           self.mark_as_played_when_time > now:
            self.mark_as_played_lock = False
            return

        print "mark as played:", self.mark_as_played_when_percent, "<="
        print "               ", percent_played
        print "            or ", self.last_time_marked_as_played, "<="
        print "               ", now
        print "self.last_time_marked_as_played:",self.last_time_marked_as_played, \
              'drift:', now - self.last_time_marked_as_played
        print "self.last_percent_played:", self.last_percent_played
        self.update_artists_ltp()
        query("""UPDATE files 
                 SET ltp = NOW() 
                 WHERE fid = %s""", 
                 (self.db_info['fid'],))

        sql = """DELETE FROM preload 
                 WHERE fid = %s AND reason NOT ILIKE '%%search%%'
              """
        query(sql, (self.db_info['fid'], ))

        self.print_locations()
        
        updated = self.ratings_and_scores.mark_as_played(percent_played)
        self.mark_as_played_when_percent = percent_played + 10
        if self.mark_as_played_when_percent > 100:
            self.mark_as_played_when_percent = 100
        now = datetime.now()
        self.mark_as_played_when_time = now + timedelta(seconds=5)
        self.last_time_marked_as_played = now
        self.last_percent_played = percent_played
        if percent_played < 100:
            # Never unlock if the file is done playing.
            self.mark_as_played_lock = False
        return updated

    def update_history(self,percent_played=0):
        self.ratings_and_scores.update_history(percent_played=percent_played)

    def deinc_score(self):
        self.ratings_and_scores.deinc_score()

    def inc_score(self):
        self.ratings_and_scores.inc_score()
        self.mark_as_played(100.0)
        self.update_history(100.0)

    def get_selected(self):
        return self.ratings_and_scores.get_selected()


    def update_artists_ltp(self):
        artists = get_results_assoc("""UPDATE artists a SET altp = NOW() 
                                       FROM file_artists fa 
                                       WHERE fa.aid = a.aid AND 
                                             fa.fid = %s RETURNING *;""",
                                       (self.db_info['fid'],))
        self.ratings_and_scores.artists = artists

        return artists

    def set_attribs(self, quick=True):
        if not self.db_info:
            return

        self.fid = self.db_info['fid']
        self.ltp = self.db_info['ltp']
        self.mtime = self.db_info['mtime']
        self.set_paths_from_locations()
        self.get_artists()
        self.get_albums()
        self.get_genres()

        if not self.db_info['title']:
            self.get_title()

        self.set_db_keywords()

    def set_paths_from_locations(self, db_info=None):
        if db_info is None:
            db_info = self.db_info

        if not db_info:
            self.dirname = None
            self.basename = None
            self.filename = None
            return
        
        self.locations = self.get_locations(db_info['fid'], db_info['fingerprint'], insert=False)
        
        filename, dirname, basename = self.get_paths_from_locations()
        self.dirname = dirname
        self.basename = basename
        self.filename = filename


    def get_artists(self):
        self.artists = get_results_assoc("""SELECT * 
                                            FROM artists a, file_artists fa 
                                            WHERE fa.fid = %s AND 
                                                  fa.aid = a.aid""",
                                            (self.fid,))
        return self.artists
        
    def get_albums(self):
        self.albums = get_results_assoc("""SELECT * 
                                           FROM albums al, album_files af 
                                           WHERE af.fid = %s AND 
                                                 af.alid = al.alid""", 
                                           (self.fid,))
        return self.albums

    def get_genres(self):
        self.genres = get_results_assoc("""SELECT * 
                                           FROM genres g, file_genres fg 
                                           WHERE fg.fid = %s AND 
                                                 g.gid = fg.gid""",
                                           (self.fid,))
        return self.genres

    def insert(self):
        if self.db_info:

            return
        print "inserting:", self.filename
        print "self.dirname:", self.dirname
        print "self.basename:", self.basename
        self.get_tags()

        try:
            self.db_info = get_assoc("""INSERT INTO files(dir, basename) 
                                        VALUES(%s, %s) RETURNING *""", 
                                        (self.dirname, self.basename))
        except psycopg2.IntegrityError:
            query("COMMIT")
            self.db_info = get_assoc("""SELECT *
                                        FROM files
                                        WHERE dir = %s AND 
                                              basename = %s""",
                                        (self.dirname, self.basename))
        self.set_attribs()
        print "insert:", os.path.join(self.dirname, self.basename)
        pp.pprint(self.db_info)

    def process_tags(self):
        if self.process_tags_lock:
            return
        self.process_tags_lock = True
        if self.db_info['edited']:
            return
        self.get_tags()

        self.process_filename()
        self.process_artist()
        self.process_genre()
        self.process_album()
        self.process_tags_lock = False

    def process_artist(self):
        if self.tags_easy:
            artists = self.tags_combined.get('artist')
            if artists:
                query("""DELETE FROM file_artists WHERE fid = %s""", (self.db_info['fid'],))
                for a in artists:
                    aids = self.get_aids_by_artist_string(a)
                    for aid in aids:
                        try:
                            query("""INSERT INTO file_artists(fid, aid) 
                                     VALUES(%s, %s)""", 
                                     (self.db_info['fid'], aid))
                        except psycopg2.IntegrityError:
                            query("COMMIT")

    def get_aids_by_artist_string(self, artists, insert=True):
        if not artists:
            return []
        print "get_aids_by_artist_string:",artists
        aids = []
        print "type:",type(artists)
        if type(artists) == str or type(artists) == unicode:
            artists = self.parse_artist_string(artists)

        print "artists:",artists
        if artists:
            for a in artists:
                print "A:",a
                self.add_artist(a)
        
        if self.artists:
            for a in self.artists:
                aids.append(a['aid'])
            return aids

        return None

    def add_artist(self, artist_name):
        if artist_name is None or not artist_name:
            return
        artist_name = artist_name.strip()
        artist_name = artist_name.replace("\x00", "")
        if not artist_name:
            return

        for a in self.artists:
            if a['artist'] == artist_name:
                # print "found:",artist_name
                return

        artist = get_assoc("""SELECT * FROM artists WHERE artist = %s""", 
                              (artist_name,))
        if not artist:
            print "inserting artist :" ,artist_name
            artist = get_assoc("""INSERT INTO artists (artist) 
                                  VALUES(%s) RETURNING *""", (artist_name,))

        self.artists.append(artist)

        association = get_assoc("""SELECT * 
                                   FROM file_artists 
                                   WHERE fid = %s AND aid = %s""", (self.fid, artist['aid']))
        if not association:
            print "associating artist:",artist_name
            association =  get_assoc("""INSERT INTO file_artists (fid, aid) 
                                        VALUES(%s, %s) RETURNING *""", 
                                        (self.fid, artist['aid']))
        self.set_db_keywords()
        return artist

    def remove_artist(self, aid=None):
        for i, a in enumerate(self.artists):
            if a['aid'] == aid:
                print "del:",a
                del self.artists[i]
        query("""DELETE FROM file_artists 
                 WHERE fid = %s AND aid = %s""",
                 (self.fid, aid))
        present = get_assoc("""SELECT count(*) AS total 
                               FROM file_artists fa, files f
                               WHERE f.fid = fa.fid AND fa.aid = %s""",
                               (aid,))
        if not present or present['total'] == 0:
            query("""DELETE FROM artists WHERE aid = %s""", (aid,))

        self.set_db_keywords()

    def remove_genre(self, gid=None):
        genre = None
        for i, g in enumerate(self.genres):
            if g['gid'] == gid:
                print "del:",g
                genre = copy.deepcopy(self.genres[i])
                del self.genres[i]
        query("""DELETE FROM file_genres 
                 WHERE fid = %s AND gid = %s""",
                 (self.fid, gid))
        present = get_assoc("""SELECT count(*) AS total 
                               FROM file_genres fg, files f
                               WHERE f.fid = fg.fid AND fg.gid = %s""",
                               (gid,))
        if not present or present['total'] == 0:
            if genre is not None and genre['genre'] not in genres_v1.genres_v1:
                query("""DELETE FROM genres WHERE gid = %s""", (gid,))

        self.set_db_keywords()

    def remove_album(self, alid=None):
        album = None
        for i, al in enumerate(self.albums):
            if al['alid'] == alid:
                print "del:",al
                album = copy.deepcopy(self.albums[i])
                del self.albums[i]
        query("""DELETE FROM album_files 
                 WHERE fid = %s AND alid = %s""",
                 (self.fid, alid))
        present = get_assoc("""SELECT count(*) AS total 
                               FROM album_files af, files f
                               WHERE f.fid = af.fid AND af.alid = %s""",
                               (alid,))
        if not present or present['total'] == 0:
            if album is not None:
                query("""DELETE FROM albums WHERE alid = %s""", (alid,))
        self.set_db_keywords()

    def parse_artist_string(self, artists):
        artists = artists.strip()
        artists = artists.replace("\x00", "")
        print "parse_artist_string:", artists
        if not artists:
            return []
        combos = []
        combos.append(artists)
        lines = artists.splitlines()
        for l in lines:
            l = l.strip()
            if not l:
                continue

            all_seps = '/w\/|v\/|\/|,|&|\ and\ |\ ft\.|\ ft\ |\ \-\ |\-\ |\ \-|\ vs\ |\ vs\.\ |feat\. |feat\ |\ featuring\ /'
            parts = re.split(all_seps, l, re.I)

            for p in parts:
                p = p.strip()
                if len(p) <= 2:
                    continue
                if type(p) != unicode:
                    try:
                        p = unicode(p, "utf8",errors='replace')
                    except UnicodeEncodeError, err:
                        print "UnicodeEncodeError parts:",err
                        exit()
                if numeric.match(p):
                    continue

                if combos.count(p) == 0:
                    combos.append(p)

            return combos

    def insert_tag_to_db(self, fid, key, value):
        if type(value) == list:
            for i, v in enumerate(value):
                self.insert_tag_to_db(fid, "%s[%s]" % (key,i), v)
            return

        if type(value) == dict:
            for k, v in value.iteritems():
                self.insert_tag_to_db(fid, "%s[%s]" % (key,k), v)
            return

        if type(value) == int:
            value = "%s" % value

        if type(value) == float:
            value = "%s" % value

        if type(value) == ID3TimeStamp:
            value = "%s" % value

        if type(value) != unicode:
            value = unicode(value, "utf8", errors='replace')

        q = pg_cur.mogrify("""INSERT INTO tags (fid, tag_name,tag_value) 
                              VALUES(%s,%s,%s)""", (fid, key, value))
        print "value-type:",type(value)
        print "query:",q
        query("""INSERT INTO tags (fid, tag_name,tag_value) VALUES(%s,%s,%s)""", 
                (fid, key, value))

    def mtime_changed(self):
        if not self.db_info:
            return True
        self.getmtime()
        if self.mtime != self.db_info['mtime']:
            return True

        print "self.mtime:",self.mtime,"==",self.db_info['mtime']
        return False

    def update_tags(self, fid=None):
        if not fid:
            fid = self.db_info['fid']

        if not self.mtime_changed():
            print "MTIME not changed:", self.filename
            return

        pg_cur.execute("DELETE FROM tags WHERE fid = %s", (fid,))
        print "TAGS_EASY:",self.tags_easy

        if not self.tags_easy:
            return
        
        for k in self.tags_easy.keys():
            v = self.tags_easy[k]
            self.insert_tag_to_db(fid, k, v)
            print "tag:%s=%s" % (k,v)

        query("""UPDATE files SET mtime = %s WHERE fid = %s""", (self.mtime, fid))

    def process_filename(self):
        print "process_filename"
        base, ext = os.path.splitext(self.basename)
        parts = base.split(' - ',1)
        print "parts:",parts
        if len(parts) == 2:
            artist = parts[0].strip()
            title = parts[1].strip()
            print "Artist:", artist
            print "Title:", title
            if artist:
                combos = self.parse_artist_string(artist)
                self.process_artist_combos(combos)

    def process_artist_combos(self,combos):
        if not combos:
            return

        if len(combos) > 1:
            print "combos:",combos
        for c in combos:
            print "C:",c
            self.add_artist(c)

    def add_album(self, album_name, aid=None):
        album_name = album_name.replace("\x00", "")
        album_name = album_name.strip()
        if not album_name:
            return
        if aid is None:
            for a in self.artists:
                self.add_album(album_name, a['aid'])
            return

        album_name = album_name.strip()

        if not album_name:
            return

        if type(album_name) != unicode:
            album_name = unicode(album_name, "utf8", errors='replace')

        for al in self.albums:
            if al['album_name'] == album_name and al['aid'] == aid:
                return

        album = get_assoc("""SELECT * FROM albums WHERE album_name = %s AND aid = %s""",
                             (album_name, aid))

        if not album:
            print "associating album:", album_name
            album = get_assoc("""INSERT INTO albums (album_name, aid) 
                                 VALUES(%s,%s) RETURNING *""",
                                 (album_name, aid))

        album_file = get_assoc("""SELECT * 
                                  FROM album_files 
                                  WHERE alid = %s AND fid = %s""", 
                                  (album['alid'], self.fid))
        if not album_file:
            print "associating file to album:", album_name
            album_file = get_assoc("""INSERT INTO album_files (alid, fid) 
                                      VALUES(%s,%s) RETURNING *""", 
                                      (album['alid'], self.fid))

        self.albums.append(album)
        self.set_db_keywords()
        return album

    def process_album(self):
        if self.tags_combined:
            albums = self.tags_combined.get('album')
            if albums:
                for al in albums:
                    if not al:
                        continue
                    for a in self.artists:
                        self.add_album(al, a['aid'])

    def process_genre(self):
        if self.tags_combined:
            genres = self.tags_combined.get('genre')
            if genres:
                for g in genres:
                    self.add_genre(g)
                

    def rate(self, uid=None, rating=None, uname=None, selected=None):
        print "lfobj:","1"*100
        for d in self.dups:
            d.ratings_and_scores.rate(uid=uid, rating=rating, uname=uname, 
                                      selected=selected)
        print "lfobj:","2"*100
        res = self.ratings_and_scores.rate(uid=uid, rating=rating, 
                                           uname=uname, 
                                           selected=selected)
        print "lfobj:","3"*100
        if self.rating_callback:
            self.rating_callback(res)

        print "lfobj:","4"*100

        return res

    def add_genre(self, genre_name):
        genre_name = genre_name.replace("\x00", "")
        genre_name = genre_name.strip()
        if not genre_name:
            return
        for g in self.genres:
            if g['genre'] == genre_name:
                return
        genre = get_assoc("""SELECT * 
                             FROM genres 
                             WHERE genre = %s""",
                             (genre_name,))
        if not genre:
            print "inserting genre:",genre_name
            genre = get_assoc("""INSERT INTO genres (genre, enabled) 
                                 VALUES(%s, %s) RETURNING *""", 
                                 (genre_name, True))

        association = get_assoc("""SELECT * 
                                   FROM file_genres 
                                   WHERE fid = %s AND gid = %s""", 
                                   (self.fid, genre['gid']))

        if not association:
            print "associating genre:", genre_name
            association = get_assoc("""INSERT INTO file_genres (fid, gid) 
                                       VALUES(%s, %s) RETURNING *""", 
                                       (self.fid, genre['gid']))

        self.genres.append(genre)
        self.set_db_keywords()
        return genre

    def get_artist_title(self):
        self.get_tags()
        artist = self.tags_combined.get('artist')
        title = self.tags_combined.get('title')
        if artist and title:
            return "%s - %s" % (artist[0], title[0])

        return self.db_info['title'] or self.basename

    def __repr__(self):
        return '<%s\n\tpath:%s\n\tbasename:%s>' % (
            self.__class__.__name__, self.dirname, self.basename)
    
def get_words_from_string(string):
    if string is None:
        return []

    if not string or not isinstance(string,(str, unicode)):
        print "NOT VALID:",string
        print "TYPE:",type(string)
        return []

    string = string.strip().lower()
    final_words = string.split()
    dash_splitted = string.split("-")
    for p in dash_splitted:
        p = p.strip()
        final_words.append(p)

    # replace any non-word characters
    # This would replace "don't say a word" with "don t say a word"
    replaced_string = re.sub("[\W]", " ", string)
    final_words += replaced_string.split()
    # replace any non words characters and leave spaces.
    # To change phrases like "don't say a word" to "dont say a word"
    # so I'm will become "im"
    # P.O.D. will become pod
    removed_string = re.sub("[^\w\s]", "", string)
    final_words += removed_string.split()
    final_words = list(set(final_words))

    return final_words

def sanity_check(fid):
    finfo = get_assoc("""SELECT *
                         FROM files
                         WHERE fid = %s""",(fid,))

    sql = """INSERT INTO dont_pick (fid, reason) 
             VALUES(%s, 'file is missing, or not readable')"""
    query(sql, (fid,))

    if not finfo:
        print "DELETING FID:",fid
        delete_fid(fid)
        wait()
        return
    print "SHIT'S FUCKED UP."
    sql = """SELECT *
             FROM file_locations
             WHERE fid = %s"""
    locations = get_results_assoc(sql, (fid,))
    
    for l in locations:
        dirname = l['dirname']
        # 1. Confirm that the folder can be read from.
        #    The folder may have been unmounted, and no longer
        #    exists, but we'd like to keep the data if this is
        #    the situation.
        if not os.path.exists(dirname) or not os.access(dirname, os.R_OK):
            continue
        filename = os.path.join(l['dirname'], l['basename'])
        if os.path.exists(filename):
            # 2. make sure we're not removing a file that exists.
            continue
        # 3. Delete the location from the database because the 
        #    dir exists and is readable, but the file does not.
        sql = """DELETE FROM file_locations WHERE flid = %s"""
        query(sql, (l['flid'],))

    sql = """SELECT *
             FROM file_locations
             WHERE fid = %s"""

    locations = get_results_assoc(sql, (fid,))

    if not locations:
        print "NO LOCATIONS"
        # 4. There are no file locations so we delete the file
        #    from the database.
        delete_fid(fid)

    # sys.exit()


def delete_fid(fid):
    delete_user_history_for_fid(fid)
    wait()
    delete_ratings_for_fid(fid)
    wait()
    delete_locations_for_fid(fid)
    wait()
    delete_artist_for_fid(fid)
    wait()
    delete_genres_for_fid(fid)
    wait()
    delete_fid_from_preload(fid)
    wait()
    delete_fid_from_files(fid)
    wait()

def delete_fid_from_files(fid):
    sql = """DELETE FROM files WHERE fid = %s"""
    query(sql, (fid,))

def delete_fid_from_preload(fid):
    query("""DELETE FROM preload WHERE fid = %s""",(fid,))
    query("""DELETE FROM preload_cache WHERE fid = %s""",(fid,))
    query("""DELETE FROM dont_pick WHERE fid = %s""",(fid,))

def delete_user_history_for_fid(fid):
    query("""DELETE FROM user_history
             WHERE id_type = 'f' AND id = %s """,(fid,))

def delete_ratings_for_fid(fid):
    query("""DELETE FROM user_song_info
             WHERE fid = %s """,(fid,))

def delete_locations_for_fid(fid):
    query("""DELETE FROM file_locations 
             WHERE fid = %s""", (fid,))

def delete_artist_for_fid(fid):
    artists_before = get_artists_for_fid(fid)
    query("""DELETE FROM file_artists
             WHERE fid = %s""",(fid,))
    for artist in artists_before:
        has_artist = get_files_for_aid(artist['aid'])
        if not has_artist:
            delete_artist(artist['aid'])

def get_artists_for_fid(fid):
    return get_results_assoc("""SELECT *
                                FROM file_artists
                                WHERE fid = %s""", (fid,))

def get_files_for_aid(aid):
    return get_results_assoc("""SELECT *
                                FROM file_artists
                                WHERE aid = %s""",(aid,))

def delete_artist(aid):
    query("""DELETE FROM artists 
             WHERE aid = %s""", (aid,))


def delete_genres_for_fid(fid):
    genres_before = get_genres_for_fid(fid)
    query("""DELETE FROM file_genres
             WHERE fid = %s""",(fid,))
    for genre in genres_before:
        has_genre = get_files_for_gid(genre['gid'])
        if not has_genre:
            delete_genres(genre['gid'])

def get_files_for_gid(gid):
    return get_results_assoc("""SELECT *
                                FROM file_genres 
                                WHERE gid = %s""",(gid,))

def delete_genres(gid):
    query("""DELETE FROM genres 
             WHERE gid = %s""", (gid,))

def get_genres_for_fid(fid):
    return get_results_assoc("""SELECT *
                                FROM file_genres
                                WHERE fid = %s""", (fid,))


if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            if os.path.isfile(arg):
                obj = Local_File(filename=arg, insert=True)
                print obj.filename
        except CreationFailed, e:
            print "CreationFailed:",e


