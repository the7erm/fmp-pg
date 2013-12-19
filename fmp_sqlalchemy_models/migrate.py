#!/usr/bin/env python
# /lib/__init__.py -- Initialize fmp
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

import psycopg2
import psycopg2.extras
import sys
import os
import pprint
import ConfigParser
import gc
import time
import random
import hashlib
import gtk
import gobject
from files_model_idea import FileLocation, FileInfo, Artist, DontPick, Genre,\
                             Preload, Title, Album, User, UserHistory, \
                             UserFileInfo, make_session, NoResultFound, and_

session = make_session()
gobject.threads_init()
gtk.gdk.threads_init()

global threads
threads = []

DEFAULTS = {
    "Netcasts": {
        "cue": False,
    },
    "password_salt": {
        "salt" : "",
    },
    "Misc": {
        "bedtime_mode": False
    },
    "postgres" : {
        "host": "127.0.0.1",
        "port": "5432",
        "username": "",
        "password": "",
        "database": "fmp"
    },
}

ALLOWED_TYPES = (str, int, bool, float, unicode)

class ConfigWrapper:
    def __init__(self, config_file=None, defaults=None):
        self.type_map = {}
        self.cfg = ConfigParser.ConfigParser()
        self.config_file = config_file
        if defaults is None:
            defaults = DEFAULTS
        self.defaults = defaults
        self.cfg.read(config_file)
        self.set_defaults()

    def set_defaults(self):
        
        for section, option_value in self.defaults.iteritems():
            for option, value in option_value.iteritems():
                self.add_to_typemap(section, option, value)
                if not self.cfg.has_option(section, option):
                    self.set(section, option, value)

    def read(self, config_file=None):
        if config_file is None:
            config_file = self.config_file
        self.cfg.read(config_file)

    def process_value(self, val, force=None):
        if force is None:
            return val
        if force == int:
            val = float(val)
        return force(val)

    def check_get_default(self, get_cmd, section, option, default=None, 
                          force=None):
        if default is None and section in self.defaults and option in self.defaults[section]:
            default = self.defaults[section][option]

        if default is None:
            val = get_cmd(section, option)
            return self.process_value(val, force)

        try:
            val = get_cmd(section, option) or default
        except ConfigParser.NoSectionError, e:
            self.add_section(section)
            self.set(section, option, default, force)
            val = get_cmd(section, option) or default
        except ConfigParser.NoOptionError:
            self.set(section, option, default, force)
            val = get_cmd(section, option) or default
        except ValueError:
            val = self.cfg.get(section, option) or default
        return self.process_value(val, force)

    def get(self, section, option, default=None, force=None, *args, **kwargs):
        try:
            return_type = None
            if force in ALLOWED_TYPES:
                return_type = force

            if return_type is None and section in self.type_map and \
               option in self.type_map[section]:
                if self.type_map[section][option] == bool:
                    return_type = bool
                if self.type_map[section][option] == float:
                    return_type = float
                if self.type_map[section][option] == int:
                    return_type = int

            if return_type is None:
                return_type = str

            if return_type in (str, unicode):
                return self.check_get_default(self.cfg.get, section, option,
                                              default, force)

            if return_type == int:
                return self.check_get_default(self.cfg.getint, section, option, 
                                              default, force)

            if return_type == bool:
                return self.check_get_default(self.cfg.getboolean, section, 
                                              option, default, force)

            if return_type == float:
                return self.check_get_default(self.cfg.getfloat, section, 
                                              option, default, force)
            

        except ConfigParser.NoSectionError, e:
            self.add_section(section)
            self.on_no_section(e, section, option, *args, **kwargs)
            if 'default' in kwargs:
                self.set(section, option, kwargs['default'])

    def on_no_section(self, e, section, option, *args, **kwargs):
        print "ConfigParser.NoSectionError:", e
        return self.add_section(section)

    def add_section(self, section):
        if not self.cfg.has_section(section):
            self.cfg.add_section(section)
            self.write()
        if section not in self.type_map:
            self.type_map[section] = {}

    def set(self, section, option, value, force=None, *args, **kwargs):
        self.add_to_typemap(section, option, value, force)
        self.cfg.set(section, option, "%s" % value)
        self.write()

    def add_to_typemap(self, section, option, value, force=None):
        self.add_section(section)
        if option not in self.type_map[section]:
            if force in ALLOWED_TYPES:
                self.type_map[section][option] = force
                return
            self.type_map[section][option] = type(value)

    def set_by_type(self, section, option, value, *args, **kwargs):
        try:
            if isinstance(value, (float, )):
                cfg.set(section, option, value)
            else:
                self.cfg.set(section, option, value)
        except ConfigParser.NoSectionError, e:
            if self.on_no_section(e, section, option, *args, **kwargs):
                self.cfg.set(section, option, value)

    def write(self):
        with open(self.config_file, 'wb') as cfg_fp:
            self.cfg.write(cfg_fp)

