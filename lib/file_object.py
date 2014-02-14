#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# file_object.py -- File object
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

import psycopg2
import psycopg2.extras

from os.path import basename, dirname, splitext, realpath, getmtime
from sys import exit
import time, datetime, re, pytz

audio_ext = ['.mp3','.wav','.ogg','.wma','.flac']
audio_with_tags = ['.mp3','.ogg','.wma','.flac']
video_ext = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv','.mp4', '.m4a', '.mov']

try:
    import mutagen
    from mutagen.id3 import APIC, PRIV, GEOB, MCDI, TIPL, ID3TimeStamp, UFID, TMCL, PCNT, RVA2, WCOM, COMM, Frame

except ImportError, err:
	print "mutagen isn't installed"
	print "run sudo apt-get install python-mutagen"
	exit(1)


numeric = re.compile("^[0-9]+$")

class File_Obj:
    def __init__(self,filename=None, fid=None, eid=None, insert=False, 
                 is_file=True, is_netcast=False):
        self.fid = fid
        self.eid = eid
        self.artists = []
        self.albums = []
        self.genres = []
        self.album_artists = None
        self.dirname = ""
        self.basename = ""
        self.is_file = is_file
        self.is_netcast = is_netcast
        if filename:
            filename = realpath(filename)
        self.filename = filename
        
        self.valid_ext = False
        self.file_db_info = None
        self.tags_easy = None
        self.tags_hard = None

        if fid != None:
            self.file_db_info = get_assoc("SELECT * FROM files WHERE fid = %s LIMIT 1", (fid,))

        if eid != None:
            self.file_db_info = get_assoc("SELECT * FROM netcast_episodes WHERE eid = %s LIMIT 1", (eid,))

        if filename != None:
            self.dirname = dirname(filename)
            self.basename = basename(filename)
            self.root, self.ext = splitext(self.basename)
            if self.ext.lower() not in audio_ext and self.ext.lower() not in video_ext:
                return
            self.valid_ext = True

            self.add_or_get_file_db_info()

            if self.ext.lower() in audio_with_tags:
                print "ext:",self.ext
                try:
                    self.tags_easy = mutagen.File(self.filename, easy=True)
                    self.tags_hard = mutagen.File(self.filename)
                    self.process_artist_tag()
                except mutagen.mp3.HeaderNotFoundError:
                    pass

            self.process_filename()
            self.process_genre()
            self.process_album()
    
    def process_artist_tag(self):
        if not self.tags_easy or not self.tags_easy.has_key('artist'):
            return

        if isinstance(self.tags_easy['artist'], list):
            print "self.tags_easy['artist']:",self.tags_easy['artist']
            for a in self.tags_easy['artist']:
                combos = self.parse_artist_string(a)
                self.process_artist_combos(combos)
        else:
            print "not list:",self.tags_easy['artist']
            combos = self.parse_artist_string(self.tags_easy['artist'])
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


    def add_artist(self, artist_name):
        if artist_name == None:
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
        

    def process_filename(self):
        print "process_filename"
        base, ext = splitext(self.basename)
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
    

    def add_or_get_file_db_info(self):
        # TODO: Add check for podcasts/streams.

        if self.dirname and self.basename:
            self.file_db_info = get_assoc("SELECT * FROM files WHERE dir = %s AND basename = %s LIMIT 1", (self.dirname, self.basename))
            if not self.file_db_info:
                print "inserting file_db_info:%s/%s" % (self.dirname,self.basename)
                self.file_db_info = get_assoc("INSERT INTO files (dir, basename) VALUES(%s,%s) RETURNING *",(self.dirname, self.basename))

        self.fid = self.file_db_info['fid']

    ########################

    def getmtime(self):
        t = getmtime(self.filename)
        self.mtime = datetime.datetime.fromtimestamp(t)
        tz = time.strftime("%Z", time.gmtime())
        localtz = pytz.timezone(tz)
        self.mtime = localtz.localize(self.mtime)
        return self.mtime

    def mtime_changed(self):
        if not self.file_db_info:
            return True
        self.getmtime()
        if self.mtime != self.file_db_info['mtime']:
            return True

        print "self.mtime:",self.mtime,"==",self.file_db_info['mtime']
        return False

    def insert(self):
        self.get_tags()
        self.file_db_info = get_assoc("INSERT INTO files(dir, basename) VALUES(%s, %s) RETURNING *", (self.dirname, self.basename))
        self.fid = self.file_db_info['fid']

        print "dbInfo:",self.file_db_info
        if isinstance(self.tags_easy, dict) and self.tags_easy.has_key('artist') and self.tags_easy['artist']:
            query("DELETE FROM file_artists WHERE fid = %s", self.file_db_info['fid'])
            for a in self.tags_easy['artist']:
                aids = self.get_aids_by_artist_string(a)
                for aid in aids:
                    query("INSERT INTO file_artists(fid, aid) VALUES(%s, %s)", (self.file_db_info['fid'], aid))
            

        self.update_tags()
        self.update_album()
    

    def update(self):
        print "UPDATE"
        self.get_tags()
        self.update_tags()
        if self.tags_easy and self.tags_easy.has_key('artist') and self.tags_easy['artist']:
            print "ARTIST:",self.tags_easy['artist']
            for a in self.tags_easy['artist']:
                self.get_aids_by_artist_string(a)

        if self.tags_easy and self.tags_easy.has_key('album') and self.tags_easy['album']:
            self.update_album()

    def update_album(self):
        if self.tags_easy and self.tags_easy.has_key('album') and self.tags_easy['album']:
            for a in self.artists:
                for al in self.tags_easy['album']:
                    al = al.strip()
                    if not al:
                        continue
                    if type(al) == str:
                        al = unicode(al, "utf8", errors="replace")
                    print "AL:",self.tags_easy['album']
                    # print "AL:", al
                    album = self.get_album_by_album_name_and_aid(al, a['aid'])
                    print "album_file:",self.add_album_file(album['alid'], self.fid)
            return

    def add_album_file(self, alid, fid, insert=True):
        
        album_file = get_assoc("SELECT * FROM album_files WHERE alid = %s AND fid = %s", (alid, fid))
        print "album_file:",album_file
        if not album_file:
            album_file = get_assoc("INSERT INTO album_files (alid, fid) VALUES(%s, %s) RETURNING *",(alid, fid))
        return album_file
    
    def get_album_by_album_name_and_aid(self, album_name, aid, insert=True):

        for al in self.albums:
            if al['album_name'] == album_name and al['aid'] == aid:
                return al
        
        album = get_assoc("SELECT * FROM albums al, artists a, album_artists ala WHERE al.album_name = %s AND a.aid = %s AND ala.aid = a.aid AND ala.alid = al.alid", (album_name, aid))

        
        if not album:
            album = get_assoc("INSERT INTO albums (album_name) VALUES(%s) RETURNING *",(album_name,))
            print "ALBUM2:",album
            print "ALID:",album['alid']
            album_artists = get_assoc("SELECT * FROM album_artists WHERE alid = %s AND aid = %s", (album['alid'], aid))

            if not album_artists:
                album_artists = get_assoc("INSERT INTO album_artists (alid, aid) VALUES(%s, %s) RETURNING *", (album['alid'], aid))

            print "album_artists:",album_artists
                
            album = get_assoc("SELECT * FROM albums al, artists a, album_artists ala WHERE al.album_name = %s AND a.aid = %s AND ala.aid = a.aid AND ala.alid = al.alid", (album_name, aid))

        found = False
        for al in self.albums:
            if al['alid'] == album['alid']:
                found = True
                break;

        if not found:
            self.albums.append(album)
        print "ALBUM3:", album
        for k,v in album.iteritems():
            print k,"=",v
        return album

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


    def get_tags(self):
        if self.filename:
            # print "getting tags:", self.filename
            self.tags_easy = mutagen.File(self.filename, easy=True)
            # self.tags_hard = mutagen.File(self.filename)
            # print "tags_easy:",self.tags_easy
            # print "tags_hard:",self.tags_hard

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

    def update_tags(self, fid=None):
        if not fid:
            fid = self.file_db_info['fid']

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


    def update_hard_tags(self, fid=None):
        if not fid:
            fid = self.file_db_info['fid']

        if not self.mtime_changed():
            print "MTIME not changed:", self.filename
            return

        print "TAGS_HARD:",self.tags_hard
        for k in self.tags_hard.keys():
            
            v = self.tags_hard[k]
            if type(k) != unicode:
                print "converting k to unicode:",k
                k = unicode(k, "utf8",errors="replace")
            # k = k[:255]
            if isinstance(v,ID3TimeStamp):
                print "V:",v
                self.insert_tag_to_db(fid, k, v)
                continue

            if isinstance(v, Frame):
                print "FRAME:"
                for f in v._framespec:
                    print "k:",k
                    print "name:",f.name
                    value = getattr(v,f.name)
                    print "value:", value
                    kf = "%s[%s]" % (k, f.name)
                    print "before:",kf
                    if type(kf) != unicode:
                        kf = str(kf)
                        kf = unicode(kf, "utf8", errors='replace')
                    # 
                    print "after kf:",kf
                    try:
                        self.insert_tag_to_db(fid, kf, value)
                    except psycopg2.DataError, err:
                        print "psycopg2.DataError:",err
                        print "filename:",self.filename
                        pg_conn.commit()
                        print "changing kf1"
                        kf = kf.replace("'\\x00\\x00\\x00'","")
                        print "kf:",kf
                        try:
                            self.insert_tag_to_db(fid, kf, value)
                        except psycopg2.DataError:
                            print "psycopg2.DataError *2nd error:",err
                            pg_conn.commit()
                        print "ERROR"
                        time.sleep(5)
                    except psycopg2.IntegrityError, err:
                        print "filename:",self.filename
                        print "psycopg2.IntegrityError:",err
                        pg_conn.commit()
                        print "ERROR2"

                        time.sleep(5)

                # if isinstance(v, WCOM):
                #   sys.exit()

                continue
            if isinstance(v, APIC):
                print "APIC:",v
                for f in v._framespec:
                    print "name:",f.name
                    value = getattr(v,f.name)
                    if type(value) == str:
                        print "value:[hidden]"
                    else:
                        print "value:[hidden]"
                    kf = "%s[%s]" % (k, f.name)
                    print "kf:", kf
                    self.insert_tag_to_db(fid, kf, value)
                continue

            print "K:",k
            print "V:",v
            print "tag:%s=%s" % (k,v)
            try:
                self.insert_tag_to_db(fid, k, v)
            except psycopg2.DataError, err:
                print "filename:",self.filename
                print "psycopg2.DataError:",err
                pg_conn.commit()
                print "changing kf2"
                kf = k.replace("'\\x00\\x00\\x00'","")
                print "kf:",kf
                self.insert_tag_to_db(fid, kf, v)
                print "ERROR"
                time.sleep(5)
            except psycopg2.IntegrityError, err:
                print "filename:",self.filename
                print "psycopg2.IntegrityError:",err
                pg_conn.commit()
                print "ERROR2"

                time.sleep(5)
            
           

        query("UPDATE files SET mtime = %s WHERE fid = %s", (self.mtime, fid))

