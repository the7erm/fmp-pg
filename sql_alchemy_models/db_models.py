
import sys
sys.path.append("../")
from fmp_utils.db_session import engine, session, create_all, Session
from fmp_utils.jobs import jobs
from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import not_, and_, text
import os
from random import shuffle
from datetime import date

try:
    from .fmp_base import Base, to_json
except SystemError:
    from fmp_base import Base, to_json

from math import floor
import re
import sys
import urllib
from pprint import pprint, pformat
from time import time


from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags

import hashlib
BLOCKSIZE = 65536

def get_users(user_ids=[]):
    user_query = session.query(User)
    if user_ids:
        user_query = user_query.filter(User.id.in_(user_ids))
    else:
        user_query = user_query.filter(User.listening==True)

    users_query = user_query.order_by(User.name.asc())
    users = user_query.all()

    if not users:
        users = session.query(User)\
                       .order_by(User.name.asc())\
                       .all()
    return users

def do_commit(*objs):
    for obj in objs:
        _session = Session.object_session(obj)
        if _session:
            _session.commit()
        else:
            session.add(obj)
            session.commit()

artist_association_table = Table('artist_association', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('artist_id', Integer, ForeignKey('artists.id'))
)

genre_association_table = Table('genre_association', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('genre_id', Integer, ForeignKey('genres.id'))
)

album_association_table = Table('album_association', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('album_id', Integer, ForeignKey('albums.id'))
)

album_artist_association_table = Table('album_artist_association', Base.metadata,
    Column('artist_id', Integer, ForeignKey('artists.id')),
    Column('album_id', Integer, ForeignKey('albums.id'))
)

title_assocation_table = Table('title_assocation', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('title_id', Integer, ForeignKey('titles.id'))
)

keywords_assocation_table = Table('keyword_assocation', Base.metadata,
    Column('file_id', Integer, ForeignKey('files.id')),
    Column('keyword_id', Integer, ForeignKey('keywords.id'))
)

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean)
    albums = relationship("Album",
                          secondary=album_artist_association_table,
                          backref="artists")

    def json(self):
        return to_json(self, Artist)

class Title(Base):
    __tablename__ = 'titles'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def json(self):
        return to_json(self, Title)

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    name = Column(String)

class Genre(Base):
    __tablename__ = 'genres'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    def json(self):
        return to_json(self, Genre)

