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

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy import Column, Integer, String, DateTime, Text, Float,\
                       UniqueConstraint, Boolean, Table, ForeignKey, Date, \
                       Unicode, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3, HeaderNotFoundError


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
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('gid', Integer, ForeignKey('genres.gid'))
)

file_artists_association_table = Table('file_artists', Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('aid', Integer, ForeignKey('artists.aid'))
)

file_titles_association_table = Table('file_titles', Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('tid', Integer, ForeignKey('titles.tid'))
)

file_albums_association_table = Table('file_albums', Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('alid', Integer, ForeignKey('albums.alid'))
)

file_keywords_association_table = Table("file_keywords", Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('kid', Integer, ForeignKey('keywords.kid'))
)

class BaseClass(object):

    def pre_save(self):
        return

    def post_save(self):
        return

    def save(self):
        start_save = datetime.datetime.now()
        self.pre_save()
        session.add(self)
        try:
            session.commit()
            self.post_save()
        except IntegrityError:
            session.rollback()
            print "ROLLBACK"

        delta = datetime.datetime.now() - start_save
        print self.__class__.__name__,"save time:",delta.total_seconds()
        

    def getattr(self, obj, name, default=None):
        if '.' in name:
            name, rest = name.split('.', 1)
            obj = getattr(obj, name)
            if obj:
                return self.getattr(obj, rest, default=default)
            return None
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


