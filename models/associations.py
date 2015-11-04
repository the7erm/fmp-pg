
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

from sqlalchemy import Table, Column, ForeignKey, Integer

try:
    from .base import Base
except SystemError:
    from base import Base

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

folder_assocation_table = Table('folder_assocation', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('folder_id', Integer, ForeignKey('folders.id'))
)

netcast_assocation_table = Table('netcast_association', Base.metadata,
    Column('user_id', Integer, ForeignKey('users.id')),
    Column('rss_id', Integer, ForeignKey('rss.id'))
)
