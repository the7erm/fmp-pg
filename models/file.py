
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.db_session import engine, session, create_all, Session
from sqlalchemy import Column, Integer, String, BigInteger,\
                       Float, Boolean

from sqlalchemy.orm import relationship

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from math import floor
import re
from pprint import pprint, pformat
from time import time

from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags
from .utils import do_commit

from .associations import artist_association_table, \
                          title_assocation_table,\
                          genre_association_table, \
                          album_association_table

from .preload import Preload
from .user import User, get_users
from .user_file_info import UserFileInfo
from .artist import Artist
from .title import Title
from .genre import Genre
from .album import Album
from .location import Location

import hashlib
BLOCKSIZE = 65536

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