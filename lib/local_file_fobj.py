#!/usr/bin/env python
# -*- coding: utf-8 -*-
# local_file_fobj.py -- Netcast file obj
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
import os
import sys
import genres_v1
import copy

numeric = re.compile("^[0-9]+$")

class Local_File(fobj.FObj):
    def __init__(self, dirname=None, basename=None, fid=None, filename=None, 
                 insert=False, silent=False, sha512=None, must_match=False, get_dups=True, **kwargs):

        if kwargs.has_key('dir') and dirname is None:
            dirname = kwargs['dir']

        self.can_rate = True
        self.db_info = None
        db_info = None
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
        self.last_time_marked_as_played = datetime.now()

        if fid:
            db_info = get_assoc("""SELECT * 
                                   FROM files 
                                   WHERE fid = %s LIMIT 1""",
                                   (fid,))

        if sha512 is not None and not db_info:
            db_info = get_assoc("""SELECT * 
                                   FROM files 
                                   WHERE sha512 = %s 
                                   LIMIT 1""",
                                   (sha512,))

        if not db_info:
            if filename is not None:
                filename = os.path.realpath(filename)
                print "filename:",filename
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)
            elif dirname is not None and basename is not None:
                filename = os.path.realpath(os.path.join(dirname, basename))
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)

            if not filename or not os.path.exists(filename):
                self.exists = False
                raise CreationFailed("File must exist on local drive:%s" % filename)

            db_info = get_assoc("""SELECT * 
                                   FROM files 
                                   WHERE dir = %s AND basename = %s""",
                                   (dirname, basename))

        if db_info:
            filename = os.path.join(db_info['dir'], db_info['basename'])
            dirname = db_info['dir']
            basename = db_info['basename']
            self.db_info = db_info
        elif not insert:
            raise CreationFailed(
                "Unable to find file information based on:\n" +
                "   fid:%s\n" % fid +
                "   filename:%s\n" % filename +
                "   dirname:%s\n" % dirname +
                "   basename:%s\n" % basename
            )

        fobj.FObj.__init__(self, filename=filename, dirname=dirname, 
                           basename=basename, **kwargs)

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

        self.set_attribs()
        self.can_rate = True
        self.ratings_and_scores = RatingsAndScores(fid=self.db_info['fid'], 
                                                   listening=True)
        #if not silent:
        #    print "RatingsAndScores:",self.ratings_and_scores

        ok_to_hash = True

        if kwargs.has_key('hash') and not kwargs['hash']:
            ok_to_hash = False

        if ok_to_hash and (not self.db_info['sha512'] or self.mtime_changed()):
            self.update_hash()

        if get_dups and self.db_info["sha512"]:
            self.prepare_dups(must_match=must_match)

    def set_db_keywords(self):
        keywords = []

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

        present = get_assoc("""SELECT * FROM keywords WHERE fid = %s""",
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
        if not self.tags_easy:
            try:
                self.get_tags()
            except KeyError, e:
                print "KeyError:",e

        if self.tags_easy:
            if 'title' in self.tags_easy and self.tags_easy['title']:
                self.db_info = get_assoc("""UPDATE files SET title = %s
                                            WHERE fid = %s 
                                            RETURNING *;""",
                                            (self.tags_easy['title'][0], 
                                             self.db_info['fid'],))
                print "SET TITLE:%s" % self.tags_easy['title'][0]
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
        now = datetime.now()

        if self.mark_as_played_when_percent > percent_played and \
           self.mark_as_played_when_time > now:
            return

        print "mark as played:", self.mark_as_played_when_percent, "<="
        print "               ",percent_played
        print "            or ",self.last_time_marked_as_played, "<="
        print "               ",now
        print "self.last_time_marked_as_played:",self.last_time_marked_as_played, \
              'drift:', now - self.last_time_marked_as_played
        print "self.last_percent_played:", self.last_percent_played
        self.update_artists_ltp()
        
        self.ratings_and_scores.mark_as_played(percent_played)
        for d in self.dups:
            d.mark_as_played(percent_played)
        self.mark_as_played_when_percent = percent_played + 10
        if self.mark_as_played_when_percent > 100:
            self.mark_as_played_when_percent = 100
        now = datetime.now()
        self.mark_as_played_when_time = now + timedelta(seconds=5)
        self.last_time_marked_as_played = now
        self.last_percent_played = percent_played

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
        self.ratings_and_scores.artists = artists;

        return artists

    def set_attribs(self, quick=True):
        if not self.db_info:
            return
        self.fid = self.db_info['fid']
        self.ltp = self.db_info['ltp']
        self.mtime = self.db_info['mtime']
        self.dirname = self.db_info['dir']
        self.basename = self.db_info['basename']
        self.filename = os.path.join(self.db_info['dir'], self.db_info['basename'])
        self.get_artists()
        self.get_albums()
        self.get_genres()

        if not self.db_info['title']:
            self.get_title()

        self.set_db_keywords()


    def get_artists(self):
        self.artists = get_results_assoc("""SELECT * 
                                            FROM artists a, file_artists fa 
                                            WHERE fa.fid = %s AND fa.aid = a.aid""",
                                            (self.fid,))
        return self.artists
        
    def get_albums(self):
        self.albums = get_results_assoc("""SELECT * 
                                           FROM albums al, album_files af 
                                           WHERE af.fid = %s AND af.alid = al.alid""", 
                                           (self.fid,))
        return self.albums

    def get_genres(self):
        self.genres = get_results_assoc("""SELECT * 
                                           FROM genres g, file_genres fg 
                                           WHERE fg.fid = %s AND g.gid = fg.gid""",
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
                                        WHERE dir = %s and basename = %s""",
                                        (self.dirname, self.basename))
        self.set_attribs()
        print "insert:", os.path.join(self.dirname, self.basename)
        pp.pprint(self.db_info)

        if isinstance(self.tags_easy, dict) and self.tags_easy.has_key('artist') \
           and self.tags_easy['artist']:
            query("""DELETE FROM file_artists WHERE fid = %s""", (self.db_info['fid'],))
            for a in self.tags_easy['artist']:
                aids = self.get_aids_by_artist_string(a)
                for aid in aids:
                    query("""INSERT INTO file_artists(fid, aid) 
                             VALUES(%s, %s)""", 
                             (self.db_info['fid'], aid))

        self.process_filename()
        self.process_genre()
        self.process_album()

    def get_aids_by_artist_string(self, artists, insert=True):
        print "get_aids_by_artist_string:",artists
        aids = []
        print "type:",type(artists)
        if type(artists) == str or type(artists) == unicode:
            artists = self.parse_artist_string(artists)

        print "artists:",artists
        
        for a in artists:
            print "A:",a
            self.add_artist(a)
        
        if self.artists:
            for a in self.artists:
                aids.append(a['aid'])
            return aids

        return None

    def add_artist(self, artist_name):
        if artist_name is None:
            return
        artist_name = artist_name.strip()
        
        if artist_name == "":
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

    def parse_artist_string(self, artists):
        artists = artists.strip()
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
                        p = unicode(p,"utf8",errors='replace')
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

        #  print "self.mtime:",self.mtime,"==",self.db_info['mtime']
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
            self.add_artist(c)

    def add_album(self, album_name, aid):
        if album_name == None:
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
        return album

    def process_album(self):
        if self.tags_easy and self.tags_easy.has_key('album') and self.tags_easy['album']:
            if isinstance(self.tags_easy['album'], list):
                for al in self.tags_easy['album']:
                    for a in self.artists:
                        self.add_album(al, a['aid'])
            elif self.tags_easy['album']:
                al = self.tags_easy['album']
                for a in self.artists:
                    self.add_album(al, a['aid'])

    def process_genre(self):
        if self.tags_easy and 'genre' in self.tags_easy and self.tags_easy['genre']:
            if isinstance(self.tags_easy['genre'], list):
                for g in self.tags_easy['genre']:
                    self.add_genre(g)

            # print self.tags_hard
        if self.tags_hard and self.tags_hard.has_key('TCON') and self.tags_hard['TCON']:
            if isinstance(self.tags_hard['TCON'].text, list):
                for g in self.tags_hard['TCON'].text:
                    self.add_genre(g)

    def rate(self, uid=None, rating=None, uname=None, selected=None):
        for d in self.dups:
            d.ratings_and_scores.rate(uid=uid, rating=rating, uname=uname, 
                                      selected=selected)

        return self.ratings_and_scores.rate(uid=uid, rating=rating, uname=uname, 
                                            selected=selected)

    def add_genre(self, genre_name):
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
        return genre

    def get_artist_title(self):
        self.get_tags(easy=True)
        if self.tags_easy:
            if 'artist' in self.tags_easy and self.tags_easy['artist'] and \
               'title' in self.tags_easy and self.tags_easy['title']:
                return "%s - %s" % (self.tags_easy['artist'][0], self.tags_easy['title'][0])

        return self.db_info['title'] or self.basename

    def __repr__(self):
        return '<%s\n\tpath:%s\n\tbasename:%s>' % (
            self.__class__.__name__, self.dirname, self.basename)
    
def get_words_from_string(string):
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
        
if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            if os.path.isfile(arg):
                obj = Local_File(filename=arg, insert=True)
                print obj.filename
        except CreationFailed, e:
            print "CreationFailed:",e


