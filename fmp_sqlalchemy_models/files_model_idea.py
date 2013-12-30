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
import logging
import json

from alchemy_session import make_session, Base

from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy import Column, Integer, String, DateTime, Text, Float,\
                       UniqueConstraint, Boolean, Table, ForeignKey, Date, \
                       Unicode, and_
from sqlalchemy.exc import IntegrityError, InvalidRequestError, InterfaceError,\
                           OperationalError
from sqlalchemy.orm.exc import NoResultFound
from baseclass import BaseClass
from file_info import FileInfo
from file_location import FileLocation
from folder import Folder
from user import User
from user_file_info import UserFileInfo
from user_history import UserHistory

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
hanlder = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hanlder.setFormatter(formatter)
hanlder.setLevel(logging.DEBUG)
log.addHandler(hanlder)

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
            print "SAVING folder_info:",dirname
            folder_info.save(session=session)
        elif not has_media:
            log.info("No Media:%s", dirname)
        else:
            log.info("Already Scanned:%s", dirname)

def create_user(uname, admin=False, listening=True, session=None):
    try:
        user = session.query(User).filter(User.uname==uname).limit(1).one()
        log.info("User:%s already exists", user.uname)
        
        return
    except NoResultFound:
        pass

    user = User(uname=uname, admin=admin, listening=listening)
    user.save(session)
    log.info("Created user:%s", user)

# session = make_session(Base)

def simple_rate(fid, uid, rating, session=None):
    user_file_info = session.query(UserFileInfo)\
                            .filter(and_(
                                UserFileInfo.fid == fid,
                                UserFileInfo.uid == uid,
                             ))\
                            .limit(1)\
                            .one()
    
    user_file_info.rate(rating, session=session)
    # user_file_info.save()

if __name__ == "__main__":
    session = make_session(Base)
    create_user("erm", True, True, session=session)
    create_user("steph", True, False, session=session)
    create_user("sam", True, False, session=session)
    create_user("halle", True, False, session=session)
    users = session.query(User).all()

    # f = session.query(File).order_by(FileInfo.ltp.asc(),func.random()).limit(1).one()
    # print "F:",f 
    # sys.exit()
    scan("/home/erm/Amazon MP3", session=session)
    scan("/home/erm/dwhelper", session=session)
    scan("/home/erm/halle", session=session)
    scan("/home/erm/mp3", session=session)
    scan("/home/erm/ogg", session=session)
    scan("/home/erm/sam", session=session)
    scan("/home/erm/steph", session=session)
    scan("/home/erm/stereofame", session=session)
    scan("/home/erm/Videos", session=session)
