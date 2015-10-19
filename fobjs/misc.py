import os
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from utils import utcnow
from pprint import pprint
import sys
import traceback
import logging
import sqlparse
from copy import deepcopy
from datetime import date, datetime
import re

from log_class import Log, logging

import gi
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango,\
                          GLib, Gio, GdkPixbuf

GObject.threads_init()

logger = logging.getLogger(__name__)

def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (str, unicode)):
        value = value.lower()
        if value in ('t','true','1','on'):
            return True
        if not value or value in('f', '0', 'false', 'off', 'null', 
                                 'undefined'):
            return False
    return bool(value)

class Listeners_Watcher(GObject.GObject, Log):
    __name__ = 'Listeners_Watcher'
    logger = logger
    __gsignals__ = {
        'listeners-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                              (object,)),
    }
    def __init__(self, *args, **kwargs):
        super(Listeners_Watcher, self).__init__(*args, **kwargs)
        self.container = {
            'users': [],
            'listeners': [],
            'non_listeners': [],
            'user_dict': {}
        }
        self.load_users()
        if not self.listeners:
            self.set_listening(1, True)

    def get_users(self):
        sql = """SELECT uid, uname, listening, admin, cue_netcasts, sync_dir,
                        listening_on_satellite
                 FROM users
                 ORDER BY listening DESC, admin DESC, uname"""

        return get_results_assoc_dict(sql)

    def user_in(self, user, key):
        for u in self.container[key]:
            if u['uid'] == user['uid']:
                return True
        return False

    def get_idx(self, user, key):
        for idx, u in enumerate(self.container[key]):
            if u['uid'] == user['uid']:
                return idx
        return None

    def add_to_remove_from(self, user, add_to, remove_from):
        idx = self.get_idx(user, add_to)
        if idx is None:
            self.container[add_to].append(user)
        else:
            # We update the elements because we want to keep all
            # reference to the object intact.  So doing an user[idx] = user 
            # value will break that reference. where .update() won't.
            self.container[add_to][idx].update(user)

        idx = self.get_idx(user, remove_from)
        if idx is not None:
            del self.container[remove_from][idx]

    def load_users(self):
        pre_users = deepcopy(self.container['users'])
        self.container['users'] = self.get_users()
        if self.container['users'] == pre_users:
            return

        for user in self.container['users']:
            uid = user.get('uid')
            if uid not in self.container['user_dict']:
                self.container['user_dict'][uid] = user
                self.container['user_dict'][str(uid)] = user
            else:
                self.container['user_dict'][uid].update(user)
                self.container['user_dict'][str(uid)].update(user)

            if user.get('listening'):
                self.add_to_remove_from(
                    user=user, add_to='listeners', remove_from="non_listeners")
            else:
                self.add_to_remove_from(
                    user=user, add_to='non_listeners', remove_from="listeners")

        self.emit('listeners-changed', self.json())

    def set_listening_on_satellite(self, uid, state):
        GObject.idle_add(self.set_user_bool_column, uid, 
                         'listening_on_satellite', state)

    def set_listening(self, uid, state):
        GObject.idle_add(self.set_user_bool_column, uid, 
                         'listening', state)

    def set_admin(self, uid, state):
        GObject.idle_add(self.set_user_bool_column, uid, 
                         'admin', state)

    def set_cue_netcasts(self, uid, state):
        GObject.idle_add(self.set_user_bool_column, uid, 
                         'cue_netcasts', state)

    def set_user_bool_column(self, uid, col, value):
        Gdk.threads_leave()
        uid = int(uid)
        value = to_bool(value)
        whitelist = ('listening', 'cue_netcasts', 'admin',
                     'listening_on_satellite')
        if col not in whitelist:
            return

        spec = {
            'uid': uid
        }
        spec[col] = value

        sql = """UPDATE users 
                 SET {col} = %({col})s
                 WHERE uid = %(uid)s""".format(col=col)

        query(sql, spec)
        self.load_users()

    def check_users(self):
        if not self.container['listeners'] or not self.container['users']\
           or not self.container['user_dict']:
            self.load_users()


    @property
    def listeners(self):
        self.check_users()

        return self.container['listeners']

    @property
    def users(self):
        self.check_users()
        return self.container['users']

    @property
    def user_dict(self):
        self.check_users()
        return self.container['user_dict']

    @property
    def non_listeners(self):
        self.check_users()
        return self.container['non_listeners']

    def json(self):
        return {
            'listeners': self.listeners,
        }

listener_watcher = Listeners_Watcher()

