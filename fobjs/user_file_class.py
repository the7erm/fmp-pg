import os

from pprint import pprint, pformat
import json

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from datetime import timedelta

from misc import get_most_recent, user_history_sanity_check,\
                 date_played_info_for_uid, get_most_recent_for_uid, \
                 jsonize, listener_watcher, leave_threads
from utils import utcnow

from log_class import Log, logging
logger = logging.getLogger(__name__)
from copy import deepcopy

class UserFile(Log):
    __name__ = 'UserFile'
    logger = logger
    def __init__(self, *args, **kwargs):
        super(UserFile, self).__init__(*args, **kwargs)
        self.kwargs = kwargs
        self.parent = kwargs.get('parent')
        self.userDbInfo = kwargs.get('userDbInfo', {})
        self.userFileDbInfo = kwargs.get('userFileDbInfo', {})
        self.userHistoryItems = []
        self.most_recent = None
        self.most_recent_expire = utcnow()
        self.history_items_expire = utcnow()
        self.most_recent = None
        if self.userDbInfo is None:
            self.userDbInfo = {}
        self.uid = kwargs.get('uid')
        self.uname = kwargs.get('uname')
        self.log_debug("/.__init__()")
        # listener_watcher.connect("listeners-changed", 
        #                       self.on_listeners_changed)

    def on_listeners_changed(self, *args, **kwargs):
        leave_threads()
        self.reload()

    def reload(self):
        if not self.parent.playing:
            self.log_debug(".reload() fid:%s eid:%s - not reloading, not playing uname:%s" % (self.fid, self.eid, self.uname))
            return
        self.log_debug(".reload() fid:%s eid:%s" % (self.fid, self.eid))
        self.load_from_uid(self.uid)

    @property
    def uid(self):
        # UserFile.uid
        return self.userDbInfo.get('uid')

    @uid.setter
    def uid(self, value):
        # UserFile.uid
        if not value:
            return
        if self.uid != value or self.userDbInfo == {}:
            self.load_from_uid(self, value)

    def load_from_uid(self, value):
        # UserFile.load_from_uid
        sql_args = {
            'uid': value
        }
        sql = """SELECT *
                 FROM users
                 WHERE uid = %(uid)s
                 LIMIT 1"""
        self.userDbInfo = get_assoc_dict(sql, sql_args)
        self.load_user_file_db_info()

    @property
    def uname(self):
        # UserFile.uname
        return self.userDbInfo.get('uname')

    @uname.setter
    def uname(self, value):
        # UserFile.uname
        if not value:
            return
        if self.uname != value:
            self.load_from_uname(value)

    def load_from_uname(self, uname):
        # UserFile.load_from_uname
        sql_args = {
            'uname': value
        }
        sql = """SELECT *
                 FROM users
                 WHERE uname = %(uname)s
                 LIMIT 1"""
        self.userDbInfo = get_assoc_dict(sql, sql_args)
        self.load_user_file_db_info()

    @property
    def fid(self):
        # UserFile.fid
        if hasattr(self.parent, 'fid'):
            return self.parent.fid
        fid = self.kwargs.get('fid')
        if fid:
            return fid
        return None

    @property
    def eid(self):
        # UserFile.eid
        if hasattr(self.parent, 'eid'):
            return self.parent.eid
        eid = self.kwargs.get('eid')
        if eid:
            return eid
        return None

    @property
    def listening(self):
        # UserFile.listening
        return self.userDbInfo.get('listening')

    @listening.setter
    def listening(self, value):
        # UserFile.listening
        value = bool(value)
        if value != self.listening:
            self.userDbInfo['listening'] = value
            self.save_user()

    def save(self):
        # UserFile.save
        return self.save_user()

    def save_user(self):
        # UserFile.save_user()
        sql = """UPDATE users
                 SET uname = %(uname)s,
                     listening = %(listening)s
                 WHERE uid = %(uid)s
                 RETURNING *"""
        self.userDbInfo = get_assoc_dict(sql, self.userDbInfo)
        return self.userDbInfo

    @property
    def history(self):
        # UserFile.save_user()
        
        if self.userHistoryItems and self.history_items_expire > utcnow():
            return self.userHistoryItems
        self.history_items_expire = utcnow() + timedelta(minutes=5)
        self.userHistoryItems = []
        sql_args = {
            'uid': self.uid, 
            'fid': self.fid,
            'eid': self.eid
        }

        fid_query, eid_query = self.get_history_query(**sql_args)
        
        sql = """SELECT uh.*, uname, sync_dir
                 FROM
                 user_history uh, users u
                 WHERE uh.uid = %(uid)s AND
                       u.uid = uh.uid AND
                       {fid_query} AND
                       {eid_query}
                 ORDER BY time_played DESC""".format(fid_query=fid_query,
                                                     eid_query=eid_query)
        
        items = get_results_assoc_dict(sql, sql_args)

        for item in items:
            item['userDbInfo'] = self.userDbInfo
            obj = UserHistoryItem(parent=self.parent, **item)
            if obj:
                self.userHistoryItems.append(obj)
        return self.userHistoryItems

    @property
    def most_recent_history_item(self):
        self.log_debug(".most_recent_history_item")
        # UserFile.most_recent_history_item
        # We only need to get the most recent once a minute.
        if self.most_recent and self.most_recent_expire > utcnow():
            return self.most_recent
        self.most_recent_expire = utcnow() + timedelta(minutes=1)
        most_recent_item = None
        if not self.history:
            self.most_recent = UserHistoryItem(**self.kwargs)
            # Put it at the top of the list.
            self.userHistoryItems.insert(0, self.most_recent)
            return self.most_recent

        # Loop through history and find the item with the greatest time_played
        # value.
        for item in self.history:
            if not most_recent_item:
                # There is no most_recent_item so just use the first.
                most_recent_item = item
                continue
            if item.time_played > most_recent_item.time_played:
                most_recent_item = item
        
        if not most_recent_item:
            # This really should throw a fatal error.
            # because it didn't find anything.
            self.most_recent = UserHistoryItem(parent=self.parent, 
                **self.kwargs)
            # Put it at the top of the list.
            self.userHistoryItems.insert(0, self.most_recent)
            return self.most_recent
        
        # Search ALL user history, not just this fid/eid & uid.
        most_recent_from_db = get_most_recent_for_uid(**{ 'uid': self.uid })
        most_recent_fid = most_recent_from_db.get('fid')
        most_recent_eid = most_recent_from_db.get('eid')
        most_recent_uhid = most_recent_from_db.get('uhid')

        
        if (
                most_recent_uhid == most_recent_item.uhid
           ) or (
                most_recent_eid == most_recent_item.eid and 
                most_recent_fid == most_recent_item.fid
           ):
            # - The uhid matches so use most_recent_item.
            # OR
            # - The fid & eid match so use most_recent_item.
            # This is done to fix a bug that I've encountered where 
            # You start playing a file on one day, and it's done playing 
            # The next. This would create 2 user_history entries.
            self.most_recent = most_recent_item
            # This item was already in the history so we just return it.
            # No need to add it to self.history
            return self.most_recent

        # The most_recent_item in user_history isn't the same file
        # so we create a new one.
        most_recent = UserHistoryItem(**self.kwargs)
        self.userHistoryItems.append(most_recent)
        self.most_recent = most_recent
        self.log_debug("Creating new most_recent")
        return self.most_recent

    def get_history_query(self, **sql_args):
        # UserFile.get_history_query
        fid = sql_args.get('fid')
        fid_query = "fid = %(fid)s"

        if fid is None:
            fid_query = "fid IS NULL"

        eid = sql_args.get('eid')
        eid_query = "eid = %(eid)s"

        if eid is None:
            eid_query = "eid IS NULL"
        return fid_query, eid_query

    def get_now(self, **sql_args):
        self.log_debug(".get_now()  from:%s" % sql_args)
        # UserFile.get_now
        keys = ['now', 'ltp', 'ultp', 'time_played']
        now = None
        for k in keys:
            now = sql_args.get(k)
            if now:
                self.log_debug("now using:%s", k)
                break;
        if not now:
            now = utcnow()
            self.log_debug("using utcnow():%s" % now)
        self.log_debug(".get_now() result:%s" %  now)
        return now

    def calculate_true_score(self):
        # UserFile.calculate_true_score
        self.userFileDbInfo['true_score'] = (
            (self.rating * 2 * 10) + 
            (self.score * 10)
        ) / 2.0

    def json(self):
        # UserFile.json
        if self.userFileDbInfo == {}:
            self.load_user_file_db_info()
        return jsonize(self.userFileDbInfo)