pp = pprint.PrettyPrinter(depth=6)
sys.path.append(sys.path[0]+'/lib/')

home = os.path.expanduser('~')
config_dir = home+"/.fmp"
config_file = config_dir+"/config"
cache_dir = config_dir+"/cache"

if not os.path.isdir(config_dir):
    os.mkdir(config_dir, 0775)

if not os.path.isdir(cache_dir):
    os.mkdir(cache_dir, 0775)

cfg = ConfigWrapper(config_file, DEFAULTS)

def create_salt():
    random_string = "%s%s" % (random.random(), time.time())
    salt = hashlib.sha256(random_string).hexdigest()
    return salt

pg_conn = psycopg2.connect("dbname=%s user=%s password=%s host=%s" % (
                            cfg.get('postgres','database', 'fmp', str), 
                            cfg.get('postgres','username', '', str), 
                            cfg.get('postgres','password', '', str), 
                            cfg.get('postgres','host', '127.0.0.1', str)))
salt = cfg.get('password_salt', 'salt', create_salt(), str)

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

def get_results_assoc(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(query, args)
    pg_conn.commit()
    res = cur.fetchall()
    return res

def get_assoc(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(query, args)
    pg_conn.commit()
    res = cur.fetchone()
    return res

def query(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # print cur.mogrify(query,args)
    cur.execute(query, args)
    pg_conn.commit()
    return cur

files = get_results_assoc("""SELECT fid, dir, basename 
                             FROM files
                             ORDER BY dir, basename""")
def utf8( string):
    if not isinstance(string, unicode):
        return unicode(string, "utf8", errors="replace")
    return string

for f in files:
    print f
    rating_info = get_results_assoc("""SELECT usi.*, u.uname
                                       FROM user_song_info usi, users u
                                       WHERE fid = %s AND 
                                       u.uid = usi.uid""",
                                       (f['fid'],))
    try:
        location_info = session.query(FileLocation).filter(and_(
            FileLocation.dirname == utf8(f['dir']),
            FileLocation.basename == utf8(f['basename'])
        ))\
        .limit(1)\
        .one()
    except NoResultFound:
        print "COULDN'T FIND:%s", f
        continue
    # print rating_info
    for r in rating_info:
        print dict(r)
        """
        SELECT user_file_info.ufid AS user_file_info_ufid, user_file_info.uid AS user_file_info_uid, user_file_info.fid AS user_file_info_fid, user_file_info.rating AS user_file_info_rating, user_file_info.skip_score AS user_file_info_skip_score, user_file_info.percent_played AS user_file_info_percent_played, user_file_info.true_score AS user_file_info_true_score, user_file_info.ultp AS user_file_info_ultp 
FROM user_file_info JOIN users ON users.uid = user_file_info.uid 
WHERE user_file_info.fid = :fid_1 AND users.uname = :uname_1"""
        try:
            user_file_info = session.query(UserFileInfo)\
                                  .join(UserFileInfo.user)\
                                  .filter(UserFileInfo.fid == location_info.fid)\
                                  .filter(User.uname == r['uname'])\
                                  .limit(1)\
                                  .one()
        except NoResultFound:
            # print "COULDN'T FIND:%s" % location_info.fid, r['uname']
            continue
        """
        {'rating': 3, 'uid': 46, 'last_time_cued': None, 'usid': 332376, 'admin': False, 'selected': False, 'true_score': 66.6666666666667, 'uname': 'erm2', 'ultp': None, 'pword': None, 'listening': False, 'fid': 22818, 'percent_played': 50.0, 'score': 9}"""
        print user_file_info

        user_file_info.percent_played = r['percent_played']
        user_file_info.skip_score = r['score']
        if r['ultp'] != None and \
           (user_file_info.ultp is None or r['ultp'].replace(tzinfo=None) > user_file_info.ultp.replace(tzinfo=None)):
            user_file_info.ultp = r['ultp'].replace(tzinfo=None)
        
        
        
        history = get_results_assoc("""SELECT * 
                                       FROM user_history uh 
                                       WHERE id_type = 'f' AND
                                             id = %s AND
                                             uid = %s """,
                                       (f['fid'], r['uid']))
        #history_info = session.query(UserHistory)\
        #                      .filter(UserHistory.fid == user_file_info.fid)\
        #                      .filter(UserHistory.uid == user_file_info.uid)\
        #                      .all()
        #for h2 in history_info:
        #        print "h2:", h2

        for h1 in history:
            print "h1:", dict(h1)
            found = False
            for h2 in user_file_info.history:
                if h2.uid == user_file_info.uid and \
                   h2.ufid == user_file_info.ufid and \
                   h2.fid == user_file_info.fid and \
                   h2.date_played == h1['date_played']:
                    found = True
                    break

            if found:
                print "FOUND:",dict(h1)
                continue

            user_history = UserHistory(uid=user_file_info.uid,
                                       ufid=user_file_info.ufid,
                                       fid=user_file_info.fid,
                                       rating=h1['rating'],
                                      skip_score=h1['score'],
                                      percent_played=h1['percent_played'],
                                      true_score=h1['true_score'],
                                      time_played=h1['time_played'],
                                      date_played=h1['date_played'])
            user_history.save(session=session)
            user_file_info.history.append(user_history)
            user_file_info.save(session=session)
            """
            uhid = Column(Integer, primary_key=True)
            uid = Column(Integer, ForeignKey("users.uid"))
            ufid = Column(Integer, ForeignKey("user_file_info.ufid"))
            fid = Column(Integer, ForeignKey("files_info.fid"))
            # eid = Column(Integer, ForeignKey("episodes.eid"))
            rating = Column(Integer)
            skip_score = Column(Integer)
            percent_played = Column(Float)
            true_score = Column(Float)
            time_played = Column(DateTime(timezone=True))
            date_played = Column(Date)
            
                Column     |           Type           |                          Modifiers                          
            ----------------+--------------------------+-------------------------------------------------------------
             uhid           | integer                  | not null default nextval('user_history_uhid_seq'::regclass)
             uid            | integer                  | not null
             id             | integer                  | not null
             percent_played | integer                  | 
             time_played    | timestamp with time zone | 
             date_played    | date                     | 
             id_type        | character varying(2)     | 
             true_score     | double precision         | not null default 0
             score          | integer                  | not null default 0
             rating         | integer                  | not null default 0
            Indexes:
                "user_history_pkey" PRIMARY KEY, btree (uhid)
                "uid_id_id_type_date_played" UNIQUE, btree (uid, id, id_type, date_played)
            """
        user_file_info.rate(r['rating'], session=session)
        print "location_info.filename:", location_info.filename
        print "user_file_info.json()",user_file_info.json()
        print "user_file_info.history", user_file_info.history
        session.commit()


