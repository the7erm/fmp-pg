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
import alchemy_session
import datetime
from files_model_idea import FileLocation, FileInfo, Artist, DontPick, Genre,\
                             Preload, Title, Album, User, UserHistory, \
                             UserFileInfo, session
from sqlalchemy import and_, distinct
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.sql.expression import func
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
    def __init__(self):
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
        session.query(DontPick).delete()
        wait()

    def insert_most_recent_into_dontpick(self):
        total_files = session.query(FileInfo).count()
        ten_percent = int(total_files * 0.01)
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

    def inset_rated_0_into_dontpick(self):
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

    def insert_disabled_genres_into_dontpick(self):
        # sqlalchemy.exc.InvalidRequestError: Could not find a FROM clause to 
        # join from.  Tried joining to <class 'files_model_idea.Genre'>, but 
        # got: Can't find any foreign key relationships between 'files_info' 
        # and 'genres'.
        # GOAL: SELECT fid 
        #       FROM files_info fi, file_genres fg, genres g
        #       WHERE fi.fid = fg.fid AND g.gid = fg.gid AND g.enabled = 0 
        disabled = session.query(FileInfo)\
                          .join(Genre)\
                          .distinct(FileInfo.fid)\
                          .filter(
                              Genre.enabled == False
                          )\
                          .all()

        for f in disabled:
          print "INSERT INTO DONTPICK 3", f.filename
          dp = DontPick(fid=f.fid, reason="disabled genre")
          self.add(dp)

        self.commit()

    def do(self, *args, **kwargs):
        wait()
        print "PICKER DO"
        random.shuffle(self.percents)
        users = self.get_users()
        if not users:
            print "not needed there are no users with an empty preload"
            return True
        self.clear_dontpick()
        self.insert_disabled_genres_into_dontpick()
        self.insert_most_recent_into_dontpick()
        self.inset_rated_0_into_dontpick()
        self.insert_preload_files_into_dontpick()
        self.insert_files_into_preload()
        return True

    def get_users(self):
        return session.query(User).filter(and_(
                User.listening==True,
                User.preload==None
               )).all()

    def insert_files_into_preload(self):
        users = self.get_users()
        for p in self.percents:
            for u in users:
                f = self.get_file_for(u.uid, p)
                if f is not None:
                    print "adding:", f.fid, f.file.filename
                    preload_entry = Preload(fid=f.fid, uid=u.uid, 
                                            reason="true_score >= %s" % p)
                    self.add(preload_entry)
                    self.commit()
                    self.insert_artist_into_dont_pick(preload_entry)

    def insert_preload_files_into_dontpick(self):
        for preload_entry in session.query(Preload).all():
            self.insert_artist_into_dont_pick(preload_entry)

    def insert_artist_into_dont_pick(self, preload_entry):
        print "adding to don't pick",
        for a in preload_entry.file.artists:
            for f in a.files:
                print f.fid,
                sys.stdout.flush()
                self.add(DontPick(fid=f.fid, reason="artist"))
        self.commit()
        
        print "\n"


    def get_file_for(self, uid, true_score):
        try:
            wait()
            ufi = session.query(UserFileInfo)\
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
            wait()
            return ufi
        except NoResultFound:
            return None

    def clear_preload(self, uid=None):
        if uid is None:
            session.query(Preload).delete()
        else:
            session.query(Preload).filter(Preload.uid == uid).delete()

    def get_next_user(self):
        return session.query(User)\
                      .filter(User.listening==True)\
                      .order_by(User.last_time_cued.asc())\
                      .limit(1)\
                      .one()

    def pop(self):
        user = self.get_next_user()
        user.last_time_cued = datetime.datetime.now()
        self.add(user)
        preload_entry = session.query(Preload)\
                               .filter(Preload.uid == user.uid)\
                               .order_by(Preload.priority.desc(), func.random())\
                               .limit(1)\
                               .one()
        wait()
        file_info = session.query(FileInfo)\
                               .filter(FileInfo.fid == preload_entry.fid)\
                               .limit(1)\
                               .one()
        session.query(Preload).filter(Preload.prfid == preload_entry.prfid).delete()
        wait()
        return file_info

    def commit(self):
      wait()
      session.commit()
      wait()

    def add(self, obj):
      wait()
      session.add(obj)

if __name__ == "__main__":
    picker = Picker()
    picker.clear_preload()
    picker.do()
    playing = picker.pop()
    print playing.filename
    

