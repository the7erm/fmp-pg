from fobj_class import FObj_Class
import os
import sys
from datetime import datetime, timedelta
from time import localtime, time, timezone
from pprint import pprint
import urllib
import urllib2
import feedparser
import socket
import pytz
import subprocess
from log_class import Log, logging
import re
logger = logging.getLogger(__name__)

USER_AGENT = "Family Media Player"

print "IMPORTED netcast_episode_class.py"
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

import config
from local_fobj_class import Listeners
from misc import _listeners, get_unlistend_episode, get_expired_netcasts
from episode_downloader import downloader
from utils import utcnow

class Netcast_Listeners(Listeners, Log):
    __name__ = 'Netcast_Listeners'
    logger = logger
    def __init__(self, *args, **kwargs):
        print "Netcast_Listeners.init()"
        self.kwargs = kwargs
        self.listeners = _listeners(kwargs.get('listeners', None))
        self.parent = kwargs.get('parent')
        super(Netcast_Listeners, self).__init__(*args, **kwargs)

    def init_mark_as_played_sql_args(self, sql_args):
        ultp = sql_args.get('ltp', 
                            sql_args.get('now', utcnow())
                         )
        sql_args.update({
            'ultp': ultp,
            'time_played': ultp,
            'date_played': ultp.date(),
            'eid': self.parent.eid,
            'fid': None
        })

    def mark_as_played_for_listener(self, **sql_args):
        self.log_debug(".mark_as_played_for_listener()")
        self.mark_episode_as_played_listened(**sql_args)
        self.update_most_recent(**sql_args)
        self.log_debug("MADE IT PAST")

    def mark_episode_as_played_listened(self, **sql_args):
        sql = """SELECT * 
                 FROM netcast_listend_episodes
                 WHERE uid = %(uid)s AND
                       eid = %(eid)s"""
        present = get_assoc_dict(sql, sql_args)
        if not present:
            sql = """INSERT INTO netcast_listend_episodes (uid, eid, 
                                                           percent_played)
                     VALUES (%(uid)s, %(eid)s, %(percent_played)s)"""
            query(sql, sql_args)
        else:
            sql = """UPDATE netcast_listend_episodes
                     SET percent_played = %(percent_played)s
                     WHERE uid = %(uid)s AND eid = %(eid)s"""
            query(sql, sql_args)

    def calculate_true_score(self, *args, **sql_args):
        return {}

    def inc_score(self, **sql_args):
        return {}

    def deinc_score(self, **sql_args):
        return {}

