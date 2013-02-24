#!/usr/bin/env python
# -*- coding: utf-8 -*-
# netcast_fobj.py -- Netcast file obj
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

from __init__ import *
from listeners import listeners
import fobj
import os
import gobject
import feedparser
import socket
import urllib
import pprint
import datetime
from datetime import date
import pytz
from episode_downloader import downloader


from excemptions import CreationFailed

pp = pprint.PrettyPrinter(depth=6)

class myURLOpener(urllib.FancyURLopener):
    """Create sub-class in order to overide error 206.  This error means a
       partial file is being sent,
       which is ok in this case.  Do nothing with this error.
    """
    def __init__(self, *args):
        self.version = "Family Media Player - PostgreSQL version"
        urllib.FancyURLopener.__init__(self, *args)

    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        print "206 url:",url
        print "fp: ",fp
        print "errorcode:",errcode
        print "errmsg:",errmsg
        print "headers:",headers
        print "data:",data
        pass


class Netcast(gobject.GObject):
    __gsignals__ = {
        'updating': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'update-error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                         (gobject.TYPE_PYOBJECT,)),

        'done-updating': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                          (gobject.TYPE_PYOBJECT,)),

        'download-status': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                            (gobject.TYPE_PYOBJECT,)),

        'download-done': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                          (gobject.TYPE_PYOBJECT,)),

        'update-entry': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                         (gobject.TYPE_PYOBJECT,)),
    }

    def __init__(self, nid=None, rss_url=None, insert=False, **kwargs):
        gobject.GObject.__init__(self)

        self.db_info = None
        self.episodes = []
        self.expire_time = None
        self.nid = None
        self.rss_url = None
        self.name = None
        self.expire_time = None

        if nid is not None:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcasts 
                                        WHERE nid = %s 
                                        LIMIT 1""", (nid,))

        if rss_url is not None and not self.db_info:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcasts 
                                        WHERE rss_url = %s 
                                        LIMIT 1""", (rss_url,))

        if not self.db_info and not insert:
            raise CreationFailed("Unable to associate netcast:\n"+
                                  "\tnid:%s rss_url:%s\n" % (nid, rss_url))

        elif not self.db_info and insert:
            if rss_url:
                self.insert_netcast(rss_url=rss_url)
            else:
                raise CreationFailed("Unable to insert rss feed.  No rss_url given.")

        self.set_attribs()

    def set_attribs(self):
        if self.db_info:
            self.nid = self.db_info['nid']
            self.rss_url = self.db_info['rss_url']
            self.name = self.db_info['netcast_name']
            self.expire_time = self.db_info['expire_time']

    def insert_netcast(self, rss_url):
        self.rss_url = rss_url
        if rss_url is not None:
            self.db_info = get_assoc("""INSERT INTO netcasts (rss_url)
                                        VALUES(%s) 
                                        RETURNING *""", (rss_url,))
            self.set_attribs()

        self.update()

    def update(self, force=False):
        if self.expire_time:
            now = datetime.datetime.now(self.expire_time.tzinfo)
            if not force:
                print "EXPIRES:", self.expire_time
                print type(self.expire_time)
                if now <= self.expire_time:
                    print "now (",now,") <= (",self.expire_time,") expire_time"
                    print "not updating"
                    return
            print "now (",now,") > (",self.expire_time,") expire_time"
        print "updating"

        socket.setdefaulttimeout(30)
        self.emit('updating')
        try:
            feed = feedparser.parse(self.rss_url)
        except socket.error, msg:
            self.set_update_for_near_future()
            self.emit('update-error', msg)
            return

        if not feed.feed.has_key('title'):
            self.set_update_for_near_future()
            self.emit('update-error', "The netcast url %s " % (self.rss_url,) +
                      "doesn't have a title")
            return
        # SELECT current_timestamp AS "now", current_timestamp + interval 
        #        '1 day' as "1 day from now";
        query("""UPDATE netcasts 
                 SET expire_time = (current_timestamp + interval '1 day') 
                 WHERE nid = %s""", (self.nid,))

        query("""UPDATE netcasts 
                 SET netcast_name = %s 
                 WHERE nid = %s""", 
                 (feed['feed']['title'].encode("utf-8"), self.nid))

        print self.db_info
        for i, entry in enumerate(feed['entries']):
            if not entry.has_key('enclosures'):
                continue
            if len(entry['enclosures']) == 0:
                continue
            print "==================="
            pp.pprint(entry)
            for enclosure in entry['enclosures']:
                print "---------------------"
                pp.pprint(enclosure)
                pub_date = datetime.datetime(*entry['updated_parsed'][0:7])
                try:
                    episode = Netcast_File(netcast=self, 
                                           episode_title=entry['title'],
                                           episode_url=enclosure['href'],
                                           pub_date=pub_date,
                                           insert=True)

                    self.episodes.append(episode)
                except CreationFailed, e:
                    print "CreationFailed:",e
                print "---------------------"
            print "==================="

        query("""UPDATE netcasts 
                 SET last_updated = NOW() 
                 WHERE nid = %s""", 
                 (self.nid,))

    def update_episode(self, episode_url, episode_title):
        return Netcast_File(episode_url=episode_url, 
                            episode_title=episode_title, netcast=self,
                            insert=True)

    def set_update_for_near_future(self):
        query("""UPDATE netcasts 
                 SET expire_time = (current_timestamp + interval '1 hour') 
                 WHERE nid = %s""",(self.nid,))

    def __str__(self):
        return "%s" % (self.db_info,)

    def __repr__(self):
        return pp.pformat(dict(self.db_info))

    def download_unlistened_netcasts(self):
        unlistened_episodes = self.get_unlistened_episodes()
        for e in unlistened_episodes:
            if not os.path.exists(e['local_file']):
                downloader.append(e['episode_url'], e['local_file'])


    def get_unlistened_episodes(self):
        return get_results_assoc("""SELECT n.*, ne.*, nl.*, u.* 
                                    FROM netcasts n, netcast_episodes ne 
                                         LEFT JOIN netcast_listend_episodes nl ON 
                                                   nl.eid = ne.eid, users u, 
                                                   netcast_subscribers ns 
                                    WHERE ne.nid = n.nid AND listening = true AND 
                                          ns.uid = u.uid AND ns.nid = n.nid AND 
                                          nl.uid IS NULL AND ns.nid = %s 
                                    ORDER BY pub_date""", (self.nid,))