def get_fobj(*args, **kwargs):
    from netcast_episode_class import Netcast_FObj
    from local_fobj_class import Local_FObj
    if 'fid' in kwargs and kwargs.get('fid'):
        return Local_FObj(*args, **kwargs)
    if 'eid' in kwargs and kwargs.get("eid"):
        return Netcast_FObj(*args, **kwargs)
    print "DEPRICATED id id_type"
    print "*"*20
    print args
    print kwargs
    print sys.exc_info()[0]
    traceback.print_exc()
    traceback.print_stack()
    print "*"*20
    sys.exit()
    return None

def get_users():
    if not listener_watcher.users:
        listener_watcher.load_users()

    return listener_watcher.users

def get_recently_played(limit=10, convert_to_fobj=False, listeners=None):
    user_history_sanity_check()
    listeners = _listeners()
    uids = get_uids(listeners)
    if not uids:
        return []

    limit = int(limit)
    user_limit = limit * 3
    # TODO user user_history
    sql = """SELECT uh.eid, uh.fid, uh.time_played, percent_played, count(*)
             FROM user_history uh,
                  users u
             WHERE u.uid IN ({uids}) AND
                   uh.uid = u.uid AND
                   time_played IS NOT NULL
             GROUP BY uh.eid, uh.fid, uh.time_played, uh.percent_played
             ORDER BY time_played DESC
             LIMIT {limit}""".format(
                    limit=limit,
                    uids=",".join(uids)
             )

    print "get_recently_played:", sql

    res = get_results_assoc_dict(sql)
    if not convert_to_fobj:
        return res
    results = []
    for r in res:
        fobj = get_fobj(**r)
        if fobj is None:
            print "NONE FOBJ DETECTED"
            sys.exit()
        results.append(fobj)
    return results

def time_to_cue_netcast(listeners=None):
    listeners = _listeners(listeners)
    for l in listeners:
        if not l['cue_netcasts']:
            logger.debug("%s doesn't want to listen to netcasts" % l['uname'])
            return False

    recent = get_recently_played(listeners=listeners)
    cue = True
    for r in recent:
        if r.get('eid') is not None:
            cue = False
            logger.debug("FOUND EID")
            break
    logger.debug("TIME TO CUE NETCAST:%s", cue)
    return cue

def get_listeners():
    return listener_watcher.listeners

def _listeners(listeners=None):
    if not listener_watcher.listeners:
        listener_watcher.load_users()
    if listeners is None:
        listeners = get_listeners()
    return listeners

def fid_eid_match(most_recent, sql_args):
    check_keys = ['fid', 'eid']
    all_match = True
    for key in check_keys:
        if sql_args.get(key) != most_recent.get(key):
            all_match = False
            break
    return all_match

def get_most_recent(**sql_args):
    return get_most_recent_for_uid(**sql_args)

def get_most_recent_for_uid(**sql_args):
    user_history_sanity_check()
    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s AND
                   time_played IS NOT NULL
             ORDER BY time_played DESC
             LIMIT 1"""
    most_recent_for_uid = get_assoc_dict(sql, sql_args)
    return most_recent_for_uid

def date_played_info_for_uid(**sql_args):
    user_history_sanity_check()
    # This one makes sure it hasn't been played today.
    fid = sql_args.get('fid')
    fid_query = "fid = %(fid)s"

    if fid is None:
        fid_query = "fid IS NULL"

    eid = sql_args.get('eid')
    eid_query = "eid = %(eid)s"

    if eid is None:
        eid_query = "eid IS NULL"

    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s AND
                   {fid_query} AND
                   {eid_query} AND
                   date_played = %(date_played)s
             LIMIT 1""".format(fid_query=fid_query,
                               eid_query=eid_query)
    return get_assoc_dict(sql, sql_args)

def get_uids(listeners=None):
    listeners = _listeners()
    uids = []
    for listener in listeners:
        uids.append(str(int(listener['uid'])))
    return uids

def get_unlistend_episode(listeners=None, limit=1):
    logger.debug("GET_unlistend_episode")
    listeners = _listeners(listeners)
    uids = get_uids(listeners)
    limit = int(limit)

    if not uids:
        return None

    sql = """SELECT ne.*, n.*
             FROM netcast_episodes ne 
                  LEFT JOIN netcast_listend_episodes nle ON 
                            nle.eid = ne.eid,
                  netcast_subscribers ns,
                  netcasts n
             WHERE ns.uid IN ({uids}) AND
                   ne.nid = ns.nid AND
                   nle.uid IS NULL AND
                   n.nid = ne.nid
             ORDER BY ne.pub_date ASC
             LIMIT {limit}""".format(uids=",".join(uids), limit=limit)

    from netcast_episode_class import Netcast_FObj
    if limit == 1:
        res = get_assoc_dict(sql)
        if res != {}:
            return Netcast_FObj(**res)
        return None

    res = get_results_assoc_dict(sql)
    results = []
    for r in res:
        results.append(Netcast_FObj(**r))
    return results