class Netcast_FObj(FObj_Class, Log):
    __name__ = 'Netcast_FObj'
    logger = logger
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.dbInfo = {}
        self.listeners = Netcast_Listeners(parent=self, **kwargs)
        self.real_filename = kwargs.get('filename', "")
        self.insert_new = kwargs.get("insert", False)
        self.eid = kwargs.get("eid", None)
        if 'eid' not in kwargs and kwargs.get('id_type') == 'e':
            self.eid = kwargs.get('id')
        self.filename = kwargs.get('filename', "")
        self.local_file = kwargs.get('local_file', "")
        self.episode_url = kwargs.get("episode_url", "")
        super(Netcast_FObj, self).__init__(*args, **kwargs)
        if self.dbInfo == {}:
            self.insert()
        
    def mark_as_played(self, **sql_args):
        self.listeners.mark_as_played(**sql_args)

    def clean(self):
        self.dbInfo = {}

    @property
    def filename(self):
        local_file = self.dbInfo.get("local_file")
        if local_file and os.path.exists(local_file):
            return local_file
        return self.dbInfo.get("episode_url", self.real_filename)

    @filename.setter
    def filename(self, value):
        if os.path.exists(value):
            self.local_file = value

    @property
    def local_file(self):
        return self.dbInfo.get("local_file")

    @local_file.setter
    def local_file(self, value):
        if self.local_file != value:
            self.load_from_local_file(value)

    def load_from_local_file(self, local_file):
        if not local_file:
            return
        sql = """SELECT *
                 FROM netcast_episodes
                 WHERE local_file = %(local_file)s
                 LIMIT 1"""
        self.dbInfo = get_assoc_dict(sql, {'local_file': local_file})

    @property
    def eid(self):
        return self.dbInfo.get('eid')

    @eid.setter
    def eid(self, value):
        self_eid = self.eid
        if self_eid != value:
            self.load_from_eid(value)

    @property
    def fid(self):
        return None

    def load_from_eid(self, eid):
        if not eid:
            return
        sql = """SELECT *
                 FROM netcast_episodes
                 WHERE eid = %(eid)s"""
        self.dbInfo = get_assoc_dict(sql, {'eid': eid})

    @property
    def episode_url(self):
        return self.dbInfo.get("episode_url")

    @episode_url.setter
    def episode_url(self, value):
        self_episode_url = self.episode_url
        if self_episode_url != value:
            self.load_from_episode_url(value)

    def load_from_episode_url(self, episode_url):
        if not episode_url:
            return
        sql = """SELECT *
                 FROM netcast_episodes
                 WHERE episode_url = %(episode_url)s"""
        dbInfo = get_assoc_dict(sql, {'episode_url': episode_url})
        if not dbInfo:
            self.insert()

        self.dbInfo = dbInfo
            

    def get_eid_from_dict(self, _dict):
        eid = _dict.get('eid')
        if eid is not None:
            return eid
        id_type = _dict.get('id_type')
        _id = _dict.get("id")
        if id_type == 'e' and _id:
            return _id
        return None

    def insert(self):
        if not self.insert_new:
            return
        # make sure insert is called only once
        self.insert_new = False

        eid = self.get_eid_from_dict(self.kwargs)

        if eid is not None:
            # Double check it's not in the database already
            self.load_from_eid(eid)
            if self.dbInfo != {}:
                self.save()
                return

        self.dbInfo['eid'] = eid
        self.dbInfo['nid'] = self.kwargs.get('nid')
        self.dbInfo['episode_title'] = self.kwargs.get('episode_title')
        self.dbInfo['episode_url'] = self.kwargs.get('episode_url')
        
        local_file = self.kwargs.get("local_file")
        if local_file is None:
            basename = os.path.basename(self.dbInfo['episode_url'])
            local_file = os.path.join(config.cache_dir, basename)

        self.dbInfo['local_file'] = local_file
        self.dbInfo['pub_date'] = self.kwargs.get('pub_date')
        

        sql = """INSERT INTO netcast_episodes (episode_title, episode_url,
                                               nid, local_file, pub_date)
                 VALUES(%(episode_title)s, %(episode_url)s, 
                        %(nid)s, %(local_file)s, %(pub_date)s)
                 RETURNING *"""

        self.log_debug("INSERT:%s" % self.dbInfo)
        self.dbInfo = get_assoc_dict(sql, self.dbInfo)
        self.log_debug("RESULT:%s" % self.dbInfo)

    def save(self):
        eid = self.eid
        if eid is None:
            eid = self.get_eid_from_dict(self.kwargs)
            if eid is None:
                self.insert()
            return

        self.dbInfo['eid'] = eid
        sql = """UPDATE netcast_episodes 
                 SET episode_title = %(episode_title)s,
                     episode_url = %(episode_url)s,
                     local_file = %(local_file)s,
                     nid = %(nid)s
                 WHERE eid = %(eid)s
                 RETURNING *"""
        print "SAVE:", self.dbInfo
        self.dbInfo = get_assoc_dict(sql, self.dbInfo)

    def inc_score(self, **sql_args):
        return {}

    def deinc_score(self, **sql_args):
        return {}

