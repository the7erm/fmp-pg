#!/usr/bin/env python
# fmp_sqlalchemy_models/picker.py -- picks songs.
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
import random
import sys
import datetime
import traceback
from files_model_idea import FileLocation, FileInfo, Artist, DontPick, Genre,\
                             Preload, Title, Album, User, UserHistory, \
                             UserFileInfo, file_genre_association_table, \
                             DEFAULT_RATING, DEFAULT_SKIP_SCORE, \
                             DEFAULT_PERCENT_PLAYED, DEFAULT_TRUE_SCORE, \
                             make_session
from sqlalchemy import and_, distinct, insert
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func, not_
import math
import gtk
import gobject
gtk.gdk.threads_init()
gobject.threads_init()

def wait():
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"

class Picker():
    def __init__(self, session):
        self.session = session
        self.init_percents()
        self.percent_played = -1
        

    def init_percents(self):
        percents = []
        for percentile in range(0, 10):
            percent = percentile * 10
            for i in range(0, percentile):
                percents.append(percent)
            percents.append(percent)
        self.percents = percents

    def clear_dontpick(self):
        self.session.query(DontPick).delete()
        wait()

    def insert_most_recent_into_dontpick(self):
        """
        q = session.query(FileInfo.fid, '\'disable genre - new\'')
                   .distinct(FileInfo.fid)\
                   .join(Genre, FileInfo.genres)
                   .filter(Genre.enabled == False)
        """
        total_files = self.session.query(FileInfo)\
                             .distinct(FileInfo.fid)\
                             .join(Genre, FileInfo.genres)\
                             .filter(Genre.enabled == True)\
                             .count()
        ten_percent = int(total_files * 0.1)
        print "ten_percent:", ten_percent

        """
        INSERT INTO 
        """
        q = self.session.query(UserFileInfo.fid, "'recently played'")\
                   .join(User)\
                   .distinct(UserFileInfo.fid, UserFileInfo.uid, UserFileInfo.ultp)\
                   .filter(and_(
                      UserFileInfo.ultp != None,
                      User.listening == True
                    ))\
                   .order_by(UserFileInfo.ultp.desc())\
                   .limit(ten_percent)
        self.insert_into_dont_pick(q, [DontPick.fid, DontPick.reason, DontPick.junk])
        """
        
        recently_played = session.query(UserFileInfo)\
                                 .join(User)\
                                 .distinct(UserFileInfo.fid, UserFileInfo.uid)\
                                 .filter(and_(
                                    UserFileInfo.ultp != None,
                                    User.listening == True
                                  ))\
                                 .order_by(UserFileInfo.ultp.desc())\
                                 .limit(ten_percent).all()
        
        for f in recently_played:
            print "INSERT INTO DONTPICK", f
            dp = DontPick(fid=f.fid, reason="recently played")
            self.add(dp)
        self.commit()
        """

    def insert_rated_0_into_dontpick(self):
        q = self.session.query(UserFileInfo.fid, '\'rated 0 - new\'', '\'junk\'')\
                   .join(User)\
                   .distinct(UserFileInfo.fid, UserFileInfo.uid)\
                   .filter(and_(UserFileInfo.rating == 0,
                                User.listening == True))
        try:
            self.insert_into_dont_pick(q)
        except:
            pass
        """
        return
        rated_0 = session.query(UserFileInfo)\
                         .join(User)\
                         .distinct(UserFileInfo.fid, UserFileInfo.uid)\
                         .filter(and_(
                                    UserFileInfo.rating == 0,
                                    User.listening == True
                         )).all()
        for f in rated_0:
            print "INSERT INTO DONTPICK 2", f
            dp = DontPick(fid=f.fid, reason="rated 0")
            self.add(dp)
        self.commit()
        """

    def insert_into_dont_pick(self, select=None, names=None):
        if names is None:
            names = (DontPick.fid, DontPick.reason, DontPick.junk)
        print "select:", select
        print "names:", names
        ins = insert(DontPick).from_select(names=names, select=select)
        print "ins:", ins
        self.session.execute(ins)
        self.session.commit()

    def insert_disabled_genres_into_dontpick(self):
        """
        q = session.query(UserFileInfo.fid, '\'rated 0 - new\'')\
                   .join(User)\
                   .distinct(UserFileInfo.fid, UserFileInfo.uid)\
                   .filter(and_(UserFileInfo.uid == 1, 
                                UserFileInfo.rating == 0,
                                User.listening == True))
        print "q:",q
        """
        
        q = self.session.query(FileInfo.fid, '\'disable genre - new\'', '\'test\'')\
                   .join(Genre, FileInfo.genres)\
                   .filter(Genre.enabled == False)
        #  self.insert_into_dont_pick(q)
        ins = insert(DontPick).from_select(
            names=[DontPick.fid, DontPick.reason, DontPick.junk], 
            select=q)
        print "ins:", ins
        try:
            self.session.execute(ins,None)
            self.commit()
        except:
            print "FAILED insert_disabled_genres_into_dontpick"
        """
        return
        disabled = session.query(FileInfo)\
                          .join(Genre, FileInfo.genres)\
                          .filter(
                              Genre.enabled == False
                          )\
                          .all()

        for file_info in disabled:
          print "INSERT INTO DONTPICK 3", file_info.fid
          dp = DontPick(fid=file_info.fid, reason="disabled genre")
          self.add(dp)

        self.commit()
        """

    def do(self, *args, **kwargs):
        wait()
        print "PICKER DO"
        random.shuffle(self.percents)
        users = self.get_listeners_with_empty_preload()
        self.ensure_listener_ratings()
        if not users:
            print "not needed there are no users with an empty preload"
            self.clean_preload()
            return True
        self.clear_dontpick()
        self.insert_disabled_genres_into_dontpick()
        self.insert_most_recent_into_dontpick()
        self.insert_rated_0_into_dontpick()
        self.insert_preload_files_into_dontpick()
        self.insert_files_into_preload()
        return True

    def do_wrapper(self, *args, **kwargs):
        try:
          self.do()
        except BaseException as e:
          print "DO WRAPPER FAILED WITH EXEMPTION", e
          print traceback.format_exception(*sys.exc_info())
        return True

    def clean_preload(self):
        session = self.session
        listeners = session.query(User)\
                           .filter(User.listening == True)\
                           .all()
        uids = []
        for l in listeners:
            uids.append(l.uid)
        if not uids:
            return
        entries = session.query(Preload).filter(not_(Preload.uid.in_(uids))).all()
        for e in entries:
            session.query(Preload).filter(Preload.prfid == e.prfid).delete()
        self.commit()
        

    def ensure_listener_ratings(self):
        listeners = self.get_listeners_with_empty_preload()
        for l in listeners:
          wait()
          q = self.session.query('\'%s\'' % l.uid,
                            FileInfo.fid, 
                            '\'%s\'' % DEFAULT_RATING,
                            '\'%s\'' % DEFAULT_SKIP_SCORE,
                            '\'%s\'' % DEFAULT_PERCENT_PLAYED,
                            '\'%s\'' % DEFAULT_TRUE_SCORE)\
                     .filter(~FileInfo.listeners_ratings.any(UserFileInfo.uid == l.uid))
          ins = insert(UserFileInfo).from_select(('fid', 
                                                  'uid',
                                                  'rating', 
                                                  'skip_score', 
                                                  'percent_played',
                                                  'true_score'), 
                                                 select=q)
          print "INS:",ins
          try:
            self.session.execute(ins, None)
            self.commit()
          except:
            pass


    def get_listeners_with_empty_preload(self):
        # SELECT u.uid FROM users u LEFT JOIN preload p ON p.uid = u.uid WHERE p.uid IS NULL AND u.uid = 1;
        session = self.session
        q = session.query(User)\
                      .filter(and_(
                        User.listening == True,
                        User.preload == None
                      ))
        res = q.all()
        return res

    def insert_files_into_preload(self):
        users = self.get_listeners_with_empty_preload()
        for true_score in self.percents:
            for u in users:
                print "u.uid:", u.uid
                f = self.get_file_for(u.uid, true_score)
                if f is not None:
                    session = self.session
                    session.add(f)
                    reason = "true_score >= %s" % true_score
                    print "adding:", f.fid, f.file.filename, reason
                    preload_entry = Preload(fid=f.fid, uid=u.uid, 
                                            reason=reason)
                    self.add(preload_entry)
                    # u.preload.add(preload_entry)
                    self.commit()
                    self.insert_artist_into_dont_pick(session, preload_entry)

    def insert_preload_files_into_dontpick(self):
        # self.insert_artist_into_dont_pick(None)
        session = self.session
        for preload_entry in session.query(Preload).all():
            self.insert_artist_into_dont_pick(session, preload_entry)
        self.commit()
        

    def insert_artist_into_dont_pick(self, session, preload_entry=None):
        """
        q = session.query(FileInfo.fid, '\'artist in preload\'', Artist.name)\
                   .distinct(FileInfo.fid)\
                   .join((Preload, FileInfo.preload),
                         (Artist, FileInfo.artists),
                         (DontPick, FileInfo.dontpick))\
                   .filter(FileInfo.dontpick == None)

        self.insert_into_dont_pick(q)
        return
        """
        print "adding to don't pick",
        for a in preload_entry.file.artists:
            for f in a.files:
                print f.fid,
                sys.stdout.flush()
                self.add(DontPick(fid=f.fid, reason="artist"))
        self.commit()
        print "\n"


    def get_file_for(self, uid, true_score):
        ufi = None
        try:
            wait()
            ufi = self.session.query(UserFileInfo)\
                         .join(FileInfo)\
                         .filter(and_(
                            UserFileInfo.true_score >= true_score,
                            UserFileInfo.uid == uid,
                            FileInfo.preload == None,
                            FileInfo.dontpick == None,
                            UserFileInfo.rating != 0
                          ))\
                         .order_by(UserFileInfo.ultp.asc(), func.random())\
                         .limit(1)\
                         .one()
        except NoResultFound:
            ufi = None
        wait()
        return ufi

    def clear_preload(self, uid=None):
        if uid is None:
            self.session.query(Preload).delete()
        else:
            self.session.query(Preload).filter(Preload.uid == uid).delete()
        session.commit()
        

    def get_next_user(self):
        user = None
        try:
            user = self.session.query(User)\
                          .filter(User.listening==True)\
                          .order_by(User.last_time_cued.asc())\
                          .limit(1)\
                          .one()
        except NoResultFound:
            user = None
            
        return user

    def get_file_from_preload_for_uid(self, uid):
        preload_entry = None
        try:
            preload_entry = self.session.query(Preload)\
                                   .filter(Preload.uid == uid)\
                                   .order_by(Preload.priority.desc(), 
                                             func.random())\
                                   .limit(1)\
                                   .one()
        except NoResultFound:
            preload_entry = None
        return preload_entry

    def pop(self):
        user = self.get_next_user()
        user.last_time_cued = datetime.datetime.now()
        preload_entry = self.get_file_from_preload_for_uid(user.uid)
        if not preload_entry:
            self.do()
            preload_entry = self.get_file_from_preload_for_uid(user.uid)

        wait()
        file_info = self.session.query(FileInfo)\
                                .filter(FileInfo.fid == preload_entry.fid)\
                                .limit(1)\
                                .one()
        self.session.query(Preload)\
                    .filter(Preload.prfid == preload_entry.prfid)\
                    .delete()
        self.commit()
        return file_info

    def commit(self, session=None):
        wait()
        self.session.commit()
        wait()

    def add(self, obj):
        wait()
        self.session.add(obj)

if __name__ == "__main__":
    session = make_session()
    picker = Picker(session)
    picker.clear_preload()
    picker.do()
    playing = picker.pop()
    print playing.filename
    

