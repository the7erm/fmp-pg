
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from user_file_class import UserFile
from utils import convert_to_dt
from copy import deepcopy

from log_class import Log, logging
logger = logging.getLogger(__name__)

from misc import format_sql
import sqlparse

class UserFileInfo(UserFile, Log):
    __name__ = 'UserFileInfo'
    logger = logger
    def __init__(self, *args, **kwargs):
        super(UserFileInfo, self).__init__(*args, **kwargs)
        self.log_debug(".__init__() user:%(uname)s fid:%(fid)s" % 
                     kwargs)

    @property
    def rating(self):
        # UserFileInfo.rating
        return self.userFileDbInfo.get('rating', 6)

    @rating.setter
    def rating(self, value):
        # UserFileInfo.rating

        logger.debug("UserFileInfo.rating user:%(uname)s fid:%(fid)s" % 
                     kwargs)
        value = int(value)
        if value > -1 and value < 6 and value != self.rating:
            self.userFileDbInfo['rating'] = value
            self.save()

    @property
    def percent_played(self):
        # UserFileInfo.percent_played
        return self.userFileDbInfo.get('percent_played', 50)

    @percent_played.setter
    def percent_played(self, value):
        # UserFileInfo.percent_played
        value = float(value)
        if value > 0 and value < 100 and value != self.percent_played:
            self.userFileDbInfo['percent_played'] = value
            self.save()

    def inc_score(self, *args, **kwargs):
        # UserFileInfo.inc_score
        self.score = self.score + 1

    def deinc_score(self, *args, **kwargs):
        # UserFileInfo.inc_score
        self.score = self.score - 1

    @property
    def score(self):
        # UserFileInfo.score
        return self.userFileDbInfo.get('score', 5)

    @score.setter
    def score(self, value):
        # UserFileInfo.score
        value = int(value)
        if value != self.score and value <= 15 and value >= -15:
            self.userFileDbInfo['score'] = value
            self.save()

    def save(self):
        # UserFileInfo.save
        updated = self.save_user()
        updated.update(self.save_user_file_info())
        return updated

    def save_user_file_info(self):
        # UserFileInfo.save_user_file_info
        self.calculate_true_score()
        sql = """UPDATE user_song_info
                 SET {sets}
                 WHERE {wheres}
                 RETURNING *"""
        sets = ['rating', 'score', 'percent_played', 'ultp', 'true_score']
        wheres = ['uid', 'fid']
        sql = format_sql(sql, self.userFileDbInfo, sets=sets, wheres=wheres)
        self.userFileDbInfo = get_assoc_dict(sql, self.userFileDbInfo)
        return self.userFileDbInfo

    def mark_as_played(self, **sql_args):
        # UserFileInfo.mark_as_played
        self.log_debug('.mark_as_played()')
        if self.userFileDbInfo == {}:
            self.load_user_file_db_info()

        self.userFileDbInfo['percent_played'] = sql_args.get('percent_played', 0)
        self.userFileDbInfo['ultp'] = self.get_now(**sql_args)
        res = self.save()
        self.most_recent_history_item.mark_as_played(**res)
        return res

    def mark_as_completed(self, **sql_args):
        # UserFileInfo.mark_as_completed
        if self.userFileDbInfo == {}:
            self.load_user_file_db_info()
        self.userFileDbInfo['percent_played'] = 100
        self.userFileDbInfo['ultp'] = self.get_now(**sql_args)
        self.inc_score()
        res = self.save()
        self.most_recent_history_item.mark_as_completed(**res)
        return res

    def load_user_file_db_info(self):
        # UserFileInfo.load_user_file_db_info
        sql_args = {
            'uid': self.uid,
            'fid': self.fid
        }
        sql = """SELECT *
                 FROM user_song_info
                 WHERE uid = %(uid)s AND
                       fid = %(fid)s
                 LIMIT 1"""
        self.userFileDbInfo = get_assoc_dict(sql, sql_args)