class Netcast(Log):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.dbInfo = {}
        self.nid = kwargs.get('nid')
        self.netcast_name = kwargs.get('netcast_name')
        self.rss_url = kwargs.get('rss_url')
        self.episodes = []
        self.refresh_feed_and_download_episodes()

    def refresh_feed_and_download_episodes(self):
        if self.time_for_update:
            print "updating:", self.dbInfo.get('rss_url')
            self.refresh_feed()
            self.download_unlistened_netcasts()

    @property
    def is_expired(self):
        expire_time = self.dbInfo.get('expire_time')
        if not expire_time:
            return True
        return utcnow() > expire_time

    @property
    def time_for_update(self):
        if self.too_soon_to_refresh:
            return False
        return self.is_expired

    @property
    def too_soon_to_refresh(self):
        last_updated = self.dbInfo.get('last_updated')
        if not last_updated:
            return False
        min_dt = utcnow() - timedelta(minutes=30)
        return last_updated > min_dt

    @property
    def nid(self):
        return self.dbInfo.get('nid')

    @nid.setter
    def nid(self, value):
        if value != self.nid:
            self.load_from_nid(value)

    @property
    def rss_url(self):
        return self.dbInfo.get('rss_url')

    @rss_url.setter
    def rss_url(self, value):
        if value != self.rss_url:
            self.load_from_rss_url(value)
    
    @property
    def rss_feed_cache_file(self):
        return os.path.join(config.feed_cache_dir,
                            safe_filename(self.rss_url))

    @property
    def netcast_name(self):
        return self.dbInfo.get('netcast_name')

    @netcast_name.setter
    def netcast_name(self, value):
        if value != self.netcast_name:
            self.load_from_netcast_name(value)

    def load_from_nid(self, nid):
        if not nid:
            return
        sql = """SELECT *
                 FROM netcasts
                 WHERE nid = %(nid)s
                 LIMIT 1"""
        self.dbInfo = get_assoc_dict(sql, {"nid": nid})

    def load_from_rss_url(self, rss_url):
        if not rss_url:
            return
        sql = """SELECT *
                 FROM netcasts
                 WHERE rss_url = %(rss_url)s
                 LIMIT 1"""
        self.dbInfo = get_assoc_dict(sql, {"rss_url": rss_url})

    def load_from_netcast_name(self, netcast_name):
        if not netcast_name:
            return
        sql = """SELECT *
                 FROM netcasts
                 WHERE netcast_name = %(netcast_name)s
                 LIMIT 1"""
        self.dbInfo = get_assoc_dict(sql, {"netcast_name": netcast_name})

    def download_feed(self):
        if os.path.exists(self.rss_feed_cache_file):
            mtime = os.path.getmtime(self.rss_feed_cache_file)
            now = time()
            self.log_debug("now:%s now:%s mtime:%s  mtime:%s" % (
                now, datetime.fromtimestamp(now), mtime, 
                datetime.fromtimestamp(mtime)
            ))
            if mtime > now - (60 * 30):
                self.log_debug("USING CACHE")
                fp = open(self.rss_feed_cache_file, 'r')
                xml = fp.read()
                fp.close()
                return xml

        headers = { 'User-Agent' : USER_AGENT }
        try:
            req = urllib2.Request(self.rss_url, headers=headers)
            response = urllib2.urlopen(req)
            xml = response.read()
            fp = open(self.rss_feed_cache_file, 'w')
            fp.write(xml)
            fp.close()
        except Exception, e:
            print "Exception:", e
        return ""

    def refresh_feed(self):
        #if self.too_soon_to_refresh:
        #   print "too_soon_to_refresh:", self.too_soon_to_refresh
        #   return
        print "Netcast dbInfo:", self.dbInfo
        socket.setdefaulttimeout(30)
        print "refreshing:", self.rss_url

        try:
            feed = feedparser.parse(self.download_feed())
        except socket.error, msg:
            self.set_update_for_near_future()
            self.emit('update-error', msg)
            return
        title = feed.get('feed',{}).get('title',  "")
        if not title:
            self.log_debug("NO TITLE")
            self.set_update_for_near_future()
            return

        self.dbInfo['netcast_name'] = title
        if not feed.get('entries'):
            self.set_update_for_near_future()
            return

        self.process_entries(feed['entries'])
        self.mark_updated()

    def process_entries(self, entries):
        for i, entry in enumerate(entries):
            if not entry.has_key('enclosures'):
                continue
            if len(entry['enclosures']) == 0:
                continue
            print "==================="
            for enclosure in entry['enclosures']:
                self.process_enclosure(entry, enclosure)
            print "==================="

    def process_enclosure(self, entry, enclosure):
        print "---------------------"
        pprint(enclosure)
        pub_date = datetime(*entry['updated_parsed'][0:7])
        
        episode = Netcast_FObj(nid=self.nid, 
                               episode_title=entry['title'],
                               episode_url=enclosure['href'],
                               pub_date=pub_date,
                               insert=True)

        self.episodes.append(episode)
        
        print "---------------------"

    def set_update_for_near_future(self):
        sql = """UPDATE netcasts 
                 SET expire_time = (current_timestamp + interval '1 hour') 
                 WHERE nid = %(nid)s
                 RETURNING *"""
        self.dbInfo = get_assoc_dict(sql, {'nid': self.nid })

    def mark_updated(self):
        sql = """UPDATE netcasts 
                 SET expire_time = (current_timestamp + interval '1 day'),
                     last_updated = current_timestamp,
                     netcast_name = %(netcast_name)s,
                     rss_url = %(rss_url)s
                 WHERE nid = %(nid)s
                 RETURNING *"""
        print "mark_updated"
        pprint(self.dbInfo)
        self.dbInfo = get_assoc_dict(sql, self.dbInfo)

    def get_unlistened_episodes(self):
        sql = """SELECT n.*, ne.*, nl.*, u.* 
                 FROM netcasts n, netcast_episodes ne 
                      LEFT JOIN netcast_listend_episodes nl ON 
                                nl.eid = ne.eid, users u, 
                                netcast_subscribers ns 
                 WHERE ne.nid = n.nid AND listening = true AND 
                       ns.uid = u.uid AND ns.nid = n.nid AND 
                       nl.uid IS NULL AND ns.nid = %(nid)s 
                 ORDER BY pub_date"""
        return get_results_assoc_dict(sql, self.dbInfo)

    def download_unlistened_netcasts(self):
        unlistened_episodes = self.get_unlistened_episodes()
        for e in unlistened_episodes:
            if not os.path.exists(e['local_file']):
                print "******"
                print "not exists: e['local_file']:", e['local_file']
                # downloader.append(e['episode_url'], e['local_file'])
                subprocess.Popen(['wget', '-c', e['episode_url'], '-O', 
                                  e['local_file']])

    def save(self):
        sql = """UPDATE netcasts
                 SET netcast_name = %(netcast_name)s,
                     rss_url = %(rss_url)s
                 WHERE nid = %(nid)s"""
        self.dbInfo = get_assoc_dict(sql, self.dbInfo)


def refresh_and_download_all_netcasts():
    logger.debug("REFRESHING AND DOWNLOADING ALL NETCASTS")
    
    sql = """SELECT * 
             FROM netcasts"""
    netcasts = get_results_assoc_dict(sql)
    for n in netcasts:
        obj = Netcast(**n)
        obj.refresh_feed_and_download_episodes()

def refresh_and_download_expired_netcasts():
    # wait()
    logger.debug("REFRESHING AND DOWNLOADING EXPIRED NETCASTS")
    netcasts = get_expired_netcasts()
    for n in netcasts:
        # wait()
        obj = Netcast(**n)
        obj.refresh_feed_and_download_episodes()

def safe_filename(filename):
    if not filename:
        return ""
    return re.sub('(\W+)', "-", filename)

if __name__ == "__main__":
    from time import sleep
    refresh_and_download_all_netcasts()
    while True:
        print "SLEEP"
        sleep(1)
