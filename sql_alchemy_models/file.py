
from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
import os

from fmp_base import Base
from math import floor
import mutagen
import re
import sys
from pprint import pprint, pformat

import hashlib
BLOCKSIZE = 65536

AUDIO_EXT_WITH_TAGS = ['.mp3','.ogg','.wma','.flac', '.m4a']
AUDIO_EXT_WITHOUT_TAGS = ['.wav']
AUDIO_EXT = AUDIO_EXT_WITHOUT_TAGS + AUDIO_EXT_WITH_TAGS

VIDEO_EXT = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv',
             '.mp4', '.mov', '.m4v']

VALID_EXT = AUDIO_EXT + VIDEO_EXT

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

class Title(Base):
    __tablename__ = 'titles'

    id = Column(Integer, primary_key=True)
    name = Column(String)

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    name = Column(String)

class Genre(Base):
    __tablename__ = 'genres'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=True)
    enabled = Column(Boolean, default=True)

class Album(Base):
    __tablename__ = 'albums'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=True)

class File(Base):
    __tablename__ = 'files'

    id = Column(Integer, primary_key=True)
    time_played = Column(BigInteger)
    fingerprint = Column(String)

    artists = relationship("Artist", secondary=artist_association_table,
                           backref="files")
    titles = relationship("Title", secondary=title_assocation_table,
                          backref="files")
    genres = relationship("Genre", secondary=genre_association_table,
                           backref="files")
    albums = relationship("Album", secondary=album_association_table,
                           backref="files")

    keywords = relationship("Keyword", secondary=keywords_assocation_table,
                            backref="files")

    user_file_info = relationship("UserFileInfo", backref="file")

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

    def mark_as_played(self, percent=None):
        self.time_played = time.time()


    def __repr__(self):
           return ("<File(id=%r,\n"
                   "      fingerprint=%r\n"
                   "      filename=%r)>" % (
                    self.id,
                    self.fingerprint,
                    self.filename))

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
        self.tags_easy = None
        self.tags_hard = None
        self.tags_combined = {}
        if not self.exists:
            print ("missing:", self.filename)
            return

        if not self.changed:
            print ("not changed:", self.filename)
            return

        self.tags_combined = {
            'artist': [],
            'title': [],
            'genre': [],
            'album': [],
            'year': [],
            'track': [],
            'keywords': []
        }
        try:
            tags_easy = mutagen.File(self.filename, easy=True)
            self.combine_tags(tags_easy)
        except mutagen.mp3.HeaderNotFoundError:
            pass
        except mutagen.mp4.MP4StreamInfoError:
            pass

        try:
            tags_hard = mutagen.File(self.filename)
            self.combine_tags(tags_hard)
        except mutagen.mp3.HeaderNotFoundError:
            pass
        except mutagen.mp4.MP4StreamInfoError:
            pass


        self.update_fingerprint()

        if not self.file:
            self.file = session.query(File).filter_by(
                fingerprint=self.fingerprint).first()
            if not self.file:
                self.file = File()

        self.file.fingerprint = self.fingerprint
        session.add(self.file)
        session.add(self)
        session.commit()
        self.set_file_assocations()
        self.update_stats()


    def update_stats(self):
        self.mtime = self.actual_mtime
        self.size = self.actual_size
        self.file_exists = self.exists
        session.add(self)
        session.commit()

    def set_file_assocations(self):
        # self.add_keyword(self.basename)
        base, ext = os.path.splitext(self.basename)
        artist_from_filename = ""
        try:
            artist_from_filename, title_from_filename = base.split("-", 1)
        except:
            title_from_filename = base
        artist_from_filename = artist_from_filename.strip()
        title_from_filename = title_from_filename.strip()

        if artist_from_filename:
            self.add_to_combined('artist', artist_from_filename)

        if title_from_filename:
            self.add_to_combined('title', title_from_filename)

        self.add_obj(Artist, 'artist')
        self.add_obj(Title, 'title')

        self.add_obj(Genre, 'genre')
        self.add_obj(Album, 'album')
        self.add_obj(Keyword, 'keywords')

        session.add(self.file)
        session.commit()



    def add_obj(self, cls, tag):
        for text in self.tags_combined.get(tag, []):
            text = text.strip()
            if not text:
                continue
            obj = session.query(cls).filter_by(name=text).first()
            if not obj:
                obj = cls()
            obj.name = text
            session.add(obj)
            session.commit()
            self.add_keyword(text)
            obj.files.append(self.file)
            session.add(obj)
            session.commit()
            print ("*"*100)
            print ("TAG %s:" % tag, text)
            print ("-"*100)



    def combine_tags(self, tags):
        if not tags:
            return
        artist_keys = ('artist', 'author', 'wm/albumartist', 'albumartist',
                       'tpe1', 'tpe2', 'tpe3')
        title_keys = ('title', 'tit2')
        album_keys = ('album', 'wm/albumtitle', 'albumtitle', 'talb')
        year_keys = ('year', 'wm/year', 'date', 'tdrc', 'tdat', 'tory', 'tdor',
                     'tyer')
        genre_keys = ('genre', 'wm/genre', 'wm/providerstyle', 'providerstyle',
                      'tcon')
        track_keys = ('wm/tracknumber', 'track', 'trck')
        for k in tags:
            # print ("k:",k,":",end="")
            try:
                # print(tags[k])
                self.add_to_combined(k, tags[k])
            except KeyError as e:
                print ("KeyError:", e)
                continue
            k_lower = k.lower()
            if k_lower in artist_keys:
                self.add_to_combined('artist', tags[k])
            if k_lower in title_keys:
                self.add_to_combined('title', tags[k])
            if k_lower in album_keys:
                self.add_to_combined('album', tags[k])
            if k_lower in year_keys:
                self.add_to_combined('year', tags[k])
            if k_lower in genre_keys:
                self.add_to_combined('genre', tags[k])
            if k_lower in track_keys:
                self.add_to_combined('track', tags[k])

    def add_keyword(self, value):
        value = "%s" % value
        value = value.lower()
        value = value.strip()
        if not value:
            return
        words = value.split(" ")
        for word in words:
            if not word:
                continue
            if word not in self.tags_combined['keywords']:
                self.tags_combined['keywords'].append(word)

            _word = re.sub("[^A-z0-9]+", "", word)
            if _word and _word != word and \
               _word not in self.tags_combined['keywords']:
                self.tags_combined['keywords'].append(_word)

            _word = re.split("[^A-z0-9]+", word)
            for w in _word:
                if w and w not in self.tags_combined['keywords']:
                    self.tags_combined['keywords'].append(w)


    def add_to_combined(self, tag, value):
        if tag not in self.tags_combined:
            self.tags_combined[tag] = []
        if value not in self.tags_combined[tag]:
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, list):
                        for _v in value:
                            if _v not in self.tags_combined[tag]:
                                vs = "%s" % _v
                                vs = vs.replace("\x00", "")
                                self.tags_combined[tag].append(vs)

                    elif v not in self.tags_combined[tag]:
                        try:
                            vs = "%s" % v
                            vs = vs.replace("\x00", "")
                            self.tags_combined[tag].append(vs)
                        except TypeError:
                            continue
                return
            self.tags_combined[tag].append("%s" % value)

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
        session.add(self)
        session.commit()


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
        session.add(self)
        self.mtime = self.actual_mtime
        session.commit()


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    pword = Column(String)
    admin = Column(Boolean)
    listening = Column(Boolean)
    user_file_info = relationship("UserFileInfo", backref="user")
    history = relationship("UserFileHistory", backref="user")

    def __repr__(self):
       return "<User(name=%r)>" % (
                    self.name)

