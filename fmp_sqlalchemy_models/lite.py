#!/usr/bin/env python
# fmp_sqlalchemy_models/lite.py -- lite version.
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
import random

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref, deferred
from sqlalchemy import Column, Integer, String, DateTime, Text, Float,\
                       UniqueConstraint, Boolean, Table, ForeignKey, Date, \
                       Unicode, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.exc import NoResultFound
from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from sqlalchemy import exists


DEFAULT_SKIP_SCORE = 5
DEFAULT_PERCENT_PLAYED = 50.0
DEFAULT_TRUE_SCORE = (
                      (DEFAULT_SKIP_SCORE * 10) + 
                      DEFAULT_PERCENT_PLAYED
                     ) / 2

Base = declarative_base()

class BaseClass(object):

    def pre_save(self):
        return

    def post_save(self):
        return

    def save(self):
        self.pre_save()
        session.add(self)
        session.commit()
        self.post_save()

    def getattr(self, obj, name, default=None):
        if '.' in name:
            name, rest = name.split('.', 1)
            obj = getattr(obj, name)
            if obj:
                return self.getattr(obj, rest, default=default)
            return None
        return getattr(obj, name)

    def get_repr(self, obj, fields):
        title = self.__class__.__name__
        values = []
        title_length = len(title) + 2
        padding = " "*title_length
        join_text = "\n%s" % padding

        for field in fields:
            value = self.getattr(obj, field)
            values_string = value.__repr__()
            lines = values_string.split("\n")
            values.append("%s=%s" % (field, lines[0]))
            this_padding = " "*(len(field)+2)
            for l in lines[1:]:
                values.append(this_padding+l)
        
        return "<%s(%s)>" % (title, join_text.join(values))

    def __repr__(self):
        return self.get_repr(self, self.__repr_fields__)


class DontPick(BaseClass, Base):
    __tablename__ = 'dont_pick'
    dpfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files.fid'))
    reason = Column(String, default="No reason")
    __repr_fields__ = [
        'dpfid',
        'fid',
        'file.basename',
        "reason"
    ]

class History(BaseClass, Base):
    __tablename__ = 'history'
    __table_args__ = {
        'uniq_idx_uid_fid_date_played': UniqueConstraint('fid', 'date_played')
    }
    __repr_fields__ = fields = [
        'hid',
        'fid',
        'skip_score',
        'percent_played',
        'true_score',
        'time_played',
        'date_played'
    ]
    hid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey("files.fid"))
    skip_score = Column(Integer)
    percent_played = Column(Float)
    true_score = Column(Float)
    time_played = Column(DateTime(timezone=True))
    date_played = Column(Date)

class File(BaseClass, Base):
    __tablename__  = 'files'
    __table_args__ = (
        UniqueConstraint('dirname', 'basename', name='uniq_idx_dirname_basename'),
    )
    __repr_fields__ = [
        'fid',
        'dirname',
        'basename',
        'ltp',
        'percent_played',
        'true_score',
        'skip_score',
        'history',
        'dontpick'
    ]
    
    fid = Column(Integer, primary_key=True)
    dirname = Column(Unicode, index=True)
    basename = Column(Unicode, index=True)
    ltp = Column(DateTime(timezone=True), nullable=True, index=True)
    percent_played = Column(Float, default=DEFAULT_PERCENT_PLAYED)
    skip_score = Column(Integer, default=DEFAULT_SKIP_SCORE)
    true_score = Column(Float, default=DEFAULT_TRUE_SCORE, index=True)
    history = relationship("History", backref="file", order_by=History.time_played.desc)
    dontpick = relationship("DontPick", backref="file")

    @property
    def ext(self):
        base, ext = os.path.splitext(self.basename)
        return ext.lower()

    @property
    def filename(self):
        return os.path.join(self.dirname, self.basename)

    def mark_as_played(self, percent_played=1, ltp=None):
        if ltp is None:
            self.ltp = datetime.datetime.now()
        else:
            self.ltp = ltp
        self.percent_played = float(percent_played)
        self.calculate_true_score()
        self.update_history(percent_played, self.ltp.date())
        self.save()

    def calculate_true_score(self):
        total = 0
        cnt = 0
        for h in self.history[0:5]:
            total += float(h.percent_played)
            cnt += 1

        if cnt and total:
            self.true_score = ((self.skip_score * 10.0) + 
                              float(self.percent_played) + 
                              (total / cnt)) / 3
        else:
            self.true_score = ((self.skip_score * 10.0) + 
                              float(self.percent_played)) / 2


    def update_history(self, percent_played=1, today=None):
        if today is None:
            today = datetime.date.today()
        try:
            history = session.query(History)\
                             .filter(History.fid == self.fid)\
                             .filter(History.date_played == today)\
                             .limit(1)\
                             .one()
        except NoResultFound:
            history = History(fid=self.fid)

        history.percent_played = float(percent_played)
        history.date_played = today
        history.time_played = self.ltp
        history.true_score = self.true_score
        history.skip_score = self.skip_score
        history.true_score = self.true_score
        session.add(history)

    def inc_score(self):
        self.skip_score += 1
        if self.skip_score > 10:
            self.skip_score = 10
            self.calculate_true_score()

    def deinc_score(self):
        self.skip_score -= 1
        if self.skip_score < 1:
            self.skip_score = 1
            self.calculate_true_score()

    def save(self):
        session.add(self)
        session.commit()
        print "save"

