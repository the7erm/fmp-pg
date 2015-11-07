
import os
import sys
from math import floor
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags
from .utils import do_commit
from fmp_utils.db_session import Session, session_scope

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date, ForeignKey

import hashlib
BLOCKSIZE = 65536

from .disk_entity import DiskEntitiy


try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from .file import File
from .artist import Artist
from .title import Title
from .genre import Genre
from .album import Album


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
        with session_scope() as session:
            session.add(self)
            return os.path.join(self.dirname, self.basename)

    @property
    def actual_size(self):
        if not self.exists:
            return 0
        with session_scope() as session:
            session.add(self)
            return os.path.getsize(self.filename)

    @property
    def changed(self):
        with session_scope() as session:
            session.add(self)
            not_mtime_match = self.mtime != self.actual_mtime
            session.add(self)
            not_size_match = self.size != self.actual_size
            return not_mtime_match or not_size_match

    def scan(self):
        with session_scope() as session:
            session.add(self)
            if not self.exists:
                session.add(self)
                print ("missing:", self.filename)
                return
            session.add(self)
            if not self.changed:
                session.add(self)
                print ("not changed:", self.filename)
                return

            session.add(self)
            self.media_tags = MediaTags(filename=self.filename)
            self.update_fingerprint()
            session.add(self)

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
        with session_scope() as session:
            session.add(self)
            self.mtime = self.actual_mtime
            self.size = self.actual_size
            self.file_exists = self.exists
            session.add(self)
            do_commit(self)

    def set_file_assocations(self):
        # self.add_keyword(self.basename)
        # self.add_obj(Keyword, 'keywords')
        with session_scope() as session:
            session.add(self)
            self.add_obj(Artist, 'artist')
            session.add(self)
            self.add_obj(Title, 'title')
            session.add(self)
            self.add_obj(Genre, 'genre')
            session.add(self)
            self.add_obj(Album, 'album')
            session.add(self)
            self.file.keywords_txt = " ".join(self.media_tags.tags_combined['keywords'])
            session.add(self)
            do_commit(self.file)

    def add_obj(self, cls, tag):
        with session_scope() as session:
            session.add(self)
            for text in self.media_tags.tags_combined.get(tag, []):
                session.add(self)
                text = str(text)
                text = text.strip()
                if not text:
                    continue
                obj = session.query(cls).filter_by(name=text).first()
                if not obj:
                    obj = cls()
                obj.name = text
                do_commit(obj)
                session.add(obj)
                session.add(self)
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

#