class File(BaseClass, Base):
    __tablename__  = 'files'
    __table_args__ = (
        UniqueConstraint('dirname', 'basename', name='uniq_idx_dirname_basename'),
    )

    __repr_fields__ = [
        'fid',
        'dirname',
        'basename',
        'mtime',
        'sha512',
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
    dirname = Column(Unicode, index=True)
    basename = Column(Unicode, index=True)
    ltp = Column(DateTime(timezone=True), nullable=True, index=True)
    mtime = Column(DateTime(timezone=True), nullable=True, index=True)
    sha512 = Column(String(132), index=True)
    
    file_exists = Column(Boolean, default=False)
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
                           primaryjoin="and_(UserHistory.fid == File.fid, "
                                             "User.listening == True, "
                                             "User.uid == UserHistory.uid)")

    listeners_ratings = relationship("UserFileInfo",
        primaryjoin="and_(UserFileInfo.fid == File.fid, "
                         "User.listening == True, "
                         "User.uid == UserFileInfo.uid)")

    keywords = relationship("Keywords",
                            secondary=file_keywords_association_table,
                            backref="files")


    dontpick = relationship("DontPick", backref="file")
    preload = relationship("Preload", backref="file")

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
    def base(self):
        base, ext = os.path.splitext(self.basename)
        return base

    @property
    def exists(self):
        return os.path.exists(self.filename)

    def pre_save(self):
        if self.has_changed:
            self.update_id3_info()
            self.update_hash()
            self.update_mtime()

        self.set_db_keywords()
        self.add_user_file_info_for_all_listeners()
        self.file_exists = self.exists

    def mark_as_played(self, when=None, percent_played=0):
        print "TODO:mark as played"
        # Step 1 mark file as played
        self.ltp = self.now_if_none(when)
        self.mark_artists_as_played()
        self.mark_listeners_as_played(when, percent_played)
        self.save()

    def mark_listeners_as_played(self, when=None, percent_played=0):
        when = self.now_if_none(when)
        self.add_user_file_info_for_all_listeners()
        for user_rating in self.listeners_ratings:
            user_rating.mark_as_played(when=when, percent_played=percent_played)

    def mark_artists_as_played(self, when=None):
        when = self.now_if_none(when)
        for a in self.artists:
            a.mark_as_played(when)

    def rate(self, uid=None, rating=None):
        if uid is None:
            return
        for l in self.listeners_ratings:
            if l.uid == uid:
                l.rating = uid
                l.save()

    def scan(self, filename=None, dirname=None, basename=None):
        if dirname is not None and basename is not None:
            dirname = self.utf8(dirname)
            basename = self.utf8(basename)
            filename = os.path.join(dirname, basename)

        filename = self.utf8(os.path.realpath(os.path.expanduser(filename)))
        self.dirname, self.basename = os.path.split(filename)
        self.save()

    @property
    def has_changed(self):
        try:
            return not (self.mtime == self.get_mtime() and self.sha512)
        except TypeError:
            utc=pytz.UTC
            try:
                self.mtime = utc.localize(self.mtime)
            except ValueError:
                pass
            try:
                mtime = utc.localize(self.get_mtime())
            except ValueError:
                pass
            return not (self.mtime == mtime and self.sha512)
        return True

    def update_id3_info(self):
        if self.ext != '.mp3':
            self.set_artist_title_from_base()
            return
        self.set_id3_info()

    def set_id3_info(self):
        try:
            audio = MP3(self.filename, ID3=EasyID3)
        except HeaderNotFoundError:
            self.set_artist_title_from_base()
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

                    obj = self.insert_or_get(get_type, value)
                    current_values = getattr(self, attr)
                    # print "current_values file_info.%s:" % attr,current_values
                    if obj not in current_values:
                        current_values.append(obj)
                        setattr(self, attr, current_values)

    def add_artists(self, artist_string=""):
        artists = self.parse_artist_string(artist_string)
        if not artists:
            return
        
        for artist in artists:
            obj = self.insert_or_get(Artist, artist)
            if obj not in self.artists:
                self.artists.append(obj)

    def set_artist_title_from_base(self):
        base = self.base.replace('_', ' ').strip()
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
            obj = self.insert_or_get(Title, title)
            if obj not in self.titles:
                self.titles.append(obj)
        return

    def insert_or_get(self, get_type, name):
        try:
            return session.query(get_type).filter(get_type.name==name).limit(1).one()
        except NoResultFound:
            pass
        info = get_type(name=name)
        session.add(info)
        return info

    def update_mtime(self):
        utc = pytz.UTC
        self.mtime = utc.localize(self.get_mtime())

    def get_mtime(self):
        return datetime.datetime.fromtimestamp(os.stat(self.filename).st_mtime)

    @property
    def size(self):
        return os.path.getsize(self.filename)

    def update_hash(self):
        if not self.has_changed:
            return
        print "calculating hash:", self.filename,
        delta = datetime.timedelta(0,1)
        show_update = datetime.datetime.now() + delta
        fp = open(self.filename, 'r')
        m = hashlib.sha512()
        size = float(self.size)
        data = fp.read(1024)
        m.update(data)
        while data:
            data = fp.read(10240)
            m.update(data)
            if datetime.datetime.now() > show_update:
                percent = fp.tell() / size * 100
                show_update = datetime.datetime.now() + delta
                print "\rcalculating hash:", self.filename, "%0.2f%%" % (percent,),
                sys.stdout.flush()

        print "\rcalculating hash:", self.filename, "100%    "
        self.sha512 = m.hexdigest()
        # print "self.sha512:", self.sha512

    def add_user_file_info_for_all_listeners(self):
        listeners = session.query(User).filter(User.listening==True).all()
        for user in listeners:
            self.add_user_file_info(user)

    def add_user_file_info(self, user):
        try:
            ufinfo = session.query(UserFileInfo).filter(and_(
                UserFileInfo.uid == user.uid,
                UserFileInfo.fid == self.fid
            )).one()
            return
        except NoResultFound:
            pass

        ufinfo = UserFileInfo(uid=user.uid, fid=self.fid)
        session.add(ufinfo)

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
                        print "UnicodeEncodeError parts:",err
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

    def set_db_keywords(self):
        keywords = []
        # print "filename:", os.path.join(self.dirname, self.basename)
        root, ext = os.path.splitext(self.basename)
        if self.sha512:
            keywords += [self.sha512]
        keywords += self.get_words_from_string(self.basename)
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
            keywords[i] = k.strip()
        keywords = list(set(keywords))

        txt = " ".join(keywords) 
        keywords = list(set(txt.split()))
        if keywords.count("-"):
            keywords.remove("-")
        new_keywords = sorted(keywords, key=unicode.lower)
        # txt = " ".join(keywords)

        for kw in self.keywords:
            if kw.word not in new_keywords:
                session.delete(kw)

        for nkw in new_keywords:
            found = False
            for kw in self.keywords:
                if nkw == kw:
                    found = True
                    break
            if found:
                continue

            word = self.find_or_insert_keyword(nkw)
            self.keywords.append(word)

    def find_or_insert_keyword(self, word):
        try:
            word = session.query(Keywords).filter(Keywords.word == word).one()
            return word
        except NoResultFound:
            pass
        word = Keywords(word=word)
        word.save()
        return word
    """
    duplicates = relationship("File",
        primaryjoin="and_(File.sha512 == File.sha512, "
                         "File.fid != File.fid, "
                         "File.sha512 != None)",
        foreign_keys=sha512,
        remote_side=fid)
    """
    @property
    def duplicates(self):
        return session.query(File).filter(and_(File.sha512 == self.sha512,
                                               File.fid != self.fid, 
                                               File.sha512 != None)).all()

