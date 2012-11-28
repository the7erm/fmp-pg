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
import fobj, math
from listeners import listeners
import pprint, re
from excemptions import CreationFailed

class Local_File(fobj.FObj):
    def __init__(self, dirname=None, basename=None, fid=None, filename=None, insert=False):
        self.can_rate = True
        self.db_info = None
        db_info = None
        self.artists = []
        self.albums = []
        self.genres = []
        self.last_percent_played = 0

        if fid:
            db_info = get_assoc("SELECT * FROM files WHERE fid = %s LIMIT 1",(fid,))

        if not db_info:
            if filename is not None:
                filename = os.path.realpath(filename)
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)
            elif dirname is not None and basename is not None:
                filename = os.path.realpath(os.path.join(dirname, basename))
                dirname = os.path.dirname(filename)
                basename = os.path.basename(filename)

            if not os.path.exists(filename):
                raise CreationFailed("File must exist on local drive:%s" % filename)

            db_info = get_assoc("SELECT * FROM files WHERE dir = %s AND basename = %s",(dirname, basename))


        if db_info:
            filename = os.path.join(db_info['dir'], db_info['basename'])
            dirname = db_info['dir']
            basename = db_info['basename']
            self.db_info = db_info
            self.set_attribs()
        elif not insert:
            raise CreationFailed(
                "Unable to find file information based on:\n" +
                "   fid:%s\n" % fid +
                "   filename:%s\n" % filename +
                "   dirname:%s\n" % dirname +
                "   basename:%s\n" % basename
            )

        fobj.FObj.__init__(self,filename=filename, dirname=dirname, basename=basename)

        if not self.is_audio and not self.is_video:
            raise CreationFailed("File is not an audio or video file:%s" % self.filename)

        if not self.exists:
            raise CreationFailed("File must exist on local drive:%s" % self.filename)

        if self.filename and self.filename.startswith(cache_dir):
            raise CreationFailed("File is in cache_dir:%s", (self.filename,))

        if not self.db_info and insert:
            self.insert()

        elif not self.db_info:
            raise CreationFailed("File is not in database:%s", (self.filename,))

        self.set_attribs()
        self.can_rate = True

    def calculate_true_score():
        query("UPDATE user_song_info SET true_score = (((rating * 2 * 10.0) + (score * 10) + percent_played) / 3) WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true)",(self.fid,))
        

    def mark_as_played(self, percent_played=0):
        fid = self.fid
        print "mark_fid_as_played:",fid
        query("UPDATE user_song_info SET ultp = NOW(), percent_played = %s WHERE fid = %s AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)",(percent_played, fid,))

        self.calculate_true_score()
        
        if not listeners.listeners:
            listeners.reload(force=True)
        
        if listeners.listeners and self.last_percent_played != math.ceil(percent_played):
            artists = get_results_assoc("SELECT aid FROM file_artists WHERE fid = %s",(fid,))
            for l in self.listeners:
                try:
                    user_history = get_assoc("INSERT INTO user_history (uid, fid, percent_played, time_played, date_played) VALUES(%s,%s,%s, NOW(), current_date) RETURNING *",(l['uid'], fid, percent_played))
                except psycopg2.IntegrityError, err:
                    query("COMMIT;")
                    query("UPDATE user_history SET percent_played = %s, time_played = NOW(), date_played = NOW() WHERE uid = %s AND fid = %s AND date_played = current_date",(percent_played, l['uid'], fid))

                if artists:
                    for a in artists:
                        try:
                            user_artist_history = get_assoc("INSERT INTO user_artist_history (uid, aid, time_played, date_played) VALUES(%s, %s, NOW(), current_date) RETURNING *", (l['uid'], a['aid']))
                        except psycopg2.IntegrityError, err:
                            query("COMMIT;")
                            query("UPDATE user_artist_history SET time_played = NOW() WHERE uid = %s AND aid = %s AND date_played = current_date",(l['uid'], a['aid']))
                            
        
            self.last_percent_played = math.ceil(percent_played)

    

    def set_attribs(self, quick=True):
        if not self.db_info:
            return
        self.fid = self.db_info['fid']
        self.ltp = self.db_info['ltp']
        self.mtime = self.db_info['mtime']
        self.dirname = self.db_info['dir']
        self.basename = self.db_info['basename']
        self.filename = os.path.join(self.db_info['dir'], self.db_info['basename'])
        if not quick:
            self.get_artists()
            self.get_albums()
            self.get_genres()

    def get_artists(self):
        self.artists = get_results_assoc("SELECT * FROM artists a, file_artists fa WHERE fa.fid = %s AND fa.aid = a.aid",(self.fid,))
        
    def get_albums(self):
        self.albums = get_results_assoc("SELECT * FROM albums al, album_files af WHERE af.fid = %s AND af.alid = al.alid", (self.fid,))

    def get_genres(self):
        self.genres = get_results_assoc("SELECT * FROM genres g, file_genres fg WHERE fg.fid = %s AND g.gid = fg.gid",(self.fid,))

    def insert(self):
        if self.db_info:
            return
        self.get_tags()
        self.db_info = get_assoc("INSERT INTO files(dir, basename) VALUES(%s, %s) RETURNING *", (self.dirname, self.basename))
        self.set_attribs()
        print "insert:", self.dirname, self.basename
        pp.pprint(self.db_info)

        if isinstance(self.tags_easy, dict) and self.tags_easy.has_key('artist') and self.tags_easy['artist']:
            query("DELETE FROM file_artists WHERE fid = %s", self.db_info['fid'])
            for a in self.tags_easy['artist']:
                aids = self.get_aids_by_artist_string(a)
                for aid in aids:
                    query("INSERT INTO file_artists(fid, aid) VALUES(%s, %s)", (self.db_info['fid'], aid))

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

        artist = get_assoc("SELECT * FROM artists WHERE artist = %s", (artist_name,))
        if not artist:
            print "inserting artist :" ,artist_name
            artist = get_assoc("INSERT INTO artists (artist) VALUES(%s) RETURNING *", (artist_name,))

        self.artists.append(artist)

        association = get_assoc("SELECT * FROM file_artists WHERE fid = %s AND aid = %s", (self.fid, artist['aid']))
        if not association:
            print "associating artist:",artist_name
            association =  get_assoc("INSERT INTO file_artists (fid, aid) VALUES(%s, %s) RETURNING *", (self.fid, artist['aid']))

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

        q = pg_cur.mogrify("INSERT INTO tags (fid, tag_name,tag_value) VALUES(%s,%s,%s)", (fid, key, value))
        print "value-type:",type(value)
        print "query:",q
        query("INSERT INTO tags (fid, tag_name,tag_value) VALUES(%s,%s,%s)", (fid, key, value))

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

        query("UPDATE files SET mtime = %s WHERE fid = %s", (self.mtime, fid))

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

        album = get_assoc("SELECT * FROM albums WHERE album_name = %s AND aid = %s",(album_name, aid))

        if not album:
            print "associating album:", album_name
            album = get_assoc("INSERT INTO albums (album_name, aid) VALUES(%s,%s) RETURNING *",(album_name, aid))

        album_file = get_assoc("SELECT * FROM album_files WHERE alid = %s AND fid = %s", (album['alid'], self.fid))
        if not album_file:
            print "associating file to album:", album_name
            album_file = get_assoc("INSERT INTO album_files (alid, fid) VALUES(%s,%s) RETURNING *", (album['alid'], self.fid))

        self.albums.append(album)

    def process_album(self):
        if self.tags_easy and self.tags_easy.has_key('album') and self.tags_easy['album']:
            if isinstance(self.tags_easy['album'],list):
                for al in self.tags_easy['album']:
                    for a in self.artists:
                        self.add_album(al, a['aid'])
            elif self.tags_easy['album']:
                al = self.tags_easy['album']
                for a in self.artists:
                    self.add_album(al, a['aid'])

    def process_genre(self):
        if self.tags_easy and self.tags_easy.has_key('genre') and self.tags_easy['genre']:
            if isinstance(self.tags_easy['genre'],list):
                for g in self.tags_easy['genre']:
                    self.add_genre(g)

            # print self.tags_hard
        if self.tags_hard and self.tags_hard.has_key('TCON') and self.tags_hard['TCON']:
            if isinstance(self.tags_hard['TCON'].text,list):
                for g in self.tags_hard['TCON'].text:
                    self.add_genre(g)

    def add_genre(self, genre_name):
        for g in self.genres:
            if g['genre'] == genre_name:
                return
        genre = get_assoc("SELECT * FROM genres WHERE genre = %s",(genre_name,))
        if not genre:
            print "inserting genre:",genre_name
            genre = get_assoc("INSERT INTO genres (genre, enabled) VALUES(%s, %s) RETURNING *", (genre_name, True))

        association = get_assoc("SELECT * FROM file_genres WHERE fid = %s AND gid = %s", (self.fid, genre['gid']))

        if not association:
            print "associating genre:", genre_name
            association = get_assoc("INSERT INTO file_genres (fid, gid) VALUES(%s, %s) RETURNING *", (self.fid, genre['gid']))

        self.genres.append(genre)
    
        
if __name__ == "__main__":
    import sys
    for arg in sys.argv[1:]:
        try:
            if os.path.isfile(arg):
                obj = Local_File(filename=arg, insert=True)
                print obj.filename
        except CreationFailed, e:
            print "CreationFailed:",e



    