class Netcast_File(fobj.FObj):
    def __init__(self, filename=None, dirname=None, basename=None, eid=None,
                 episode_url=None, local_filename=None, nid=None, rss_url=None,
                 episode_title=None, netcast=None, fuzzy=False, insert=False,
                 pub_date=None, **kwargs):
        self.can_rate = False
        self.netcast = netcast
        self.db_info = None
        self.nid = nid
        self.eid = eid
        self.title = episode_title
        self.url = episode_url
        self.local_file = local_filename
        self.pub_date = pub_date
        

        if self.netcast is None and (nid is not None or rss_url is not None):
            self.netcast = Netcast(nid=nid, rss_url=rss_url, insert=False)

        self.set_db_info_by_nid_eid(eid)
        self.set_db_info_by_episode_url(episode_url)
        self.set_db_info_by_local_filename(local_filename)
        self.set_db_info_by_filename(filename)
        self.set_db_info_by_dirname_basename(dirname, basename)
        
        if fuzzy:
            self.set_db_info_by_like_episode_url(episode_url)
            self.set_db_info_by_like_local_filename(local_filename)
            self.set_db_info_by_like_filename(filename)
            self.set_db_info_by_like_basename(basename)

        self.set_netcast()

        if self.db_info:
            self.set_attribs()
            if os.path.exists(self.local_file):
                filename=self.local_file
            else:
                filename=self.url

        if filename:
            dirname=os.path.dirname(filename)
            basename=os.path.basename(filename)
        elif dirname and basename:
            filename=os.path.join(dirname, basename)
        elif episode_url:
            filename=episode_url
        elif local_filename:
            filename=local_filename
            print self.db_info

        fobj.FObj.__init__(self, filename=filename, dirname=dirname, 
                           basename=basename, **kwargs)

        if not self.db_info:
            if insert:
                self.insert(episode_title=episode_title, 
                            episode_url=episode_url, pub_date=pub_date)

                self.set_attribs()
            else:
                """
                filename=None, dirname=None, basename=None, eid=None, 
                episode_url=None, local_filename=None, nid=None, rss_url=None, 
                episode_title=None, netcast=None, fuzzy=False
                """
                raise CreationFailed(
                    "Unable to find netcast episode information based on:\n"+
                    "    eid:%s\n" % eid +
                    "    nid:%s\n" % nid +
                    "    filename:%s\n" % filename +
                    "    basename:%s\n" % basename +
                    "    dirname:%s\n" % dirname +
                    "    episode_url:%s\n" % episode_url +
                    "    netcast:%s\n" % netcast +
                    "    fuzzy:%s\n" % fuzzy
                )

    def set_db_info_by_nid_eid(self, eid=None):
        if self.db_info or not eid:
            return

        self.db_info = get_assoc("SELECT * FROM netcast_episodes WHERE eid = %s",(eid,))
        

    def set_db_info_by_episode_url(self, episode_url=None):
        if self.db_info or not episode_url:
            return

        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND episode_url = %s 
                                        LIMIT 1""", 
                                        (self.netcast.nid, episode_url))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE episode_url = %s LIMIT 1""",
                                        (episode_url,))

    def set_db_info_by_local_filename(self, local_filename=None):
        if self.db_info or not local_filename:
            return

        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND local_file = %s 
                                        LIMIT 1""",
                                        (self.netcast.nid, local_filename))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE local_file = %s 
                                        LIMIT 1""",
                                        (local_filename,))

    def set_db_info_by_filename(self, filename=None):
        if self.db_info or not filename:
            return

        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND (local_file = %s OR
                                                            episode_url = %s)
                                        LIMIT 1""", 
                                        (self.netcast.nid, filename, filename))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE local_file = %s OR 
                                              episode_url = %s 
                                        LIMIT 1""", 
                                        (filename, filename))

        if not self.db_info:
            filename = self.get_local_filename(filename)
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE local_file = %s OR 
                                              episode_url = %s 
                                        LIMIT 1""", 
                                        (filename, filename))

    def set_db_info_by_dirname_basename(self, dirname=None, basename=None):
        if self.db_info or not dirname or not basename:
            return

        filename = os.path.join(dirname, basename)
        self.set_db_info_by_filename(filename)

    def set_db_info_by_like_episode_url(self, episode_url=None):
        if self.db_info or not episode_url:
            return
        basename = os.path.basename(episode_url)
        like = "%%%s" % basename
        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND (episode_url LIKE %s) 
                                        LIMIT 1""",
                                        (self.netcast.nid, like))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE episode_url LIKE %s 
                                        LIMIT 1""",
                                        (like,))

    def set_db_info_by_like_local_filename(self, local_filename=None):
        if self.db_info or not local_filename:
            return
        basename = os.path.basename(local_filename)
        like = "%%%s" % basename
        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND local_file LIKE %s 
                                        LIMIT 1""", 
                                        (self.netcast.nid, like))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE local_file LIKE %s 
                                        LIMIT 1""",
                                        (like,))

    def set_db_info_by_like_filename(self, filename=None):
        if self.db_info or not filename:
            return
        basename = os.path.basename(filename)
        self.set_db_info_by_like_basename(basename)

    def set_db_info_by_like_basename(self, basename=None):
        if self.db_info or not basename:
            return
        like = "%%%s" % basename;
        if self.netcast:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE nid = %s AND (episode_url LIKE %s
                                                            OR local_file LIKE %s)
                                        LIMIT 1""",
                                        (self.netcast.nid, like, like))
        else:
            self.db_info = get_assoc("""SELECT * 
                                        FROM netcast_episodes 
                                        WHERE episode_url LIKE %s OR 
                                              local_file LIKE %s""", 
                                        (like, like))

    def set_netcast(self):
        if not self.netcast and self.db_info:
            self.netcast = Netcast(nid=self.db_info['nid'], insert=False)

    def get_local_filename(self, url=None, urldecode=False):
        if url is None:
            url = self.episode_url
            urldecode = True
        basename = os.path.basename(url)
        parts = basename.split('?')
        base = parts.pop(0)
        if urldecode:
            base = urllib.url2pathname(base)
        return os.path.join(cache_dir, base)

    def check_recently_played(self):
        print "****************************"
        print "Netcast_File:check_recently_played()"
        
        recently_played = fobj.recently_played(1)
        if not recently_played:
            return
        e = dict(recently_played[0])
        if not e.has_key('id_type') or not e.has_key('id') or \
           e['id_type'] != 'e' or e['id'] != self.eid:
            return
        print "INITAL E:",e
        today = date.today()
        if today.isoformat() == e['date_played'].isoformat():
            print today.isoformat(),"==",e['date_played'].isoformat()
            return
        print "******* DELETEING OLD RECORD DATE CHANGED *******"
        query("""DELETE FROM user_history 
                 WHERE uid IN (SELECT uid FROM users WHERE listening = true) AND
                       id_type = 'e' AND id = %s AND date_played = %s""", 
                 (self.eid, e['date_played'].isoformat()))

    def mark_as_played(self, percent_played=0):
        print "TODO: Necast_file::mark_as_played()"
        """nlid, uid, eid, percent_played"""
        print "percent_played:",percent_played

        updated = get_results_assoc("""UPDATE netcast_listend_episodes nle
                                       SET percent_played = %s
                                       WHERE uid IN (SELECT uid FROM users 
                                                     WHERE listening = true)
                                             AND eid = %s RETURNING *""",
                                       (percent_played, self.eid))
        print "updated:",updated

        for l in listeners.listeners:
            found = False
            for u in updated:
                if u['uid'] == l['uid']:
                    found = True

            if not found:
                inserted = get_results_assoc("""INSERT INTO 
                                                netcast_listend_episodes
                                                    (uid, eid, percent_played)
                                                VALUES(%s, %s, %s) RETURNING *""",
                                                (l['uid'], self.eid, 
                                                 percent_played))

        self.update_history(percent_played)

    def update_user_history(self):
        return get_results_assoc("""UPDATE user_history uh 
                                       SET percent_played = nle.percent_played, 
                                           time_played = NOW(), 
                                           date_played = current_date 
                                       FROM netcast_listend_episodes nle 
                                       WHERE 
                                            nle.uid IN (SELECT uid 
                                                        FROM users 
                                                        WHERE listening = true) AND 
                                            uh.uid = nle.uid AND 
                                            nle.eid = uh.id AND 
                                            uh.id_type = 'e' AND 
                                            uh.date_played = current_date AND 
                                            uh.id = %s 
                                       RETURNING uh.*""",
                                       (self.eid,))

    def insert_user_history(self, uid, percent_played=0):
        try:
            user_history = get_assoc("""INSERT INTO 
                                            user_history (uid, id, id_type,
                                                          percent_played, 
                                                          time_played,
                                                          date_played) 
                                        VALUES (%s, %s, %s, %s, NOW(), 
                                                current_date) 
                                        RETURNING *""",
                                        (uid, self.eid, 'e', 
                                         percent_played))

            updated_user = get_assoc("""UPDATE user_history uh
                                        SET percent_played = nle.percent_played, 
                                            time_played = NOW(),
                                            date_played = current_date 
                                        FROM netcast_listend_episodes nle
                                        WHERE nle.uid = %s AND
                                              uh.uid = nle.uid AND
                                              nle.eid = uh.id AND
                                              uh.id_type = 'e' AND
                                              uh.date_played = current_date AND 
                                              uh.id = %s RETURNING uh.*""", 
                                        (uid, self.eid))

            if updated_user:
                return updated_user

        except psycopg2.IntegrityError, err:
            query("COMMIT;")
            print "(file) psycopg2.IntegrityError:",err
        return None

    def update_history(self,percent_played=0):
        """nlid, uid, eid, percent_played"""
        self.check_recently_played()
        updated = self.update_user_history()
        for l in listeners.listeners:
            found = False
            for u in updated:
                if u['uid'] == l['uid']:
                    found = True
                    break;

            if not found:
                updated_user = self.insert_user_history(l['uid'], percent_played)
                if updated_user:
                    updated.append(updated_user)

    def deinc_score(self, *args, **kwargs):
        print "TODO: Netcast_File::deinc_score"

    def inc_score(self,*args,**kwargs):
        print "TODO: Netcast_File::inc_score"

    def insert(self, episode_title, episode_url, pub_date):
        if self.db_info:
            return
        episode_url = episode_url.replace("'","%27");
        local_file = self.get_local_filename(episode_url, urldecode=True)
        print "====[ Insert ]====="
        print "netcast:",self.netcast.name
        print "Title:",episode_title
        print "url:",episode_url
        print "local_file:",local_file
        print "pub_date:",pub_date

        self.db_info = get_assoc("""INSERT INTO netcast_episodes 
                                        (nid, episode_title, episode_url,
                                         local_file, pub_date)
                                    VALUES(%s, %s, %s, %s, %s) RETURNING *""",
                                    (self.netcast.nid, episode_title, 
                                     episode_url, local_file, pub_date))

        self.set_attribs()
        pp.pprint(dict(self.db_info))
        print "====[ /Insert ]====="

    def set_attribs(self):
        if self.db_info:
            self.nid = self.db_info['nid']
            self.eid = self.db_info['eid']
            self.title = self.db_info['episode_title']
            self.url = self.db_info['episode_url']
            self.local = self.local_file = self.db_info['local_file']
            self.pub_date = self.db_info['pub_date']

    def is_unlistened (self):
        return get_results_assoc("""SELECT n.*, ne.*, nl.*, u.* 
                                    FROM netcasts n, netcast_episodes ne 
                                         LEFT JOIN netcast_listend_episodes nl ON 
                                                   nl.eid = ne.eid, users u, 
                                                   netcast_subscribers ns
                                    WHERE ne.nid = n.nid AND listening = true AND 
                                          ns.uid = u.uid AND ns.nid = n.nid AND 
                                          nl.uid IS NULL AND ns.nid = %s AND
                                          ne.eid = %s
                                    ORDER BY pub_date""", (self.nid, self.eid))

    def get_artist_title(self):
        try:
            return "%s - %s" % (self.netcast.db_info['netcast_name'], self.db_info['episode_title'])
        except KeyError:
            pass

        self.get_tags()
        if self.tags_easy:
            if self.tags_easy['artist'] and self.tags_easy['title']:
                return "%s - %s" % (self.tags_easy['artist'][0], self.tags_easy['title'][0])

        return self.basename