class Album(Base):
    __tablename__ = 'albums'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=False)

    def json(self):
        return to_json(self, Album)

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    time_played = Column(BigInteger)
    percent_played = Column(Float)
    fingerprint = Column(String)
    keywords_txt = Column(String)
    reason = Column(String)

    artists = relationship("Artist", secondary=artist_association_table,
                           backref="files",
                           order_by="Artist.name")
    titles = relationship("Title", secondary=title_assocation_table,
                          backref="files",
                          order_by="Title.name")
    genres = relationship("Genre", secondary=genre_association_table,
                           backref="files",
                           order_by="Genre.name")
    albums = relationship("Album", secondary=album_association_table,
                           backref="files",
                           order_by="Album.name")

    keywords = relationship("Keyword", secondary=keywords_assocation_table,
                            backref="files")

    user_file_info = relationship("UserFileInfo", backref="file",
                                  order_by="UserFileInfo.user_id")

    locations = relationship(
        "Location",
         order_by="Location.dirname,Location.basename", backref="file")

    @property
    def filename(self):
        for l in self.locations:
            if l.exists:
                return l.filename
        return None

    @property
    def exists(self):
        for l in self.locations:
            if l.exists:
                return True
        return False

    @property
    def cued(self):
        cued = session.query(Preload)\
                      .filter(Preload.file_id==self.id)\
                      .first()
        if cued:
            cued = cued.json()
        else:
            cued = False

        return cued


    def mark_as_played(self, **kwargs):
        print("File.mark_as_played()")
        percent_played = kwargs.get('percent_played', 0)
        if self.percent_played and int(self.percent_played) == int(percent_played):
            return
        self.time_played = int(kwargs.get('now', time()))
        self.percent_played = percent_played
        do_commit(self)
        self.iterate_user_ids(self.mark_user_as_played, **kwargs)

    def iterate_user_ids(self, cmd, **kwargs):
        if 'user_ids' in kwargs:
            for user_id in kwargs.get('user_ids'):
                cmd(user_id, **kwargs)
            return

        for user in session.query(User).filter(User.listening==True).all():
            kwargs['user'] = user
            cmd(user.id, **kwargs)

        # The goal here is to make it so files are not marked as played
        # when no one is listening, or inc de_inc score.

    def mark_user_as_played(self, user_id, *args, **kwargs):
        self.iterate_ufi('mark_as_played', user_id, *args, **kwargs)

    def create_ufi(self, user_id, **kwargs):
        if 'user' not in kwargs or not kwargs.get('user'):
            kwargs['user'] = session.query(User).filter(id=user_id).first()

        user = kwargs.get('user')
        if not user:
            return None

        ufi = UserFileInfo()
        ufi.file_id = self.id
        ufi.user_id = user.id
        ufi.reason = self.reason
        return ufi

    def inc_score(self, *args, **kwargs):
        self.iterate_user_ids(self.inc_user_score, **kwargs)

    def inc_user_score(self, user_id, *args, **kwargs):
        self.iterate_ufi('inc_score', user_id, *args, **kwargs)

    def deinc_score(self, *args, **kwargs):
        self.iterate_user_ids(self.deinc_user_score, **kwargs)

    def deinc_user_score(self, user_id, *args, **kwargs):
        self.iterate_ufi('deinc_score', user_id, *args, **kwargs)

    def iterate_ufi(self, cmd, user_id, *args, **kwargs):
        for ufi in self.user_file_info:
            if ufi.user.id == user_id:
                ufi.reason = self.reason
                exec_cmd = getattr(ufi, cmd)
                exec_cmd(*args, **kwargs)
                return

        ufi = self.create_ufi(user_id, **kwargs)
        if ufi:
            exec_cmd = getattr(ufi, cmd)
            exec_cmd(*args, **kwargs)

    def __repr__(self):
           return ("<File(id=%r,\n"
                   "      fingerprint=%r\n"
                   "      filename=%r)>" % (
                    self.id,
                    self.fingerprint,
                    self.filename))

    def clear_voted_to_skip(self, user_ids=[]):

        users = get_users(user_ids)

        for user in users:
            for ufi in self.user_file_info:
                if ufi.user_id == user.id and ufi.voted_to_skip:
                    ufi.voted_to_skip = False
                    do_commit(ufi)

    def get_users(self, user_ids=[]):
        return get_users(user_ids)

    def json(self, user_ids=[]):
        json = to_json(self, File)
        json['cued'] = self.cued

        users = get_users(user_ids)

        keys = ['artists', 'titles', 'genres', 'locations']
        for k in keys:
            json[k] = []
            for obj in getattr(self, k):
                json[k].append(obj.json())

        json['user_file_info'] = []
        for user in users:
            found = False
            for ufi in self.user_file_info:
                if ufi.user_id == user.id:
                    json['user_file_info'].append(ufi.json())
                    found = True
                    break
            if found:
                continue
            ufi = self.create_ufi(user.id, user=user)
            do_commit(ufi)
            json['user_file_info'].append(ufi.json())

        return json

class DiskEntitiy(object):
    id = Column(Integer, primary_key=True)
    dirname = Column(String)
    mtime = Column(BigInteger)
    file_exists = Column(Boolean)
    type = Column(String(50))

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def actual_mtime(self):
        mtime = os.path.getmtime(self.filename)
        return floor(mtime)

    @property
    def changed(self):
        return self.mtime != self.actual_mtime

    @property
    def filename(self):
        return self.dirname


