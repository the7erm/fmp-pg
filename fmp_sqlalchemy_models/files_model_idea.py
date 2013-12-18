#!/usr/bin/env python
# fmp_sqlalchemy_models/files_model.py -- model for files db.
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

import os
import sys
import time
import datetime
import hashlib
import re
import pytz
import pprint
import urllib
import gtk
import logging
import json

from alchemy_session import make_session

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy import Column, Integer, String, DateTime, Text, Float,\
                       UniqueConstraint, Boolean, Table, ForeignKey, Date, \
                       Unicode, and_
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from sqlalchemy.orm.exc import NoResultFound
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3, HeaderNotFoundError

gtk.gdk.threads_init()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
hanlder = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hanlder.setFormatter(formatter)
hanlder.setLevel(logging.DEBUG)
log.addHandler(hanlder)

numeric = re.compile("^[0-9]+$")
DEFAULT_RATING = 6
DEFAULT_SKIP_SCORE = 8
DEFAULT_PERCENT_PLAYED = 50.0
DEFAULT_TRUE_SCORE = ((DEFAULT_RATING * 2 * 10) + 
                      (DEFAULT_SKIP_SCORE * 10) + 
                      DEFAULT_PERCENT_PLAYED
                     ) / 3

Base = declarative_base()

file_genre_association_table = Table('file_genres', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('gid', Integer, ForeignKey('genres.gid'))
)

file_artists_association_table = Table('file_artists', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('aid', Integer, ForeignKey('artists.aid'))
)

file_titles_association_table = Table('file_titles', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('tid', Integer, ForeignKey('titles.tid'))
)

file_albums_association_table = Table('file_albums', Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('alid', Integer, ForeignKey('albums.alid'))
)

file_keywords_association_table = Table("file_keywords", Base.metadata,
    Column('fid', Integer, ForeignKey('files_info.fid')),
    Column('kid', Integer, ForeignKey('keywords.kid'))
)

class BaseClass(object):

    def pre_save(self, session=None):
        return

    def post_save(self, session=None):
        return

    def save(self, session=None):
        wait()
        start_save = datetime.datetime.now()
        self.pre_save(session=session)
        saved = False
        try:
            session.add(self)
            session.commit()
            saved = True
        except IntegrityError, e:
            session.rollback()
            log.error("IntegrityError:%s ROLLBACK", e)
        except InvalidRequestError, e:
            session.rollback()
            log.error("InvalidRequestError:%s ROLLBACK", e)
        if saved:
            self.post_save(session=session)
        delta = datetime.datetime.now() - start_save
        log.info("%s save time:%s", self.__class__.__name__, delta.total_seconds())
        wait()
        

    def getattr(self, obj, name, default=None):
        if '.' in name:
            name, rest = name.split('.', 1)
            obj = getattr(obj, name)
            if obj:
                return self.getattr(obj, rest, default=default)
            return None
        if not hasattr(obj, name):
            return default

        return getattr(obj, name)

    def get_value_repr(self, values, value, field=None, padding=0):
        this_padding = " "*padding
        if isinstance(value, list) and value:
            start_string = "%s=[" % (field,)
            values.append(start_string)
            for val in value:
                self.get_value_repr(values, val, padding=4)
                 
            values.append("]")
            return
        values_string = value.__repr__()
        lines = values_string.split("\n")
        if field:
            values.append("%s=%s" % (field, lines[0]))
        else:
            values.append(this_padding+lines[0])
        for l in lines[1:]:
            values.append(this_padding+l)

    def get_repr(self, obj, fields):
        title = self.__class__.__name__
        values = []
        title_length = len(title) + 2
        padding = " "*title_length
        join_text = "\n%s" % padding

        for field in fields:
            value = self.getattr(obj, field)
            self.get_value_repr(values, value, field, padding=len(field)+2)
        
        return "<%s(%s)>" % (title, join_text.join(values))

    def __repr__(self):
        return self.get_repr(self, self.__repr_fields__)

    def utf8(self, string):
        if not isinstance(string, unicode):
            return unicode(string, "utf8", errors="replace")
        return string

    def now_if_none(self, datetime_object=None):
        if datetime_object is not None:
            return datetime_object
        return datetime.datetime.now()

    def json(self, fields=None, session=None):
        if fields is None:
            if hasattr(self, '__json_fields__') and getattr(self, '__json_fields__'):
                fields = getattr(self, '__json_fields__')
            else:
                fields = self.__repr_fields__
        obj = {}

        for field in fields:
            val = self.getattr(self, field)
            # print "Field:%s" % field
            # print "field %s:%s %s" % (field, val, type(val))
            
            if isinstance(val, (datetime.datetime, datetime.date)):
                val = val.isoformat()
                # print "field %s:%s %s" % (field, val, type(val))
            obj[field] = val
            if isinstance(val, list):
                new_val = []
                for v in val:
                    new_val.append(v.to_dict(session=session))
                obj[field] = new_val

        return json.dumps(obj, indent=4)

    def to_dict(self, fields=None, session=None):
        if fields is None:
            if hasattr(self, '__json_fields__') and getattr(self, '__json_fields__'):
                fields = getattr(self, '__json_fields__')
            else:
                fields = self.__repr_fields__
        obj = {}
        for field in fields:
            val = self.getattr(self, field)
            if isinstance(val, (datetime.datetime, datetime.date)):
                val = val.isoformat()
            # print "to_dict:%s %s %s" % (field, val, type(val))
            obj[field] = val
            if isinstance(val, list):
                new_val = []
                for v in val:
                    new_val.append(v.to_dict(session=session))
                obj[field] = new_val
        return obj