class UserNetcastInfo(UserFileInfo):
    __name__ = 'UserNetcastInfo'
    logger = logger

    def __init__(self, **kwargs):
        super(UserNetcastInfo, self).__init__(*args, **kwargs)
        self.netcastInfo = kwargs.get('netcastInfo', {})
        self.episodeInfo = kwargs.get('episodeInfo', {})
        self.subscriptionInfo = kwargs.get('subscriptionInfo', {})
        self.load_user_file_db_info()

    @property
    def nid(self):
        # UserNetcastInfo.nid
        return self.episodeInfo.get('nid',
                    self.netcastInfo.get('nid',
                        self.subscriptionInfo.get('nid',
                            self.kwargs.get('nid'))))

    def load_episode(self):
        # UserNetcastInfo.load_episode
        if self.eid == self.episodeInfo.get('eid'):
            return
        sql = """SELECT *
                 FROM netcast_episodes ne,
                 WHERE eid = %(eid)s
                 LIMIT 1"""
        sql_args = {
            'eid': self.eid
        }
        self.episodeInfo = get_assoc_dict(sql, sql_args)

    def load_subscription(self):
        # UserNetcastInfo.load_subscription
        sql = """SELECT *
                 FROM netcast_subscribers
                 WHERE uid = %(uid)s AND
                       nid = %(nid)s
                 LIMIT 1"""
        sql_args = {
            'nid': self.nid,
            'uid': self.uid
        }
        self.subscriptionInfo = get_assoc_dict(sql, sql_args)

    def load_listened(self):
        # UserNetcastInfo.load_listened
        sql = """SELECT *
                 FROM netcast_listend_episodes
                 WHERE uid = %(uid)s AND
                       nid = %(eid)s"""
        sql_args = {
            'eid': self.eid,
            'uid': self.uid
        }
        self.listenedInfo = get_assoc_dict(sql, sql_args)

    @property
    def subscribed(self):
        # UserNetcastInfo.subscribed
        return self.subscriptionInfo != {}

    @subscribed.setter
    def subscribed(self, value):
        # UserNetcastInfo.subscribed
        value = bool(value)

        sql_args = {
            'nid': self.nid,
            'uid': self.uid
        }

        subscribed = self.subscribed
        
        if value and not subscribed:
            sql = """INSERT INTO netcast_subscribers (uid, nid)
                     VALUES(%(uid)s, %(nid)s)
                     RETURNING *"""
            self.subscriptionInfo = get_assoc_dict(sql, sql_args)
        elif not value and subscribed:
            sql = """DELETE FROM netcast_subscribers 
                     WHERE uid = %(uid)s AND
                           nid = %(nid)s"""
            query(sql, sql_args)
            self.subscriptionInfo = {}

    @property
    def listened(self):
        # UserNetcastInfo.listened
        return self.listenedInfo != {}

    @listened.setter
    def listened(self, value):
        # UserNetcastInfo.listened
        value = bool(value)
        listened = self.listened
        if value == listened:
            return

        sql_args = {
            'uid': self.uid,
            'eid': self.eid,
            'percent_played': 0
        }
        if value and not listened:
            sql = """INSERT INTO netcast_listened (eid, uid, percent_played)
                     VALUES(%(eid)s, %(uid)s, %(percent_played)s)"""
        elif not value and listened:
            sql = """DELETE FROM netcast_listened
                     WHERE eid = %(eid)s AND
                           uid = %(uid)s"""

        self.listenedInfo = get_assoc_dict(sql, sql_args)

    @property
    def percent_played(self):
        # UserNetcastInfo.percent_played
        return self.listenedInfo.get('percent_played', 0)

    @percent_played.setter
    def percent_played(self, value):
        # UserNetcastInfo.percent_played
        value = float(value)
        if not self.listened:
            self.listened = True
        self.listenedInfo['percent_played']  = value
        self.save()

    def load_user_file_db_info(self):
        # UserNetcastInfo.load_user_file_db_info
        self.load_netcast()
        self.load_episode()
        self.load_subscription()
        self.load_listened()

    def mark_as_played(self, **sql_args):
        # UserNetcastInfo.mark_as_played
        self.listened = True
        self.percent_played = sql_args.get('percent_played', 0)
        self.most_recent_history_item.mark_as_played(**sql_args)
        return self.save()

    def mark_as_completed(self, **sql_args):
        # UserNetcastInfo.mark_as_completed()
        sql_args['percent_played'] = 100
        return self.mark_as_played(**sql_args)


    def save_listened(self):
        # UserNetcastInfo.save_listened()
        sql = """UPDATE netcast_listened
                 SET percent_played = %(percent_played)s
                 WHERE uid = %(uid)s AND eid = %(eid)s
                 RETURNING *"""

        self.listenedInfo = get_assoc_dict(sql, self.listenedInfo)


    def save_subscribed(self):
        # UserNetcastInfo.save_subscribed
        # Not handled here.
        # Send bool value to self.subscribed = True/False
        return self.subscriptionInfo

    def save_user_file_info(self):
        # UserNetcastInfo.save_user_file_info
        updated = deepcopy(self.episodeInfo)
        updated = deepcopy(self.netcastInfo)
        updated.update(self.save_listened())
        updated.update(self.subscriptionInfo)
        return self.updated