class Location(DiskEntitiy, Base):
    __tablename__ = "locations"
    __mapper_args__ = {'concrete':True}

    id = Column(Integer, primary_key=True)
    basename = Column(String)
    size = Column(BigInteger)
    fingerprint = Column(String)

    file_id = Column(Integer, ForeignKey('files.id'))

    @property
    def filename(self):
        return os.path.join(self.dirname, self.basename)

    @property
    def actual_size(self):
        if not self.exists:
            return 0
        return os.path.getsize(self.filename)

    @property
    def changed(self):
        return self.mtime != self.actual_mtime or self.size != self.actual_size

    def scan(self):
        if not self.exists:
            print ("missing:", self.filename)
            return

        if not self.changed:
            print ("not changed:", self.filename)
            return

        self.media_tags = MediaTags(filename=self.filename)
        self.update_fingerprint()

        if not self.file:
            self.file = session.query(File).filter_by(
                fingerprint=self.fingerprint).first()
            if not self.file:
                self.file = File()

        self.file.fingerprint = self.fingerprint
        do_commit(self.file, self)
        self.set_file_assocations()
        self.update_stats()


    def update_stats(self):
        self.mtime = self.actual_mtime
        self.size = self.actual_size
        self.file_exists = self.exists
        do_commit(self)

    def set_file_assocations(self):
        # self.add_keyword(self.basename)

        self.add_obj(Artist, 'artist')
        self.add_obj(Title, 'title')

        self.add_obj(Genre, 'genre')
        self.add_obj(Album, 'album')
        # self.add_obj(Keyword, 'keywords')
        self.file.keywords_txt = " ".join(self.media_tags.tags_combined['keywords'])

        do_commit(self.file)

    def add_obj(self, cls, tag):
        for text in self.media_tags.tags_combined.get(tag, []):
            text = str(text)
            text = text.strip()
            if not text:
                continue
            obj = session.query(cls).filter_by(name=text).first()
            if not obj:
                obj = cls()
            obj.name = text
            do_commit(obj)
            obj.files.append(self.file)
            do_commit(obj)
            print ("*"*100)
            print ("TAG %s:" % tag, text)
            print ("-"*100)

    def update_fingerprint(self):
        hasher = hashlib.sha512()
        filesize = self.actual_size
        with open(self.filename, 'rb') as afile:
            # Get the beginning of the file.
            buf = afile.read(BLOCKSIZE)

            # Get the middle of the file.
            afile.seek(floor(filesize / 2))
            hasher.update(buf)

            seek = filesize - BLOCKSIZE
            if seek > 0:
                # Get the end of the file.
                afile.seek(seek)
                buf = afile.read(BLOCKSIZE)
                hasher.update(buf)



        self.fingerprint = hasher.hexdigest()
        do_commit(self)

    def json(self):
        return to_json(self, Location)


class Folder(DiskEntitiy, Base):
    __tablename__ = "folders"
    __mapper_args__ = {'concrete':True}

    id = Column(Integer, primary_key=True)

    def scan(self):
        if not self.exists:
            print("MISSING:", self.dirname)
            return

        if not self.changed:
            print("NOT CHANGED:", self.dirname)
            return

        print ("scanning:", self.dirname)
        for dirname, dirs, files in os.walk(self.dirname):
            # pprint(files)
            for _dir in dirs:
                d = os.path.realpath(os.path.join(dirname, _dir))
                if not d or d == "/":
                    continue
                folder = session.query(Folder).filter_by(dirname=d).first()
                if not folder:
                    folder = Folder(dirname=d)
                session.add(folder)
                folder.scan()

            for basename in files:
                filename = os.path.realpath(os.path.join(dirname, basename))
                _dirname = os.path.dirname(filename)
                _basename = os.path.basename(filename)
                base, ext = os.path.splitext(_basename)
                ext = ext.lower()
                if ext not in VALID_EXT:
                    continue
                loc = session.query(Location).filter_by(
                    dirname=_dirname,
                    basename=_basename
                ).first()
                if not loc:
                    loc = Location()
                    loc.dirname = _dirname
                    loc.basename = _basename
                loc.scan()
            break
        self.mtime = self.actual_mtime
        do_commit(self)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    pword = Column(String)
    admin = Column(Boolean)
    listening = Column(Boolean)
    user_file_info = relationship("UserFileInfo", backref="user")
    history = relationship("UserFileHistory", backref="user")

    def json(self):
        d = to_json(self, User)
        del d['pword']
        return d

    def __repr__(self):
       return "<User(name=%r)>" % (
                    self.name)