class UserHistory(BaseClass, Base):
    __tablename__ = 'user_history'

    __table_args__ = (
        UniqueConstraint('uid', 'fid', 'date_played', 
                         name='uniq_idx_user_history_uid_fid_date_played'),
    )
    __repr_fields__ = [
        'uhid',
        'uid',
        'ufid',
        'fid',
        'rating',
        'skip_score',
        'percent_played',
        'true_score',
        'time_played',
        'date_played',
        'user.uname'
    ]
    uhid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey("users.uid"))
    ufid = Column(Integer, ForeignKey("user_file_info.ufid"))
    fid = Column(Integer, ForeignKey("files_info.fid"))
    # eid = Column(Integer, ForeignKey("episodes.eid"))
    rating = Column(Integer)
    skip_score = Column(Integer)
    percent_played = Column(Float)
    true_score = Column(Float)
    time_played = Column(DateTime(timezone=True))
    date_played = Column(Date)
    user = relationship("User")


class FileLocation(BaseClass, Base):
    __tablename__  = 'file_location'
    __table_args__ = (
        UniqueConstraint('dirname', 'basename', name='uniq_idx_dirname_basename'),
    )
    __repr_fields__ = [
        'flid',
        'fid',
        'dirname',
        'basename',
        'mtime',
        'ctime',
        'file_exists',
        'size',
        'file'
    ]
    fid = Column(Integer, ForeignKey('files_info.fid'))
    flid = Column(Integer, primary_key=True)
    dirname = Column(Unicode, index=True)
    basename = Column(Unicode, index=True)
    mtime = Column(DateTime(timezone=False), nullable=True, index=True)
    ctime = Column(DateTime(timezone=False), nullable=True, index=True)
    file_exists = Column(Boolean, default=False)
    size = Column(Integer, index=True, default=0)

    def __init__(self, *args, **kwargs):
        self.file_stats = None
        Base.__init__(self, *args, **kwargs)

    @property
    def ext(self):
        base, ext = os.path.splitext(self.basename)
        return ext.lower()

    @property
    def filename(self):
        return os.path.realpath(
            os.path.expanduser(
                os.path.join(self.dirname, self.basename)
            )
        )

    @property
    def uri(self):
        filename = self.filename
        if self.exists:
            return "file://%s" % (urllib.quote(filename.encode('utf8')),)
        else:
            return urllib.quote(filename.encode('utf8'))

    @property
    def base(self):
        base, ext = os.path.splitext(self.basename)
        return base

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def has_changed(self):
        mtime = self.get_mtime()
        ctime = self.get_ctime()
        size = self.get_size()
        if self.mtime != mtime:
            log.info("mtime %s != self.mtime %s", mtime, self.mtime)
            
        if self.ctime != ctime:
            log.info("ctime %s != self.ctime %s", ctime, self.ctime)
        if self.size != size:
            log.info("size %s != self.size %s", size, self.size)
        return (self.mtime != mtime or self.ctime != ctime or self.size != size)

    def update_mtime(self):
        self.mtime = self.get_mtime()

    def update_ctime(self):
        self.mtime = self.get_ctime()

    def update_size(self):
        self.size = self.get_size()

    def get_mtime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_mtime)

    def get_ctime(self):
        return datetime.datetime.fromtimestamp(self.file_stats.st_ctime)

    def get_size(self):
        self.set_stats()
        return self.file_stats.st_size

    def set_stats(self, force_refresh=False):
        if force_refresh:
            self.file_stats = None

        if not hasattr(self, 'file_stats'):
            self.file_stats = None

        if self.file_stats is not None:
            return
        self.file_stats = os.stat(self.filename)

    def update_stats(self, session=None):
        self.set_stats()
        self.mtime = self.get_mtime()
        self.ctime = self.get_ctime()
        self.size = self.get_size()

    def scan(self, filename=None, dirname=None, basename=None, save=True,
             session=None):
        if dirname is not None and basename is not None:
            dirname = self.utf8(dirname)
            basename = self.utf8(basename)
            filename = os.path.join(dirname, basename)

        filename = self.utf8(os.path.realpath(os.path.expanduser(filename)))
        self.dirname, self.basename = os.path.split(filename)
        if save:
            self.save(session=session)

    def pre_save(self, session=None):
        if self.has_changed:
            self.update_hash(session=session)
            self.update_stats(session=session)
            # self.update_hash()
            # self.update_mtime()

    def update_hash(self, session=None):
        self.set_stats(True)
        log.info("calculating hash:%s", self.filename)
        delta = datetime.timedelta(0, 1)
        show_update = datetime.datetime.now() + delta
        fp = open(self.filename, 'r')
        m = hashlib.sha512()
        size = self.get_size()
        fingerprint_size = 512 * 1024
        data = fp.read(fingerprint_size)
        m.update(data)
        seek = size / 2
        if seek >= fingerprint_size:
            fp.seek(seek)
            data = fp.read(fingerprint_size)
            m.update(data)

        seek = size - fingerprint_size
        if seek > (size / 2) + fingerprint_size:
            fp.seek(seek)
            data = fp.read(fingerprint_size)
            m.update(data)
        
        fingerprint = m.hexdigest()
        try:
            file_info = session.query(FileInfo).filter(and_(
                FileInfo.fingerprint == fingerprint,
                FileInfo.size == size
            )).one()
        except NoResultFound:
            file_info = FileInfo(fingerprint=fingerprint, size=size)
            file_info.save(session=session)

        self.fid = file_info.fid
        found = False
        for l in file_info.locations:
            if l.flid == self.flid:
                found = True
                break;

        if not found:
            file_info.locations.append(self)
            file_info.save(session=session)


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
    size = Column(Integer, index=True, default=0)
    
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
                                             "User.uid == UserHistory.uid)",
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
        self.mark_listeners_as_played(when, percent_played, uids=uids, session=session)
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
        for loc in self.get_locations():
            root, ext = os.path.splitext(loc.basename)
            # keywords += self.get_words_from_string(loc.basename)
            keywords += self.get_words_from_string(root)
            keywords += self.get_words_from_string(ext)
        
        for a in self.artists:
            keywords += self.get_words_from_string(a.name)

        for a in self.albums:
            keywords += self.get_words_from_string(a.name)

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
            session.commit()
        
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
        
        if uids is None:
            session.add(self)
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
                size = l.size
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


