
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date, ForeignKey

import hashlib
BLOCKSIZE = 65536

from .disk_entity import DiskEntitiy

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json


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

