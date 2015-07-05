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
                 date_played_info_for_uid, get_most_recent_for_uid
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
        return None

    @property
    def eid(self):
        # UserFile.eid
        if hasattr(self.parent, 'eid'):
            return self.parent.eid
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
        
        sql = """SELECT * 
                 FROM
                 user_history
                 WHERE uid = %(uid)s AND
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
        # UserFile.most_recent_history_item
        # We only need to get the most recent once a minute.
        if self.most_recent and self.most_recent_expire > utcnow():
            return self.most_recent
        self.most_recent_expire = utcnow() + timedelta(minutes=1)
        most_recent_item = None
        if not self.history:
            self.most_recent = UserHistoryItem(parent=self.parent,
                **self.kwargs)
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
        # UserFile.get_now
        return sql_args.get('ltp', 
                                sql_args.get('now', utcnow())
                           )

    def calculate_true_score(self):
        # UserFile.calculate_true_score
        self.userFileDbInfo['true_score'] = (
            (self.rating * 2 * 10) + 
            (self.score * 10)
        ) / 2.0


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
        sql = """SELECT *
                 FROM user_history
                 WHERE uhid = %(uhid)s"""
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
        return self.uhid or (self.uid and (self.fid or self.eid))

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
        if 'uid' not in self.historyDbInfo:
            self.log_error(".historyDbInfo missing uid"+("<"*20))
            return
        user_history_sanity_check()
        sql_args = deepcopy(self.historyDbInfo)
        # This one makes sure it hasn't been played today.
        fid_query, eid_query = self.get_history_query(**sql_args)

        sql = """SELECT *
                 FROM user_history
                 WHERE uid = %(uid)s AND
                       {fid_query} AND
                       {eid_query} AND
                       date_played = %(date_played)s
                 LIMIT 1""".format(fid_query=fid_query,
                                   eid_query=eid_query)
        
        historyDbInfo = get_assoc_dict(sql, sql_args)
        if historyDbInfo != {}:
            self.historyDbInfo = historyDbInfo
        self.log_debug("/.load_from_uid_fid_eid_date_played()")
        self.historyDbInfo_sanity_check()

    def historyDbInfo_sanity_check(self):
        check_keys = ['uid', 'eid', 'fid', 'date_played',
                      'time_played', 'rating', 'score', 
                      'reason', 'true_score']

        for key in check_keys:
            if key not in self.historyDbInfo and key in self.kwargs:
                self.historyDbInfo[key] = self.kwargs[key]
                self.log_error(".historyDbInfo missing %s"+("<"*20), key)
                self.log_error("using self.kwargs:%s", self.kwargs[key])

        for key in check_keys:
            if key not in self.historyDbInfo and \
               key in self.kwargs['userDbInfo']:
                self.historyDbInfo[key] = self.kwargs['userDbInfo'][key]
                self.log_error(".historyDbInfo missing %s"+("<"*20), key)
                self.log_error("using self.kwargs['userDbInfo']:%s", 
                    self.kwargs[key])

        if 'eid' not in self.historyDbInfo:
            self.historyDbInfo['eid'] = None

        if 'fid' not in self.historyDbInfo:
            self.historyDbInfo['fid'] = None
        
        for key in check_keys:
            if key not in self.historyDbInfo:
                self.log_error(".historyDbInfo missing %s"+("<"*20), key)

    def insert(self):
        if not self.can_save:
            return

        self.historyDbInfo_sanity_check()

        if self.uhid:
            self.save()
            return

        sql = """INSERT INTO user_history (uid, eid, fid, date_played,
                                           time_played, rating, score, 
                                           reason, true_score)
                 VALUES (%(uid)s, %(eid)s, %(fid)s, %(date_played)s,
                         %(time_played)s, %(rating)s,%(score)s,
                         %(reason)s, %(true_score)s)
                 RETURNING *"""
        # You need to figure out how to handle eid vs fid updates
        # In particular how netcast vs local files.
        # how would we get them to use this class.
        self.historyDbInfo = get_assoc_dict(sql, self.historyDbInfo)

    def load_user_file_db_info(self):
        self.load_from_uid_fid_eid_date_played()

    def save(self):
        self.historyDbInfo_sanity_check()
        if not self.can_save:
            self.log_warn("Can't save")
            return

        if not self.uhid:
            self.load_from_uid_fid_eid_date_played()

        if not self.uhid:
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
        self.historyDbInfo = get_assoc_dict(sql, self.historyDbInfo)
        

    def mark_as_played(self, **sql_args):
        self.log_debug(".mark_as_played:%s", sql_args['percent_played'])
        self.historyDbInfo['percent_played'] = sql_args.get('percent_played', 0)
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