class Folder(BaseClass, Base):
    __tablename__ = 'folders'
    foid = Column(Integer, primary_key=True)
    dirname = Column(Text, index=True)
    mtime = Column(DateTime(timezone=False))
    ctime = Column(DateTime(timezone=False))
    file_count = Column(Integer, default=0)
    last_scan = Column(DateTime(timezone=True))
    scanned = Column(Boolean, default=False)
    __repr_fields__ = [
        "foid",
        'file_count',
        "dirname",
        "mtime",
        "ctime",
        "scanned"
    ]

    @property
    def needs_scan(self):
        if not self.has_media:
            return False

        mtime = self.get_mtime()
        ctime = self.get_ctime()
        file_count = self.get_files_count()
        if self.mtime != mtime:
            log.info("mtime %s != self.mtime %s", mtime, self.mtime)
        if self.ctime != ctime:
            log.info("ctime %s != self.ctime %s", ctime, self.ctime)
        if self.file_count != file_count:
            log.info("file_count %s != self.file_count %s", file_count, self.file_count)

        if not self.scanned:
            log.info("not scanned:%s", self.dirname)

        return (not self.scanned or self.mtime != mtime or self.ctime != ctime or 
                self.file_count != file_count)

    @property
    def has_media(self):
        if not hasattr(self, 'files'):
            self.get_files()

        if not self.files:
            return False

        for f in self.files:
            base, ext = os.path.splitext(f)
            ext = ext.lower()
            if ext in AUDIO_EXT or ext in VIDEO_EXT:
                return True
        return False


    def update_mtime(self):
        self.mtime = self.get_mtime()

    def update_ctime(self):
        self.mtime = self.get_ctime()

    def update_file_count(self):
        self.file_count = self.get_files_count()

    def get_mtime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_mtime)

    def get_ctime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_ctime)

    def set_stats(self, force_refresh=False):
        if force_refresh:
            self.file_stats = None

        if not hasattr(self, 'file_stats'):
            self.file_stats = None

        if self.file_stats is not None:
            return
        self.file_stats = os.stat(self.dirname)

    def update_stats(self):
        self.set_stats()
        self.mtime = self.get_mtime()
        self.ctime = self.get_ctime()
        self.file_count = self.get_files_count()

    def get_files(self):
        self.files = os.listdir(self.dirname)
        self.files.sort()
        return self.files

    def get_files_count(self):
        return len(self.get_files())

    def insert_file_into_db(self, dirname, basename):
        base, ext = os.path.splitext(basename)
        ext = ext.lower()
        if ext not in AUDIO_EXT and ext not in VIDEO_EXT:
            return
        start_time = datetime.datetime.now()
        log.info("="*80)
        # unicode(p, "utf8",errors='replace')
        dirname = dirname.decode('utf-8', errors='replace')
        basename = basename.decode('utf-8', errors='replace')
        location = False
        
        try:
            location = session.query(FileLocation).filter(
                and_(FileLocation.dirname==dirname,
                     FileLocation.basename==basename)).one()
            if not location.has_changed:
                log.info("Not changed:%s", location.filename)
                # location.save()
                # location.file.save()
                
                return
        except NoResultFound:
            pass

        if not location:
            location = FileLocation(dirname=dirname, basename=basename)
            log.info("scan:%s", location.filename)
            location.scan(dirname=dirname, basename=basename, save=False)
        log.info("saving:%s", location.filename)
        location.save()
        log.info("processed:%s", location)
        end_time = datetime.datetime.now()
        delta = end_time - start_time
        
        print delta.total_seconds()

    def scan(self, dirname=None, save=True, session=None):
        skip_dirs = [
            '/minecraft/',
            '/.minecraft/',
            '/resourcepacks/',
            '.local/share/Trash/',
            '/resources/',
        ]
        dirname = os.path.realpath(os.path.expanduser(dirname))
        skip = False
        for d in skip_dirs:
            if d in dirname:
                skip = True
                break
        if skip:
            log.info("Skipping:%s", dirname)
            return
        if os.path.isfile(dirname):
            dirname, basename = os.path.split(dirname)
            self.insert_file_into_db(dirname, basename)
            return
        self.dirname = dirname
        self.update_stats()
        log.info("Scanning dir:%s", dirname)
        for f in self.files:
            filename = os.path.join(dirname, f)
            if not os.path.isfile(filename):
                continue
            dirname, basename = os.path.split(filename)
            self.insert_file_into_db(dirname, basename)
        self.scanned = True
        if save:
            self.save(session=session)

    def pre_save(self, session=None):
        if self.needs_scan:
            self.scan(self.dirname, save=False, session=session)
        self.update_stats()