class UserHistoryItem(UserFile):
    __name__ = 'UserHistoryItem'
    logger = logger
    def __init__(self, *args, **kwargs):
        super(UserHistoryItem, self).__init__(*args, **kwargs)
        self.historyDbInfo = kwargs.get('historyDbInfo', {})
        self.uhid = kwargs.get('uhid')
        self.uid = kwargs.get('uid')

    def inc_score(self, *args, **kwargs):
        # UserHistoryItem.inc_score
        return

    def deinc_score(self, *args, **kwargs):
        return

    @property
    def uhid(self):
        return self.historyDbInfo.get('uhid')

    @uhid.setter
    def uhid(self, value):
        if not value or value == self.uhid:
            return
        self.load_from_uhid(value)

    def load_from_uhid(self, uhid):
        sql = """SELECT uh.*, uname
                 FROM user_history uh,
                      users u
                 WHERE uhid = %(uhid)s AND
                       u.uid = uh.uid"""
        sql_args = {
            'uhid': uhid
        }
        self.historyDbInfo = get_assoc_dict(sql, sql_args)

    @property
    def date_played(self):
        return self.historyDbInfo.get("date_played")

    @date_played.setter
    def date_played(self, value):
        if not value or value == self.date_played:
            return
        if isinstance(value, (str, unicode, int, float)):
            value = convert_to_dt(value)

        if isinstance(value, datetime):
            value = value.date()
        self.historyDbInfo['date_played'] = value
        self.save()

    @property
    def can_save(self):
        # Check to make sure that the object has all
        # the right things to save.
        uhid = self.uhid
        if uhid:
            self.log_debug("CAN save uhid:%s" % uhid)
            return True

        uid = self.uid
        eid = self.eid
        fid = self.fid
        if not uid or (not eid and not fid):
            self.log_debug("CANT'T save uid:%s fid:%s eid:%s" % (
                uid, fid, eid))
            return False

        self.log_debug("CAN save fid:%s eid:%s" % (fid, eid))
        return True

    @property
    def time_played(self):
        return self.historyDbInfo.get('time_played')

    @time_played.setter
    def time_played(self, value):
        if not value or value == self.time_played:
            return
        if isinstance(value, (str, unicode, int, float)):
            value = convert_to_dt(value)

        self.historyDbInfo['time_played'] = value
        self.historyDbInfo['date_played'] = value.date()
        self.save()

    def load_from_uid_fid_eid_date_played(self):
        self.log_debug(".load_from_uid_fid_eid_date_played()")
        self.log_debug(".historyDbInfo:%s", self.historyDbInfo)
        self.historyDbInfo_sanity_check()
        if 'uid' not in self.historyDbInfo:
            self.log_error(".historyDbInfo missing uid"+("<"*20))
            return
        user_history_sanity_check()
        
        sql_args = deepcopy(self.historyDbInfo)
        # This one makes sure it hasn't been played today.
        fid_query, eid_query = self.get_history_query(**sql_args)

        sql = """SELECT uh.*, uname, u.sync_dir
                 FROM user_history uh,
                      users u
                 WHERE uh.uid = %(uid)s AND
                       u.uid = uh.uid AND
                       {fid_query} AND
                       {eid_query} AND
                       date_played = %(date_played)s
                 LIMIT 1""".format(fid_query=fid_query,
                                   eid_query=eid_query)
        
        historyDbInfo = get_assoc_dict(sql, sql_args)
        if historyDbInfo != {}:
            self.historyDbInfo = historyDbInfo
        self.historyDbInfo_sanity_check()
        self.log_debug("/.load_from_uid_fid_eid_date_played()")

    def historyDbInfo_sanity_check(self):
        check_keys = ['uid', 'eid', 'fid', 'date_played',
                      'time_played', 'rating', 'score', 
                      'reason', 'true_score']
        now = utcnow()
        for key in check_keys:
            if key in self.historyDbInfo:
                continue
            self.log_error(".historyDbInfo missing %s"+("<"*20), key)
            if key in self.kwargs and self.kwargs.get(key):
                self.historyDbInfo[key] = self.kwargs[key]
                self.log_error("using self.kwargs[%s]:%s" %
                               (key, self.kwargs[key]))
            elif key in self.kwargs['userDbInfo'] and self.kwargs['userDbInfo'].get(key):
                self.historyDbInfo[key] = self.kwargs['userDbInfo'][key]
                self.log_error("using self.kwargs['userDbInfo'][%s]:%s" %
                               (key, self.kwargs['userDbInfo'][key]))
            else:
                if key in ('date', 'time_played'):
                    if key == 'date':
                        self.log_error("using now:%s" % now.date())
                        self.historyDbInfo[key] = now.date()
                    elif key == 'time_played':
                        self.log_error("using now:%s" % now)
                        self.historyDbInfo[key] = now
                    continue
                if key == 'reason':
                    self.historyDbInfo[key] = ""
                    self.log_error("using empty reason:''")
                    continue

                if key == 'rating':
                    self.historyDbInfo['rating'] = 6
                
                if key == 'score':
                    self.historyDbInfo['score'] = 5

                if key == 'true_score':
                    rating = self.historyDbInfo.get('rating')
                    score = self.historyDbInfo.get('score')
                    self.historyDbInfo['true_score'] = (
                        (rating * 2 * 10) +
                        (score * 10)
                    ) / 2.0

                self.log_error("No suitable fallback for %s" % key)

        if 'eid' not in self.historyDbInfo:
            self.historyDbInfo['eid'] = None

        if 'fid' not in self.historyDbInfo:
            self.historyDbInfo['fid'] = None


        rating = self.historyDbInfo.get('rating')
        if rating is None:
            self.historyDbInfo['rating'] = 6

        score = self.historyDbInfo.get('score')
        if score is None:
            self.historyDbInfo['score'] = 5

        if rating is None or score is None:
            rating = self.historyDbInfo.get('rating')
            score = self.historyDbInfo.get('score')
            self.historyDbInfo['true_score'] = (
                            (rating * 2 * 10) +
                            (score * 10)
                        ) / 2.0
        
        all_good = True
        for key in check_keys:
            if key not in self.historyDbInfo:
                all_good = False
                self.log_error(".historyDbInfo STILL missing %s"+("<"*20), key)
        self.log_info("/.historyDbInfo ALL GOOD")

    def insert(self):
        self.log_debug(".insert()")
        self.historyDbInfo_sanity_check()
        if not self.can_save:
            self.log_crit("CAN'T INSERT")
            return

        if self.uhid:
            self.log_crit("INSERT CALLED and uhid is present uhid:%s" % (uhid,))
            self.save()
            return

        sql = """INSERT INTO user_history (uid, eid, fid, date_played,
                                           time_played, rating, score, 
                                           reason, true_score)
                 VALUES (%(uid)s, %(eid)s, %(fid)s, %(date_played)s,
                         %(time_played)s, %(rating)s, %(score)s,
                         %(reason)s, %(true_score)s)
                 RETURNING *"""
        # You need to figure out how to handle eid vs fid updates
        # In particular how netcast vs local files.
        # how would we get them to use this class.
        self.log_debug("query:%s" % mogrify(sql, self.historyDbInfo))
        self.historyDbInfo = get_assoc_dict(sql, self.historyDbInfo)

    def load_user_file_db_info(self):
        self.load_from_uid_fid_eid_date_played()

    def save(self):
        self.log_debug(".save()")
        self.historyDbInfo_sanity_check()
        if not self.can_save:
            self.log_debug("CANT'T save")
            return
        self.log_debug(".save() CAN SAVE")
        if not self.uhid:
            self.load_from_uid_fid_eid_date_played()
        self.log_debug("Load ok")
        if not self.uhid:
            self.log_debug("NO UHID")
            self.insert()
            return

        if 'reason' not in self.historyDbInfo:
            self.historyDbInfo['reason'] = ''

        if 'rating' not in self.historyDbInfo:
            self.historyDbInfo['rating'] = 6

        if 'score' not in self.historyDbInfo:
            self.historyDbInfo['score'] = 6

        if 'true_score' not in self.historyDbInfo:
            self.historyDbInfo['true_score'] = 1

        sql = """UPDATE user_history
                 SET time_played = %(time_played)s,
                     percent_played = %(percent_played)s,
                     date_played = %(date_played)s,
                     score = %(score)s,
                     true_score = %(true_score)s,
                     rating = %(rating)s,
                     reason = %(reason)s,
                     uid = %(uid)s,
                     fid = %(fid)s,
                     eid = %(eid)s
                 WHERE uhid = %(uhid)s
                 RETURNING *"""
        historyDbInfo = get_assoc_dict(sql, self.historyDbInfo)
        if historyDbInfo != {}:
            self.log_debug("SAVED:%s" % historyDbInfo)
            self.historyDbInfo = historyDbInfo
        else:
            self.log_crit("UNABLE TO UPDATE HISTORY:%s" % self.historyDbInfo)

    def mark_as_played(self, **sql_args):
        percent_played = sql_args.get('percent_played', 0)
        self.log_debug(".mark_as_played:%s", percent_played)
        self.historyDbInfo['percent_played'] = percent_played
        ultp = self.get_now(**sql_args)
        self.historyDbInfo['time_played'] = ultp
        self.historyDbInfo['date_played'] = ultp.date()
        self.historyDbInfo['true_score'] = sql_args.get('true_score')
        self.historyDbInfo['rating'] = sql_args.get('rating')
        self.historyDbInfo['score'] = sql_args.get('score')
        self.save()

    def mark_as_completed(self, **sql_args):
        self.historyDbInfo['percent_played'] = 100
        ultp = self.get_now(**sql_args)
        self.historyDbInfo['time_played'] = ultp
        self.historyDbInfo['date_played'] = ultp.date()
        self.historyDbInfo['true_score'] = sql_args.get('true_score')
        self.historyDbInfo['rating'] = sql_args.get('rating')
        self.historyDbInfo['score'] = sql_args.get('score')
        self.save()