class UserFileInfo(Base):
    __tablename__ = "user_file_info"

    id = Column(Integer, primary_key=True)

    rating = Column(Integer, default=6)
    skip_score = Column(Integer, default=5)
    true_score = Column(Float, default=((6 * 2 * 10) + (5 * 10)) / 2)
    time_played = Column(BigInteger)
    date_played = Column(Date)
    percent_played = Column(Float)
    reason = Column(String)
    voted_to_skip = Column(Boolean)

    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    history = relationship("UserFileHistory", backref="user_file_info")

    def mark_as_played(self, **kwargs):
        print ("UserFileInfo.mark_as_played()")
        self.time_played = int(kwargs.get('now', time()))
        self.percent_played = kwargs.get('percent_played', 0)
        self.date_played = date.fromtimestamp(self.time_played)
        do_commit(self)

        for h in self.history:
            print("H:",h)
            if h.date_played == self.date_played and h.user_id == self.user_id:
                self.update_ufh(h)
                h.mark_as_played(**kwargs)
                return

        ufh = UserFileHistory()
        self.update_ufh(ufh)
        ufh.mark_as_played(**kwargs)
        self.history.append(ufh)

    def update_ufh(self, ufh):
        ufh.user_file_id = self.id
        ufh.user_id = self.user_id
        ufh.file_id = self.file_id
        ufh.rating = self.rating
        ufh.reason = self.reason
        ufh.voted_to_skip = self.voted_to_skip
        ufh.skip_score = self.skip_score
        ufh.true_score = self.true_score

    def inc_score(self, *args, **kwargs):
        if self.skip_score is None:
            self.skip_score = 5

        if self.voted_to_skip:
            # The user voted to skip, but the other users didn't so they
            # were forced to listen to the whole song.
            # We'll take it down by 2 notches for them.
            self.skip_score += -2
        else:
            self.skip_score += 1
        self.calculate_true_score()

    def deinc_score(self, *args, **kwargs):
        if self.skip_score is None:
            self.skip_score = 5
        self.skip_score += -1
        self.calculate_true_score()

    def calculate_true_score(self):
        print("UserFileInfo.calculate_true_score()")
        if self.rating is None:
            self.rating = 6
        if self.skip_score is None:
            self.skip_score = 5

        true_score = (((self.rating * 2 * 10) + (self.skip_score * 10)) / 2)

        if true_score < -20:
            true_score = -20

        if true_score > 125:
            true_score = 125

        self.true_score = true_score

        do_commit(self)

    def __repr__(self):
        return "<UserFileInfo(file_id=%r, user_id=%r)>" % (
                          self.file_id, self.user_id)

    def json(self):
        ufi = to_json(self, UserFileInfo)
        if ufi:
            ufi['user'] = self.user.json()
        return ufi

class UserFileHistory(Base):
    __tablename__ = "user_file_history"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer)
    skip_score = Column(Integer)
    true_score = Column(Float)
    time_played = Column(BigInteger)
    date_played = Column(Date)
    percent_played = Column(Float)
    reason = Column(String)
    voted_to_skip = Column(Boolean)
    user_id = Column(Integer, ForeignKey('users.id'))
    file_id = Column(Integer, ForeignKey('files.id'))
    user_file_id = Column(Integer, ForeignKey('user_file_info.id'))

    def mark_as_played(self, **kwargs):
        print ("UserFileHistory.mark_as_played()")
        self.time_played = int(kwargs.get('now', time()))
        self.percent_played = kwargs.get('percent_played', 0)
        self.date_played = date.fromtimestamp(self.time_played)
        do_commit(self)

class PickFrom(Base):
    __tablename__ = "pick_from"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, index=True)

class Preload(Base):
    __tablename__ = "preload"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    reason = Column(String)
    from_search = Column(Boolean, default=False)

    def json(self):
        return to_json(self, Preload)

if __name__ == "__main__":

    create_all(Base)

    dirs = [
        '/home/erm/disk2/acer-home/Amazon MP3',
        '/home/erm/disk2/acer-home/Amazon-MP3',
        '/home/erm/disk2/acer-home/media',
        '/home/erm/disk2/acer-home/dwhelper',
        '/home/erm/disk2/syncthing',
        '/home/erm/disk2/acer-home/mp3',
        '/home/erm/disk2/acer-home/ogg',
        '/home/erm/disk2/acer-home/steph',
        '/home/erm/disk2/acer-home/stereofame',
        '/home/erm/disk2/acer-home/sam',
        '/home/erm/disk2/acer-home/halle',
    ]
    shuffle(dirs)
    for d in dirs:
        folder = session.query(Folder).filter_by(dirname=d).first()
        if not folder:
            folder = Folder(dirname=d)

        do_commit(folder)
        folder.scan()