class Artist(BaseClass, Base):
    __tablename__ = 'artists'
    __repr_fields__ = [
        'aid',
        'name',
        'seq'
    ]

    aid = Column(Integer, primary_key=True)
    name = Column(Text, index=True)
    altp = Column(DateTime(timezone=True))
    seq = Column(Boolean, default=False)

    def mark_as_played(self, when=None, session=None):
        when = self.now_if_none(when)
        self.altp = when
        self.save(session=session)


class DontPick(BaseClass, Base):
    __tablename__ = 'dont_pick'
    dpfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files_info.fid'))
    reason = Column(String, default="No reason")
    junk = Column(String, default="")
    # TODO: alembic
    # alter table dont_pick  add column junk VARCHAR
    __repr_fields__ = [
        'dpfid',
        'fid',
        'file.basename',
        "reason"
    ]


class Preload(BaseClass, Base):
    __tablename__ = "preload"
    __repr_fields__ = [
        'prfid',
        'fid',
        'uid',
        'reason'
    ]
    prfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files_info.fid'))
    uid = Column(Integer, ForeignKey('users.uid'))
    priority = Column(Integer, default=1)
    reason = Column(String)


class Keywords(BaseClass, Base):
    __tablename__ = 'keywords'
    __repr_fields__ = [
        'kid',
        'word'
    ]

    kid = Column(Integer, primary_key=True)
    word = Column(Text, unique=True)