class UserFileInfo(Base):
    __tablename__ = "user_file_info"

    id = Column(Integer, primary_key=True)

    rating = Column(Integer)
    skip_score = Column(Integer)
    true_score = Column(Float)
    time_played = Column(BigInteger)
    percent_played = Column(Float)

    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    history = relationship("UserFileHistory", backref="user_file_info")

    def __repr__(self):
        return "<UserFileInfo(file_id=%r, user_id=%r)>" % (
                          self.file_id, self.user_id)

class UserFileHistory(Base):
    __tablename__ = "user_file_history"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer)
    skip_score = Column(Integer)
    true_score = Column(Float)
    time_played = Column(BigInteger)
    percent_played = Column(Float)
    reason = Column(String)
    user_id = Column(Integer, ForeignKey('users.id'))
    file_id = Column(Integer, ForeignKey('files.id'))
    user_file_id = Column(Integer, ForeignKey('user_file_info.id'))


if __name__ == "__main__":
    from db_session import engine, session, create_all
    create_all(Base)

    dirs = [
        '/home/erm/disk2/acer-home/Amazon MP3',
        '/home/erm/disk2/acer-home/Amazon-MP3',
        '/home/erm/disk2/acer-home/dwhelper',
        '/home/erm/disk2/acer-home/halle',
        '/home/erm/disk2/acer-home/media',
        '/home/erm/disk2/acer-home/mp3',
        '/home/erm/disk2/acer-home/ogg',
        '/home/erm/disk2/acer-home/sam',
        '/home/erm/disk2/acer-home/steph',
        '/home/erm/disk2/acer-home/stereofame',
        '/home/erm/disk2/syncthing',
    ]
    for d in dirs:
        folder = session.query(Folder).filter_by(dirname=d).first()
        if not folder:
            folder = Folder(dirname=d)

        session.add(folder)
        session.commit()
        folder.scan()
