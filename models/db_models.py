
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
