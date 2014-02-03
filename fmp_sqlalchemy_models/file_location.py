#!/usr/bin/env python
# fmp_sqlalchemy_models/file_location.py -- Location of file.
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
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

import datetime
import hashlib
import json
import logging
import os
import pytz
import pprint
import re
import sys
import time
import urllib

from alchemy_session import Base
from baseclass import BaseClass, log
from sqlalchemy import Column, Integer, String, DateTime, Float,\
                       UniqueConstraint, ForeignKey, Date, Unicode, Boolean,\
                       and_
from file_info import FileInfo
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

class FileLocation(BaseClass, Base):
    __tablename__  = 'file_location'
    __table_args__ = (
        UniqueConstraint('dirname', 'basename', name='uniq_idx_dirname_basename'),
    )
    __repr_fields__ = [
        'flid',
        'fid',
        'dirname',
        'basename',
        'mtime',
        'ctime',
        'file_exists',
        'size',
        'file'
    ]
    fid = Column(Integer, ForeignKey('files_info.fid'))
    flid = Column(Integer, primary_key=True)
    dirname = Column(Unicode, index=True)
    basename = Column(Unicode, index=True)
    mtime = Column(DateTime(timezone=False), nullable=True, index=True)
    ctime = Column(DateTime(timezone=False), nullable=True, index=True)
    file_exists = Column(Boolean, default=False)
    file_size = Column(Integer, index=True, default=0)

    def __init__(self, *args, **kwargs):
        self.file_stats = None
        Base.__init__(self, *args, **kwargs)

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
    def uri(self):
        filename = self.filename
        if self.exists:
            return "file://%s" % (urllib.quote(filename.encode('utf8')),)
        else:
            return urllib.quote(filename.encode('utf8'))

    @property
    def base(self):
        base, ext = os.path.splitext(self.basename)
        return base

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def has_changed(self):
        mtime = self.get_mtime()
        ctime = self.get_ctime()
        size = self.get_size()
        if self.mtime != mtime:
            log.info("mtime %s != self.mtime %s", mtime, self.mtime)
            
        if self.ctime != ctime:
            log.info("ctime %s != self.ctime %s", ctime, self.ctime)
        if self.file_size != size:
            log.info("size %s != self.size %s", size, self.file_size)
        return (self.mtime != mtime or self.ctime != ctime or self.file_size != size)

    def update_mtime(self):
        self.mtime = self.get_mtime()

    def update_ctime(self):
        self.mtime = self.get_ctime()

    def update_size(self):
        self.size = self.get_size()

    def get_mtime(self):
        self.set_stats()
        return datetime.datetime.fromtimestamp(self.file_stats.st_mtime)

    def get_ctime(self):
        return datetime.datetime.fromtimestamp(self.file_stats.st_ctime)

    def get_size(self):
        self.set_stats()
        return self.file_stats.st_size

    def set_stats(self, force_refresh=False):
        if force_refresh:
            self.file_stats = None

        if not hasattr(self, 'file_stats'):
            self.file_stats = None

        if self.file_stats is not None:
            return
        self.file_stats = os.stat(self.filename)

    def update_stats(self):
        self.set_stats()
        self.mtime = self.get_mtime()
        self.ctime = self.get_ctime()
        self.size = self.get_size()

    def scan(self, filename=None, dirname=None, basename=None, save=True,
             session=None):
        if dirname is not None and basename is not None:
            dirname = self.utf8(dirname)
            basename = self.utf8(basename)
            filename = os.path.join(dirname, basename)

        filename = self.utf8(os.path.realpath(os.path.expanduser(filename)))
        self.dirname, self.basename = os.path.split(filename)
        if save:
            self.save(session=session)

    def pre_save(self, session=None):
        if self.has_changed:
            self.update_hash(session=session)
            self.update_stats()

    def update_hash(self, session=None):
        self.set_stats(True)
        log.info("calculating hash:%s", self.filename)
        delta = datetime.timedelta(0, 1)
        show_update = datetime.datetime.now() + delta
        fp = open(self.filename, 'r')
        m = hashlib.sha512()
        size = self.get_size()
        fingerprint_size = 512 * 1024
        data = fp.read(fingerprint_size)
        m.update(data)
        seek = size / 2
        if seek >= fingerprint_size:
            fp.seek(seek)
            data = fp.read(fingerprint_size)
            m.update(data)

        seek = size - fingerprint_size
        if seek > (size / 2) + fingerprint_size:
            fp.seek(seek)
            data = fp.read(fingerprint_size)
            m.update(data)
        
        fingerprint = m.hexdigest()
        log.info("calculating fingerprint:%s", fingerprint)
        try:
            file_info = session.query(FileInfo).filter(and_(
                FileInfo.fingerprint == fingerprint,
                FileInfo.file_size == size
            ))\
            .limit(1)\
            .one()
        except NoResultFound, e:
            log.info("file info not found:%s", e)
            log.info("ADDING")
            file_info = FileInfo(fingerprint=fingerprint, file_size=size)
            log.info("/ADDING")
            session.add(file_info)
            session.commit()
            print "SAVED"
            file_info.save(session=session)
            print "/SAVED"

        self.fid = file_info.fid
        found = False
        for l in file_info.locations:
            if l.flid == self.flid:
                found = True
                break;

        if not found:
            file_info.locations.append(self)

        if self.has_changed or not found:
            file_info.save(session=session)