def insert_file_into_db(dirname, basename):

    base, ext = os.path.splitext(basename)
    ext = ext.lower()
    if ext not in AUDIO_EXT and ext not in VIDEO_EXT:
        return
    start_time = datetime.datetime.now()
    print "="*80
    dirname = dirname.decode('utf-8')
    basename = basename.decode('utf-8')
    file_info = False
    try:
        file_info = session.query(File).filter(
            and_(File.dirname==dirname,
                 File.basename==basename)).one()
        print "present:", file_info.filename
        return
    except NoResultFound:
        pass

    if not file_info:
        file_info = File(dirname=dirname, basename=basename)
        session.add(file_info)
    #try:
    #    session.commit()
    #except IntegrityError:
    #    session.rollback()
    #    print "ROLLBACK"
    print "processed:",file_info.filename
    end_time = datetime.datetime.now()
    delta = end_time - start_time
    print delta.total_seconds()

def scan(folder):
    cnt = 0
    for dirname, dirs, files in os.walk(folder):
        # print "dirname:", dirname
        # print "dirs:", dirs
        # print "files:", files
        for basename in files:
            if '/resources/' in dirname or '.minecraft' in dirname or \
               '.local/share/Trash/' in dirname:
                continue
            insert_file_into_db(dirname, basename)
            cnt += 1
            if cnt % 1000 == 0:
                session.commit()
    session.commit()

AUDIO_EXT = ('.mp3', '.ogg', '.wma', '.wmv')
VIDEO_EXT = ('.flv', '.mpg' ,'.mpeg', '.avi', '.mov', '.mp4', '.m4a')

if __name__ == "__main__":
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.sql.expression import func
    engine = create_engine('sqlite:///files-lite.sqlite.db', echo=False, encoding='utf-8',
                           convert_unicode=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()

    add = False

    if add == True:
        scan("/home/erm/Amazon MP3")
        scan("/home/erm/dwhelper")
        scan("/home/erm/halle")
        scan("/home/erm/mp3")
        scan("/home/erm/sam")
        scan("/home/erm/steph")
        scan("/home/erm/stereofame")
    

    percents = []
    for percentile in range(0, 10):
        percent = percentile * 10
        for i in range(0, percentile):
            percents.append(percent)
        percents.append(percent)

    print percents
    random.shuffle(percents)
    total_files = session.query(File).count()
    ten_percent = int(total_files * 0.01)
    #if ten_percent > 400:
    #    ten_percent = 300

    the_time = datetime.datetime.now()
    try:
        most_recent = session.query(File)\
                             .filter(File.ltp != None)\
                             .order_by(File.ltp.desc())\
                             .limit(1)\
                             .one()
        the_time = most_recent.ltp
    except NoResultFound:
        pass
        

    delta = datetime.timedelta(minutes=10)
    while True:
        print "*"*100
        not_in = []

        ids_to_check = []
        for dp in session.query(DontPick):
            ids_to_check.append(dp.fid)
            session.delete(dp) 
        session.commit()
        """
        for fid in ids_to_check:
            print "STILL THERE:", session.query(File)\
                                         .filter(File.fid == fid)\
                                         .limit(1)\
                                         .one()
        """
        recently_played = session.query(File)\
                                 .filter(File.ltp != None)\
                                 .order_by(File.ltp.desc())\
                                 .limit(ten_percent)

        for f in recently_played:
            dp = DontPick(fid=f.fid, reason="recently played")
            session.add(dp)

        session.commit()

        for percent in percents:
            try:
                # session.query(Artist).filter(Artist.tracks == None).delete(synchronize_session=False)

                print "percent:",percent
                file_info = session.query(File)\
                                   .filter(File.dontpick == None)\
                                   .filter(File.true_score >= percent) \
                                   .order_by(File.ltp.asc(), func.random()) \
                                   .limit(1)\
                                   .one()
                print "SELECTED:", file_info
                print "x"*10
                percent_played = random.randint(1, 200)
                # print "percent_played:",percent_played
                if percent_played >= 100:
                    percent_played = 100
                    file_info.inc_score()
                else:
                    file_info.deinc_score()
                # print "percent_played:",percent_played
                the_time = the_time + delta
                file_info.mark_as_played(percent_played, ltp=the_time)
                print "the_time:%s" % the_time
                dp = DontPick(fid=file_info.fid, reason="Added")
                session.add(dp)
                session.commit()
                print "AFTER:",file_info
                # time.sleep(1)
            except NoResultFound:
                continue
    