def get_subscribed_netcasts():
    netcasts = get_results_assoc("""SELECT DISTINCT n.*
                                    FROM netcasts n, netcast_subscribers ns,
                                         users u
                                    WHERE ns.uid = u.uid AND
                                          u.listening = true AND
                                          ns.nid = n.nid
                                    ORDER BY netcast_name""")
    netcast_list = []
    for n in netcasts:
        netcast = Netcast(**n)
        netcast_list.append(netcast)

    return netcast_list

def get_expired_subscribed_netcasts():
    netcasts = get_results_assoc("""SELECT DISTINCT n.*
                                    FROM netcasts n, netcast_subscribers ns,
                                         users u
                                    WHERE ns.uid = u.uid AND
                                          u.listening = true AND
                                          ns.nid = n.nid AND 
                                          expire_time <= current_timestamp
                                    ORDER BY netcast_name""")
    netcast_list = []
    for n in netcasts:
        netcast = Netcast(**n)
        netcast_list.append(netcast)

    return netcast_list

def get_one_unlistened_episode():
    f = get_assoc("""SELECT n.*, ne.*, u.uname, u.uid
                     FROM netcasts n, netcast_episodes ne 
                          LEFT JOIN netcast_listend_episodes nl ON 
                                    nl.eid = ne.eid, 
                          users u, netcast_subscribers ns 
                     WHERE ne.nid = n.nid AND listening = true AND 
                           ns.uid = u.uid AND ns.nid = n.nid AND 
                           nl.uid IS NULL 
                     ORDER BY pub_date LIMIT 1""")
    if not f:
        return None
    
    return f