def get_expired_netcasts():
    sql = """SELECT * 
             FROM netcasts
             WHERE expire_time <= NOW() OR expire_time IS NULL"""
    return get_results_assoc_dict(sql)

def user_history_sanity_check():
    sql = """UPDATE user_history 
             SET time_played = current_timestamp 
             WHERE time_played > current_timestamp"""
    query(sql)

    sql = """UPDATE user_history 
             SET date_played = current_timestamp::date
             WHERE date_played > current_timestamp::date"""
    query(sql)

def format_sql(sql, sql_args={}, sets=[], wheres=[], values=[],
               wheres_join=" AND \n", sets_join=",\n",
               cols_join=",", values_join=","):
    sql_sets = []
    for key in sets:
        if key in sql_args:
            sql_sets.append("{key} = %({key})s".format(key=key))
        else:
            logging.warn("%s not in sql_args skipping", key)

    sql_wheres = []
    for key in wheres:
        if key in sql_args and sql_args.get(key) is not None:
            value = sql_args.get(key)
            sql_wheres.append("{key} = %({key})s".format(key=key))
        else:
            # The value either doesn't exist in our sql_args
            # OR it is None eg:NULL
            sql_wheres.append("{key} IS NULL".format(key=key))
            if key not in sql_args:
                logging.warn("%s not in sql_args fallback to IS NULL", key)

    sql_cols = []
    sql_values = []
    for key in values:
        if key in sql_args:
            sql_cols.append(key)
            sql_values.append("%({key})s".format(key=key))
        else:
            logging.warn("%s not in sql_args", key)

    return sqlparse.format(
        sql.format(
            sets=sets_join.join(sql_sets),
            wheres=wheres_join.join(sql_wheres),
            cols=cols_join.join(sql_cols),
            values=values_join.join(sql_values),
        ),
        reindent=True, 
        keyword_case='upper'
    )


JSON_WHITE_LIST = [
    'aid',
    'album_name',
    'alid',
    'altp',
    'artist',
    'artists',
    'basename',
    'date_played',
    'eid',
    'enabled',
    'episode_title',
    'fid',
    'fileInfo',
    'genre',
    'genres',
    'gid',
    'listeners',
    'listening',
    'listening_on_satellite',
    'ltp',
    'netcast_name',
    'netcastInfo',
    'nid',
    'non_listeners',
    'owner',
    'owners',
    'percent_played',
    'plid',
    'preload',
    'preloadInfo',
    'rating',
    'reason',
    'score',
    'seq',
    'sync_dir',
    'time_played',
    'title',
    'true_score',
    'uhid',
    'uid',
    'ultp',
    'uname',
    'user_file_info',
    'users',
]

def jsonize(dbInfo):
    if isinstance(dbInfo, list):
        result = []
        for item in dbInfo:
            result.append(jsonize(item))
        return result
    dbInfo = deepcopy(dbInfo)
    remove_keys = []
    for key, item in dbInfo.iteritems():
        if key not in JSON_WHITE_LIST:
            remove_keys.append(key)
            continue
        if isinstance(item, (datetime, date)):
            dbInfo[key] = item.isoformat()
        #if isinstance(dbInfo[key], dict):
        #    dbInfo[key] = jsonize(dbInfo[key])
    for key in remove_keys:
        del dbInfo[key]
    return dbInfo

def get_seconds_to_next_expire_time():
    sql = """SELECT expire_time 
             FROM netcasts 
             ORDER BY expire_time ASC
             LIMIT 1"""
    res = get_assoc_dict(sql)
    expire_time = res.get('expire_time')
    if not expire_time:
        expire_time = utcnow()
    delta = expire_time - utcnow()
    total_seconds = delta.total_seconds()
    return int(total_seconds)

