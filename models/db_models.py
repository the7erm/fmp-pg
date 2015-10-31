
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.db_session import engine, session, create_all, Session
from fmp_utils.jobs import jobs
from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date
from sqlalchemy import ForeignKey
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import not_, and_, text

from random import shuffle
from datetime import date

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from math import floor
import re
import urllib
from pprint import pprint, pformat
from time import time

from folder import Folder
from model_utils import do_commit
from math import floor

"""
subscribers_table = Table('subscribers_assocation', Base.metadata,
    Column('netcast_id', Integer, ForeignKey('netcasts.id')),
    Column('users_id', Integer, ForeignKey('users.id'))
)

class Netcast(Base):
    __tablename__ = "netcasts"
    id = Column(Integer, primary_key=True)
    name = Column(String)
    url = Column(String)
    expired = Column(Integer)
    subscribers = relationship("User", secondary=subscribers_assocation,
                               backref="subscriptions",
                               order_by="User.name")

    episodes = relationship("Episodes", backref="netcast")


class Episodes(Base):
    __tablename__ = "episodes"
    id = Column(Integer, primary_key=True)
    netcast_id = Column(Integer, ForeignKey('netcasts.id'))
    name = Column(String)
    url = Column(String)
    cache_filename = Column(String)
    pub_date = Column()
    netcast_id = Column(Integer, ForeignKey('netcasts.id'))
    played_for = relationship("User", secondary=subscribers_assocation,
                              backref="episodes",
                              order_by="Episodes.pub_date DESC")
"""

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