def update_now():
    query("""UPDATE netcasts 
             SET expire_time = NOW() 
             WHERE last_updated < current_timestamp - interval '30 min'""")


def is_netcast(obj):
    if obj is None:
        return False
    return isinstance(obj, Netcast_File) or \
           (obj.has_key('id_type') and obj['id_type'] == 'e') or \
           (obj.has_key('eid') and obj['eid']) or \
           (obj.has_key('rss_url') and obj['rss_url']) or \
           (obj.has_key('episode_url') and obj['episode_url'])


if __name__ == "__main__":
    feeds = [
        'http://music.the-erm.com/feed/',
        'http://feeds.feedburner.com/coderradiomp3?format=xml',
        'http://feeds.feedburner.com/TheLinuxActionShow?format=xml',
        'http://feeds.feedburner.com/techsnapmp3?format=xml',
        'http://leo.am/podcasts/sn',
        'http://leo.am/podcasts/twit',
        'http://leo.am/podcasts/tri',
        "http://www.oneplace.com/ministries/thru-the-bible-with-j-vernon-mcgee/subscribe/podcast.xml",
        "http://revision3.com/tekzilla/feed/MP4-Large?subshow=false"
    ]

    for url in feeds:
        try:
            netcast = Netcast(rss_url=url, insert=True)
            netcast.update()
        except CreationFailed, e:
            print "CreationFailed:", e
    
    