class Folders(BaseClass, Base):
    __tablename__ = 'folders'
    foid = Column(Integer, primary_key=True)
    dirname = Column(Text, index=True)
    mtime = Column(DateTime(timezone=True))
    last_scan = Column(DateTime(timezone=True))
    __repr_fields__ = [
        "foid",
        "dirname"
    ]


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


class DontPick(BaseClass, Base):
    __tablename__ = 'dont_pick'
    dpfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files.fid'))
    reason = Column(String, default="No reason")
    __repr_fields__ = [
        'dpfid',
        'fid',
        'file.basename',
        "reason"
    ]


class Preload(BaseClass, Base):
    __tablename__ = "preload"
    prfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files.fid'))
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


class UserHistory(BaseClass, Base):
    __tablename__ = 'user_history'
    __table_args__ = {
        'uniq_idx_uid_fid_date_played': UniqueConstraint('uid', 'fid', 'date_played')
    }
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
        'date_played'
    ]
    uhid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey("users.uid"))
    ufid = Column(Integer, ForeignKey("user_file_info.ufid"))
    fid = Column(Integer, ForeignKey("files.fid"))
    # eid = Column(Integer, ForeignKey("episodes.eid"))
    rating = Column(Integer)
    skip_score = Column(Integer)
    percent_played = Column(Float)
    true_score = Column(Float)
    time_played = Column(DateTime(timezone=True))
    date_played = Column(Date)


class UserFileInfo(BaseClass, Base):
    __tablename__ = "user_file_info"
    __table_args__ = (
        UniqueConstraint('fid', 'uid', name='uniq_idx_fid_uid'),
    )
    __repr_fields__ = [
        'ufid', 
        'user.uname',
        'file.dirname',
        'file.basename',
        'rating',
        'skip_score',
        'true_score',
        'percent_played',
        'ultp'
    ]
    ufid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey('users.uid'))
    fid = Column(Integer, ForeignKey('files.fid'))
    rating = Column(Integer(2), index=True, default=DEFAULT_RATING)
    skip_score = Column(Integer(2), index=True, default=DEFAULT_SKIP_SCORE)
    percent_played = Column(Float, index=True, default=DEFAULT_PERCENT_PLAYED)
    true_score = Column(Float, index=True, default=DEFAULT_TRUE_SCORE)
    ultp = Column(DateTime(timezone=True))
    history = relationship("UserHistory", backref="user_file_info",
                           order_by=UserHistory.time_played.desc)

    def mark_as_played(self, when=None, percent_played=0):
        self.utlp = self.now_if_none(when)
        self.percent_played = percent_played
        self.calculate_true_score()
        self.update_history()

    def update_history(self):
        found = False
        today = self.ultp.date()
        current_history = None
        for h in self.history:
            if h.date_played == today:
                current_history = h
                break
        if current_history is None:
            current_history = UserHistory(uid=self.uid, fid=self.fid)
            session.add(current_history)
            self.history.add(current_history)

        current_history.rating = self.rating
        current_history.skip_score = self.skip_score
        current_history.percent_played = self.percent_played
        current_history.true_score = self.true_score
        current_history.date_played = self.ultp.date()
        current_history.time_played = self.ultp

    def calculate_true_score(self):
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

    def rate(self, rating):
        self.rating = int(rating)
        self.calculate_true_score()
        self.save()

    def inc_skip_score(self):
        skip_score = self.skip_score()
        self.set_skip_score(skip_score)

    def deinc_skip_score(self):
        skip_score = self.skip_score()
        self.set_skip_score(skip_score)

    def set_skip_score(self, skip_score):
        skip_score = int(skip_score)
        if skip_score > 10 or skip_score < 0:
            return

        self.skip_score = skip_score
        self.calculate_true_score()
        self.save()