def delete_fid(fid):
    sql = """SELECT * FROM file_locations WHERE fid = %(fid)s"""
    spec = {'fid': fid}
    file_locations = get_results_assoc_dict(sql, spec)
    if file_locations:
        return

    
    sql = """DELETE FROM user_song_info WHERE fid = %(fid)s"""
    query(sql, spec)
    sql = """DELETE FROM user_history WHERE fid = %(fid)s"""
    query(sql, spec)

    sql = """DELETE FROM file_genres WHERE fid = %(fid)s"""
    query(sql, spec)

    sql = """DELETE FROM file_artists WHERE fid = %(fid)s"""
    query(sql, spec)

    sql = """DELETE FROM files WHERE fid = %(fid)s"""
    query(sql, spec)

    
def get_words_from_string(string):
    if string is None:
        return []

    if not string or not isinstance(string,(str, unicode)):
        print "NOT VALID:",string
        print "TYPE:",type(string)
        return []

    string = string.strip().lower()
    final_words = string.split()
    dash_splitted = string.split("-")
    for p in dash_splitted:
        p = p.strip()
        final_words.append(p)

    # replace any non-word characters
    # This would replace "don't say a word" with "don t say a word"
    replaced_string = re.sub("[\W]", " ", string)
    final_words += replaced_string.split()
    # replace any non words characters and leave spaces.
    # To change phrases like "don't say a word" to "dont say a word"
    # so I'm will become "im"
    # P.O.D. will become pod
    removed_string = re.sub("[^\w\s]", "", string)
    final_words += removed_string.split()
    final_words = list(set(final_words))

    return final_words



def leave_threads():
    Gdk.threads_leave()


if __name__ == "__main__":

    sql = """SELECT DISTINCT fg.fid, 
                             string_agg(DISTINCT g.genre, ', ' ORDER BY g.genre) AS genres_agg
             FROM file_genres fg
                  LEFT JOIN genres g ON g.gid = fg.gid
             GROUP BY fg.fid"""

    aggs = get_results_assoc_dict(sql)
    for agg in aggs:
        sql = """UPDATE files SET genres_agg = %(genres_agg)s
                 WHERE fid = %(fid)s
                 RETURNING *"""
        print get_assoc_dict(sql, agg)

    sql = """SELECT DISTINCT f.fid, 
                             string_agg(DISTINCT fl.basename, ', ' ORDER BY fl.basename) AS basename_agg
             FROM files f
                  LEFT JOIN file_locations fl ON fl.fid = f.fid
             GROUP BY f.fid"""

    aggs = get_results_assoc_dict(sql)
    for agg in aggs:
        sql = """UPDATE files SET basename_agg = %(basename_agg)s
                 WHERE fid = %(fid)s
                 RETURNING *"""
        print get_assoc_dict(sql, agg)

    sql = """SELECT DISTINCT fa.fid, 
                             string_agg(DISTINCT a.artist, ', ' 
                                        ORDER BY a.artist) AS artists_agg
             FROM file_artists fa
                  LEFT JOIN artists a ON a.aid = fa.aid
             GROUP BY fa.fid"""

    aggs = get_results_assoc_dict(sql)
    for agg in aggs:
        sql = """UPDATE files SET artists_agg = %(artists_agg)s
                 WHERE fid = %(fid)s
                 RETURNING *"""
        print get_assoc_dict(sql, agg)


    sys.exit()
    sql = """SELECT *
             FROM file_locations
             ORDER BY dirname"""
    files = get_results_assoc_dict(sql)
    for fl in files:
        filename = os.path.join(fl['dirname'], fl['basename'])
        if not os.path.exists(filename):
            print "MISSING:", filename
            sql = """DELETE FROM file_locations
                     WHERE dirname = %(dirname)s AND
                           basename = %(basename)s"""
            query(sql, fl)

    sql = """SELECT f.fid
             FROM files f
                  LEFT JOIN file_locations fl ON f.fid = fl.fid
             WHERE fl.fid IS NULL"""

    null_files = get_results_assoc_dict(sql)
    for f in null_files:
        sql = """DELETE FROM user_history
                 WHERE fid = %(fid)s"""
        query(sql, f)

        sql = """DELETE FROM user_song_info
                 WHERE fid = %(fid)s"""
        query(sql, f)

        sql = """DELETE FROM file_genres
                 WHERE fid = %(fid)s"""
        query(sql, f)

        sql = """DELETE FROM file_artists
                 WHERE fid = %(fid)s"""
        query(sql, f)


        sql = """DELETE FROM keywords
                 WHERE fid = %(fid)s"""
        query(sql, f)


        sql = """DELETE FROM album_files
                 WHERE fid = %(fid)s"""
        query(sql, f)

        sql = """DELETE FROM files
                 WHERE fid = %(fid)s"""
        query(sql, f)

        print "remove:", f

