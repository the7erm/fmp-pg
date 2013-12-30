#!/usr/bin/env python
# fmp_sqlalchemy_models/file_info.py -- Information about file.
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
import re
import os

from baseclass import BaseClass, log
from alchemy_session import Base
from sqlalchemy import Table, Integer, ForeignKey, DateTime, String, Column,\
                       and_
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3, HeaderNotFoundError

from album import Album
from artist import Artist
from genre import Genre
from user import User
from user_file_info import UserFileInfo
from user_history import UserHistory
from title import Title
from keywords import Keywords

numeric = re.compile("^[0-9]+$")

file_albums_association_table = Table('file_albums', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('alid', Integer, ForeignKey('albums.alid'))
)

file_artists_association_table = Table('file_artists', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('aid', Integer, ForeignKey('artists.aid'))
)

file_genre_association_table = Table('file_genres', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('gid', Integer, ForeignKey('genres.gid'))
)

file_keywords_association_table = Table("file_keywords", Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('kid', Integer, ForeignKey('keywords.kid'))
)

file_titles_association_table = Table('file_titles', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('tid', Integer, ForeignKey('titles.tid'))
)

class FileInfo(BaseClass, Base):
    __tablename__  = 'files_info'

    __repr_fields__ = [
        'fid',
        'fingerprint',
        'size',
         # 'locations',
        'ltp',
        'artists',
        'titles',
        'genres',
        'albums',
        'listeners_ratings',
        'keywords',
        'history',
        'dontpick',
        'preload',
    ]
    
    fid = Column(Integer, primary_key=True)
    ltp = Column(DateTime(timezone=True), nullable=True, index=True)
    
    fingerprint = Column(String(132), index=True)
    file_size = Column(Integer, index=True, default=0)
    
    artists = relationship("Artist", 
                           secondary=file_artists_association_table,
                           backref="files")

    titles = relationship("Title", 
                           secondary=file_titles_association_table,
                           backref="files")

    albums = relationship("Album", 
                          secondary=file_albums_association_table,
                          backref="files")

    genres = relationship("Genre", 
                          secondary=file_genre_association_table,
                          backref="files")
    user_file_info = relationship("UserFileInfo",
                                  backref="file")
    history = relationship("UserHistory",
                           backref="file",
                           primaryjoin="and_(UserHistory.fid == FileInfo.fid, "
                                             "User.listening == True, "
                                             "User.uid == UserHistory.uid, "
                                             "UserHistory.time_played != None)",
                           order_by=UserHistory.time_played.desc)

    listeners_ratings = relationship("UserFileInfo",
        primaryjoin="and_(UserFileInfo.fid == FileInfo.fid, "
                         "User.listening == True, "
                         "User.uid == UserFileInfo.uid)")

    keywords = relationship("Keywords",
                            secondary=file_keywords_association_table,
                            backref="files")

    locations = relationship("FileLocation", 
                             backref="file")

    dontpick = relationship("DontPick", backref="file")
    preload = relationship("Preload", backref="file")

    def mark_as_played(self, when=None, percent_played=0, uids=None, session=None):
        log.warn("TODO: mark_as_played")
        # Step 1 mark file as played
        self.ltp = self.now_if_none(when)
        self.mark_artists_as_played(session=session)
        self.mark_listeners_as_played(when, percent_played, uids=uids, 
                                      session=session)
        self.save(session=session)

    def mark_listeners_as_played(self, when=None, percent_played=0, uids=None, 
                                 session=None):
        log.info("MARK LISTENERS AS PLAYED")
        when = self.now_if_none(when)
        self.add_user_file_info_for_all_listeners(session=session)
        listeners_ratings = self.get_listener_ratings(uids, session=session)
        for user_rating in listeners_ratings:
            user_rating.mark_as_played(when=when, percent_played=percent_played,
                                       session=session)

    def mark_artists_as_played(self, when=None, session=None):
        when = self.now_if_none(when)
        session.add(self)
        for a in self.artists:
            a.mark_as_played(when, session=session)
        

    def rate(self, uid=None, rating=None, selected=False, session=None):
        log.info("Rate uid:%s rating:%s selected:%s", uid, rating, selected)
        if selected:
            user_file_info = self.get_selected()
            user_file_info.rate(rating, session=session)
            return

        if uid is None:
            return
        for user_file_info in self.listeners_ratings:
            if user_file_info.uid == uid:
                user_file_info.rate(rating, session=session)

    def get_selected(self):
        selected_listener = None
        for l in self.listeners_ratings:
            if l.user.selected == True:
                selected_listener = l
                break
        if selected_listener is None:
            selected_listener = self.listeners_ratings[0]
            self.listeners_ratings[0].selected = True
        return selected_listener

    def get_locations(self):
        return self.locations

    def update_id3_info(self, session=None):
        for loc in self.locations:
            if loc.ext != '.mp3':
                self.set_artist_title_from_base(loc.base, session=session)
            else:
                self.set_id3_info(loc.filename, loc.base, session=session)

    def set_id3_info(self, filename=None, base=None, session=None):
        if filename is None or base is None:
            for loc in self.locations:
                self.set_id3_info(loc.filename, loc.base, session=session)
            return
        
        try:
            audio = MP3(filename, ID3=EasyID3)
        except HeaderNotFoundError:
            self.set_artist_title_from_base(base, session=session)
            return

        fields = [("artist", Artist, "artists"),
                  ("title", Title, "titles"),
                  ("album", Album, "albums"),
                  ("genre", Genre, "genres")]
        for key, get_type, attr in fields:
            if key in audio:
                for value in audio[key]:
                    value = value.strip()
                    if not value:
                        continue
                    if key == "artist":
                        self.add_artists(value)
                        continue

                    obj = self.insert_or_get(get_type, value, session=session)
                    current_values = getattr(self, attr)
                    # print "current_values file_info.%s:" % attr,current_values
                    if obj not in current_values:
                        current_values.append(obj)
                        setattr(self, attr, current_values)

    def add_artists(self, artist_string="", session=None):
        artists = self.parse_artist_string(artist_string)
        if not artists:
            return

        for artist in self.artists:
            obj = self.insert_or_get(Artist, artist, session=session)
            if obj not in self_artists:
                self.artists.append(obj)

    def set_artist_title_from_base(self, base=None, session=None):
        if base is None:
            locations = self.get_locations()
            for loc in locations:
                self.set_artist_title_from_base(loc.base)
            return

        base = self.utf8(base.replace('_', ' ').strip())
        artist = ""
        title = ""
        try:
            artist, title = base.split(' - ',1)
        except ValueError:
            try:
                artist, title = base.split('-',1)
            except ValueError:
                title = base
        artist = artist.strip()
        title = title.strip()
        self.add_artists(artist)
        if title:
            obj = self.insert_or_get(Title, title, session)
            if obj not in self.titles:
                self.titles.append(obj)

    def insert_or_get(self, get_type, name, session=None):
        
        try:
            info = session.query(get_type)\
                          .filter(get_type.name==name)\
                          .limit(1)\
                          .one()
        except NoResultFound:
            info = get_type(name=name)
            info.save(session=session)
            
        return info

    def get_listeners(self, session=None):
        listeners = session.query(User)\
                           .filter(User.listening == True)\
                           .all()
        return listeners

    def add_user_file_info_for_all_listeners(self, session=None):
        listeners = self.get_listeners(session)
        for user in listeners:
            self.add_user_file_info(user, session=session)

    def add_user_file_info(self, user, session=None):
        session.add(self)
        try:
            ufinfo = session.query(UserFileInfo).filter(and_(
                UserFileInfo.uid == user.uid,
                UserFileInfo.fid == self.fid
            ))\
            .limit(1)\
            .one()
        except NoResultFound:
            ufinfo = UserFileInfo(uid=user.uid, 
                                  fid=self.fid, 
                                  rating=DEFAULT_RATING,
                                  skip_score=DEFAULT_SKIP_SCORE, 
                                  percent_played=DEFAULT_PERCENT_PLAYED, 
                                  true_score=DEFAULT_TRUE_SCORE)
            ufinfo.save(session=session)

    def parse_artist_string(self, artist_string=""):
        artist_string = artist_string.strip()
        if not artist_string:
            return []
        combos = []
        combos.append(artist_string)
        lines = artist_string.splitlines()
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
                        p = unicode(p, "utf8", errors='replace')
                    except UnicodeEncodeError, err:
                        log.error("UnicodeEncodeError parts:%s", err)
                        exit()
                if numeric.match(p):
                    continue

                if combos.count(p) == 0:
                    combos.append(p)

        return combos

    def get_words_from_string(self, string):
        if not string or not isinstance(string, (str, unicode)):
            # print "NOT VALID:",string
            # print "TYPE:",type(string)
            return []

        string = self.utf8(string.strip().lower())
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

    def set_db_keywords(self, session=None):
        keywords = []
        # print "filename:", os.path.join(self.dirname, self.basename)
        keywords += [self.fingerprint]
        print "LOOPING THROUGH LOCATIONS"
        for loc in self.locations:
            root, ext = os.path.splitext(loc.basename)
            # keywords += self.get_words_from_string(loc.basename)
            keywords += self.get_words_from_string(root)
            keywords += self.get_words_from_string(ext)
        
        print "LOOPING THROUGH ARTISTS"
        for a in self.artists:
            keywords += self.get_words_from_string(a.name)

        print "LOOPING THROUGH ALBUMS"
        for a in self.albums:
            keywords += self.get_words_from_string(a.name)

        print "LOOPING THROUGH GENRES"
        for g in self.genres:
            keywords += self.get_words_from_string(g.name)
        

        for t in self.titles:
            keywords += self.get_words_from_string(t.name)
        
        keywords = list(set(keywords))
        for i, k in enumerate(keywords):
            keywords[i] = self.utf8(k.strip())
        keywords = list(set(keywords))

        txt = " ".join(keywords) 
        keywords = list(set(txt.split()))
        if keywords.count("-"):
            keywords.remove("-")
        new_keywords = sorted(keywords, key=unicode.lower)
        # txt = " ".join(keywords)
        
        keywords_to_delete = []

        for kw in self.keywords:
            if kw.word not in new_keywords:
                keywords_to_delete.append(kw)

        for kw in keywords_to_delete:
            self.keywords.remove(kw)
            # print "remove:",kw

        for nkw in new_keywords:
            found = False
            for kw in self.keywords:
                if nkw == kw.word:
                    found = True
                    break
            if found:
                continue

            word = self.find_or_insert_keyword(nkw, session=session)
            self.keywords.append(word)

        self.keywords = list(set(self.keywords))
        #if keywords_to_delete:
        #   print self.keywords
        session.commit()
        


    def find_or_insert_keyword(self, word, session=None):
        
        kw = None
        try:
            kw = session.query(Keywords).filter(Keywords.word == word).limit(1).one()
        except NoResultFound:
            kw = Keywords(word=word)
            session.add(kw)
            # session.commit()
        
        return kw

    @property
    def has_changed(self):
        has_changed = False
        for loc in self.locations:
            if loc.has_changed:
                has_changed = True
                break
        
        return has_changed

    def pre_save(self, session=None):
        if self.has_changed:
            self.update_id3_info(session=session)
        self.set_db_keywords(session=session)
        self.add_user_file_info_for_all_listeners(session=session)
        # self.file_exists = self.exists

    @property
    def filename(self):
        for l in self.locations:
            if l.exists:
                return l.filename
        return None

    @property
    def uri(self):
        for l in self.locations:
            if l.exists:
                return l.uri
        return None

    def get_listener_ratings(self, uids=None, session=None):
        print "GET LISTENERS RATINGS:", uids
        if uids is None:
            listeners_ratings = self.listeners_ratings
        else:
            listeners_ratings = session.query(UserFileInfo)\
                                       .filter(and_(
                                            UserFileInfo.uid.in_(uids),
                                            UserFileInfo.fid == self.fid))\
                                       .all()

        print "LISTENERS RATINGS:", listeners_ratings
        
        return listeners_ratings

    def inc_skip_score(self, uids=None, session=None):
        listeners_ratings = self.get_listener_ratings(uids, session=session)
        for l in listeners_ratings:
            l.inc_skip_score(session=session)

    def deinc_skip_score(self, uids=None, session=None):
        listeners_ratings = self.get_listener_ratings(uids, session=session)
        for l in listeners_ratings:
            l.deinc_skip_score(session=session)

    @property
    def artist_title(self):
        artist = ""
        title = ""
        for a in self.artists:
            if a.name:
                artist = a.name
                break

        for t in self.titles:
            if t.name:
                title = t.name
                break
        if artist and title:
            
            return "%s - %s" % (artist, title)
        
        return self.base

    @property
    def base(self):
        base = None
        for l in self.locations:
            if l.exists:
                base = l.base
                break
        return base

    @property
    def rating(self):
        selected = self.get_selected()
        return selected.rating

    @property
    def exists(self):
        exists = False
        for l in self.locations:
            if l.exists:
                exists = True
                break
        return exists

    @property 
    def ext(self):
        ext = None
        for l in self.locations:
            if l.exists:
                ext = l.ext
                break
        return ext

    @property
    def size(self):
        size = 0
        for l in self.locations:
            if l.exists:
                size = l.file_size
                break
        return size

    @property
    def mimetype(self):
        ext = self.ext
        return MIME_TYPES.get(ext)

    def get_best_mime(self, supported_mimetypes):
        if self.mimetype in supported_mimetypes:
            return self.mimetype

        if MIME_TYPES['.mp3'] in supported_mimetypes:
            return MIME_TYPES['.mp3']
        if MIME_TYPES['.ogg'] in supported_mimetypes:
            return MIME_TYPES['.ogg']
        return None