class Title(BaseClass, Base):
    __tablename__ = 'titles'
    __repr_fields__ = [
        'tid',
        'name',
    ]
    tid = Column(Integer, primary_key=True)
    name = Column(Text, index=True)


class Album(BaseClass, Base):
    __tablename__ = 'albums'
    __repr_fields__ = [
        'alid',
        'name',
        'seq'
    ]
    alid = Column(Integer, primary_key=True)
    name = Column(Text, index=True)
    seq = Column(Boolean, default=False)


class Genre(BaseClass, Base):
    __tablename__ = 'genres'
    __repr_fields__ = [
        'gid',
        'name',
        'seq',
        'enabled'
    ]

    gid = Column(Integer, primary_key=True, nullable=False)
    name = Column(Text, index=True)
    enabled = Column(Boolean, default=True, index=True)
    seq = Column(Boolean, default=False)

class User(BaseClass, Base):
    __tablename__ = "users"
    __repr_fields__ = [
        'uid',
        'uname',
        'listening',
        'admin',
        'last_time_cued',
        'selected'
    ]

    uid = Column(Integer, primary_key=True)
    admin = Column(Boolean)
    uname = Column(String, unique=True)
    pword = deferred(Column(String(132)))
    listening = Column(Boolean, default=True)
    selected = Column(Boolean, default=False)
    last_time_cued = Column(DateTime, index=True)
    rating_data = relationship("UserFileInfo", backref="user")
    preload = relationship("Preload", backref="user",
                           primaryjoin="User.uid == Preload.uid")


class UserFileInfo(BaseClass, Base):
    __tablename__ = "user_file_info"
    __table_args__ = (
        UniqueConstraint('fid', 'uid', name='uniq_idx_fid_uid'),
    )
    __repr_fields__ = [
        'ufid',
        'uid',
        'fid',
        'user.uname',
        'rating',
        'skip_score',
        'true_score',
        'percent_played',
        'ultp'
    ]
    ufid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey('users.uid'))
    fid = Column(Integer, ForeignKey('files_info.fid'))
    rating = Column(Integer(2), index=True, default=DEFAULT_RATING)
    skip_score = Column(Integer(2), index=True, default=DEFAULT_SKIP_SCORE)
    percent_played = Column(Float, index=True, default=DEFAULT_PERCENT_PLAYED)
    true_score = Column(Float, index=True, default=DEFAULT_TRUE_SCORE)
    ultp = Column(DateTime(timezone=True))
    history = relationship("UserHistory", backref="user_file_info",
                           order_by=UserHistory.time_played.desc)

    """
    listening_history = relationship("UserHistory", 
                                     order_by=UserHistory.time_played.desc,
                                     primaryjoin="and_(UserHistory.fid == UserFileInfo.fid, "
                                                 "User.listening == True, "
                                                 "User.uid == UserHistory.uid)")
    
    history = relationship("UserHistory",
                           backref="file",
                           primaryjoin="and_(UserHistory.fid == FileInfo.fid, "
                                             "User.listening == True, "
                                             "User.uid == UserHistory.uid)")"""

    def mark_as_played(self, when=None, percent_played=0, session=None):
        self.ultp = self.now_if_none(when)
        self.percent_played = percent_played
        self.calculate_true_score(session=session)
        self.update_history(session=session)
        self.save(session=session)
        # session.add(self)

    def update_history(self, session=None):
        found = False
        today = self.ultp.date()
        current_history = None
        for h in self.history:
            if h.date_played == today:
                current_history = h
                break
        if current_history is None:
            current_history = UserHistory(uid=self.uid, fid=self.fid)
            self.history.append(current_history)

        current_history.rating = self.rating
        current_history.skip_score = self.skip_score
        current_history.percent_played = self.percent_played
        current_history.true_score = self.true_score
        current_history.date_played = self.ultp.date()
        current_history.time_played = self.ultp
        self.save(session=session)

    def calculate_true_score(self, session=None):
        session.add(self)
        recent = self.history[0:5]
        
        if not recent:
            avg = DEFAULT_PERCENT_PLAYED
        else:
            total = 0
            for h in recent:
                total += h.percent_played
            avg = total / len(recent)

        self.true_score = ((self.rating * 2 * 10.0) +
                           (self.skip_score * 10.0) +
                           (self.percent_played) +
                           avg
                          ) / 4

    def rate(self, rating, session=None):
        log.info("UserFileInfo.RATE:%s", rating)
        if rating is None:
            return
        rating = int(rating)
        if rating < 0 or rating > 5 or rating == self.rating:
            return
        self.rating = rating
        self.save(session=session)

    def inc_skip_score(self, session=None):
        skip_score = self.skip_score
        skip_score += 1
        self.set_skip_score(skip_score, session=session)

    def deinc_skip_score(self, session=None):
        skip_score = self.skip_score
        skip_score -= 1
        self.set_skip_score(skip_score, session=session)

    def set_skip_score(self, skip_score, session=None):
        skip_score = int(skip_score)
        if skip_score > 10 or skip_score < 1:
            return

        self.skip_score = skip_score
        self.save(session=session)

    def pre_save(self, session=None):
        self.calculate_true_score(session=session)