def insert_file_into_db(dirname, basename):
    base, ext = os.path.splitext(basename)
    ext = ext.lower()
    if ext not in AUDIO_EXT and ext not in VIDEO_EXT:
        return
    start_time = datetime.datetime.now()
    print "="*80
    # unicode(p, "utf8",errors='replace')
    dirname = dirname.decode('utf-8', errors='replace')
    basename = basename.decode('utf-8', errors='replace')
    file_info = False
    try:
        file_info = session.query(File).filter(
            and_(File.dirname==dirname,
                 File.basename==basename)).one()
        if not file_info.has_changed:
            print "Not changed:", file_info.filename
            if file_info.duplicates:
                print "duplicates for:", file_info.filename
                print file_info.duplicates
            # file_info.save()
            return
    except NoResultFound:
        pass

    if not file_info:
        file_info = File(dirname=dirname, basename=basename)
        file_info.scan(dirname=dirname, basename=basename)
    file_info.save()
    
    
    print "processed:",file_info
    end_time = datetime.datetime.now()
    delta = end_time - start_time
    print delta.total_seconds()
    if delta.total_seconds() > 1:
        session.commit()

def scan(folder):
    skip_dirs = [
        '/minecraft/',
        '/.minecraft/',
        '/resourcepacks/',
        '.local/share/Trash/',
        '/resources/',
    ]
    sorted_files = []
    for dirname, dirs, files in os.walk(folder):
        skip = False
        for d in skip_dirs:
            if d in dirname:
                skip = True
                break
        if skip:
            continue
        files.sort()
        clear = "%s[K" % chr(27)
        print "\rscanning:", dirname,clear,
        sys.stdout.flush()
        for basename in files:
            # insert_file_into_db(dirname, basename)
            sorted_files.append((dirname,basename))

    print "\n"
    sorted_files.sort()
    for dirname, basename in sorted_files:
        insert_file_into_db(dirname, basename)
        session.commit()


def create_user(uname, admin=False, listening=True):
    user = User(uname=uname, admin=admin)
    session.add(user)
    try:
        session.commit()
    except IntegrityError:
        session.rollback()
    user.listening = listening

    print "created:", user

AUDIO_EXT = ('.mp3', '.ogg', '.wma', '.wmv')
VIDEO_EXT = ('.flv', '.mpg' ,'.mpeg', '.avi', '.mov', '.mp4', '.m4a')

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from  sqlalchemy.sql.expression import func
    """
    engine = create_engine(
                "postgresql+pg8000://scott:tiger@localhost/test",
                isolation_level="READ UNCOMMITTED"
            )

    """
    CONFIG_PATH = os.path.expanduser("~/.fmp/")
    print "CONFIG_PATH:{CONFIG_PATH}".format(**{
        "CONFIG_PATH": CONFIG_PATH
    })
    
    if not os.path.exists(CONFIG_PATH):
        os.path.mkdirs(CONFIG_PATH)

    db_connection_string = 'sqlite:///{CONFIG_PATH}files.sqlite.db'.format(**{
        "CONFIG_PATH": CONFIG_PATH
    })

    force_pg = True
    
    if "--pgsql" in sys.argv or force_pg:
        CONNECTION_FILE = os.path.join(CONFIG_PATH,"db-connection-string")
        if os.path.exists(CONNECTION_FILE):
            fp = open(CONNECTION_FILE, 'r')
            db_connection_string = fp.read().strip()
            fp.close()

    # fmp_sqlalchemy_test
    engine = create_engine(db_connection_string, echo=False, encoding='utf-8',
                           convert_unicode=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    create_user("erm", True, True)
    create_user("steph", True, False)
    create_user("sam", True, False)
    create_user("halle", True, False)
    users = session.query(User).all()

    # f = session.query(File).order_by(File.ltp.asc(),func.random()).limit(1).one()
    # print "F:",f 
    # sys.exit()
    scan("/home/erm/Amazon MP3")
    scan("/home/erm/dwhelper")
    scan("/home/erm/halle")
    scan("/home/erm/mp3")
    scan("/home/erm/sam")
    scan("/home/erm/steph")
    scan("/home/erm/stereofame")