def scan(folder, session=None):
    skip_dirs = [
        '/minecraft/',
        '/.minecraft/',
        '/resourcepacks/',
        '.local/share/Trash/',
        '/resources/',
        '/assets/'
    ]
    dirs_to_scan = []
    for dirname, dirs, files in os.walk(folder):
        dirs_to_scan.append(dirname)

    sorted_dirs = sorted(dirs_to_scan, key=str.lower)

    for dirname in sorted_dirs:
        dirname = os.path.realpath(os.path.expanduser(dirname))
        skip = False
        for d in skip_dirs:
            if d in dirname:
                skip = True
                break
        if skip:
            log.info("Skipping:%s", dirname)
            continue
        
        try:
            folder_info = session.query(Folder)\
                                 .filter(Folder.dirname == dirname)\
                                 .limit(1)\
                                 .one()
        except NoResultFound:
            folder_info = Folder(dirname=dirname)
            
        has_media = folder_info.has_media
        if has_media and folder_info.needs_scan:
            log.info("Scanning:%s", dirname)
            folder_info.save()
        elif not has_media:
            log.info("No Media:%s", dirname)
        else:
            log.info("Already Scanned:%s", dirname)

def create_user(uname, admin=False, listening=True):
    
    try:
        user = session.query(User).filter(User.uname==uname).limit(1).one()
        log.info("User:%s already exists", user.uname)
        
        return
    except NoResultFound:
        pass

    user = User(uname=uname, admin=admin, listening=listening)
    user.save()
    log.info("Created user:%s", user)

AUDIO_EXT = ('.mp3', '.ogg', '.wma', '.wmv')
VIDEO_EXT = ('.flv', '.mpg' ,'.mpeg', '.avi', '.mov', '.mp4', '.m4a')

AUDIO_MIMES = {
    '.m4a': 'audio/mp4a-latm',
    '.mp3': "audio/mpeg",
    '.ogg': "audio/ogg",
    '.wma': "audio/x-ms-wma",
    '.wmv': "audio/x-ms-wmv",
}

VIDEO_MIMES = {
    '.avi': "video/avi",
    '.flv': "video/x-flv",
    '.mov': "video/quicktime",
    '.mp4': "video/mpeg",
    '.mpg': "video/mpeg",
    '.mpeg': "video/mpeg",
}

MIME_TYPES = {}
MIME_TYPES.update(AUDIO_MIMES)
MIME_TYPES.update(VIDEO_MIMES)


# session = make_session(Base)

def wait():
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"

def simple_rate(fid, uid, rating):
    
    user_file_info = session.query(UserFileInfo)\
                            .filter(and_(
                                UserFileInfo.fid == fid,
                                UserFileInfo.uid == uid,
                             ))\
                            .limit(1)\
                            .one()
    
    user_file_info.rate(rating)
    user_file_info.save()

if __name__ == "__main__":
    create_user("erm", True, True)
    create_user("steph", True, False)
    create_user("sam", True, False)
    create_user("halle", True, False)
    users = session.query(User).all()

    # f = session.query(File).order_by(FileInfo.ltp.asc(),func.random()).limit(1).one()
    # print "F:",f 
    # sys.exit()
    scan("/home/erm/Amazon MP3")
    scan("/home/erm/dwhelper")
    scan("/home/erm/halle")
    scan("/home/erm/mp3")
    scan("/home/erm/ogg")
    scan("/home/erm/sam")
    scan("/home/erm/steph")
    scan("/home/erm/stereofame")
    scan("/home/erm/Videos")
