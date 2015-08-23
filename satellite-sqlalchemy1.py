import os
import sys
import json
import urllib
import urllib2

os.chdir(sys.path[0])

from setproctitle import setproctitle
setproctitle(os.path.basename(sys.argv[0]))

from player1 import *

from sqlalchemy import Column, ForeignKey, Integer, String, DateTime, \
                       Boolean, Text, Float, Table, Date, desc, asc, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker, scoped_session, \
                           object_session, make_transient
from sqlalchemy.orm.exc import DetachedInstanceError
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy import create_engine

from pprint import pprint, pformat
from time import time, sleep, timezone, daylight, altzone
import shutil
from config_dir import config_dir
cache_dir = os.path.join(config_dir, 'satellite-cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

debug = True

def get_time(_time=None):
    local_offset = timezone
    if daylight:
        local_offset = altzone
    if not _time:
        _time = time()
    return _time + local_offset

def _print(*args, **kwargs):
    if not debug:
        sys.stdout.flush()
        return

    for arg in args:
        print arg,
    if kwargs != {}:
        print kwargs
    print
    sys.stdout.flush()

def _pprint(*args, **kwargs):
    if not debug:
        sys.stdout.flush()
        return
    pprint(*args, **kwargs)
    sys.stdout.flush()

def ssr(created, session):
    session.commit()

Base = declarative_base()

artist_association_table = Table('file_artists', Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('aid', Integer, ForeignKey('artists.aid'))
)

genre_association_table = Table('file_genres', Base.metadata,
    Column('fid', Integer, ForeignKey('files.fid')),
    Column('gid', Integer, ForeignKey('genres.gid'))
)

class myURLOpener(urllib.FancyURLopener):
    """Create sub-class in order to overide error 206.  This error means a
       partial file is being sent,
       which is ok in this case.  Do nothing with this error.
    """
    # http://code.activestate.com/recipes/83208-resuming-download-of-a-file/
    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        pass

class IpWatcher:
    def __init__(self):
        self.ips = []
        self.ip = None
        self.host = None

    def scan_ips(self):
        wait()
        ips = self.get_ips()

        if not ips:
            self.host = None
            self.ips = ips
            return

        if ips == self.ips:
            return

        session.query(Ip)\
               .update({Ip.is_current_ip: False})
        for local_ip in ips:
            self.add_ip(local_ip=local_ip)
        self.ips = ips
        _print("ips:",self.ips)
        self.ip = session.query(Ip)\
                         .filter(Ip.is_current_ip == True)\
                         .first()
        _print("self.ip:", self.ip)

    def add_ip(self, local_ip=None):

        wait()
        if (not local_ip.startswith("192.168.") and 
            not local_ip.startswith("10.") and
            not local_ip.startswith("172.")):
                return

        if local_ip.startswith("172."):
            is_172 = False
            for i in range(16, 32):
                if ip.startswith("172.%s." % i):
                    is_172 = True
                    break
            if not is_172:
                return

        ip = session.query(Ip)\
                     .filter(Ip.local_ip == local_ip)\
                     .first()

        if not ip:
            ip = Ip(local_ip=local_ip)
            session.add(ip)
            session.commit()
        ip.is_current_ip = True
        ip.scan_hosts()

    def get_ips(self):
        ips = []
        try:
            ips = check_output(['hostname', '--ip-addresses'])
            ips = ips.strip()
            if " " in ips:
                ips = ips.split(" ")
            else:
                ips = [ips]
        except:
            pass

        return ips

class Ip(Base):
    __tablename__ = "ips"
    ip_id = Column(Integer, primary_key=True)
    local_ip = Column(String)
    hosts = relationship("Hosts", backref="ip")
    is_current_ip = Column(Boolean, default=False)
    has_connected = Column(Boolean, default=False)
    def __repr__(self):
        return ("<Ip(local_ip=%r,\n"
                "    is_current_ip=%r\n"
                "    hosts=%r\n"
                ")>" % (self.local_ip, self.is_current_ip, self.hosts))

    def scan_hosts(self):

        if self.hosts:
            for host in self.hosts:
                if host.has_connected:
                    host.scan()
                    if host.is_connected:
                        return


        parts = self.local_ip.split(".")
        if not parts:
            return
        parts.pop() # remove that last element
        parts.append("0")
        ip_range = "%s/24" % (".".join(parts))

        result = check_output(["nmap","-sn", ip_range])
        rx = re.compile("(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})")
        lines = result.split("\n")
        ips_to_check = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            match = rx.search(line)
            if match:
                ips_to_check.append(match.group(1))
        for ip in ips_to_check:
            host = session.query(Hosts)\
                          .filter(Hosts.host_ip == ip)\
                          .first()
            if not host:
                host = Hosts(host_ip=ip, ip_id=self.ip_id)
                session.add(host)
                session.commit()
            host.scan()
            if host.is_connected:
                break

        ssr(created, session)

class Hosts(Base):
    __tablename__ = "hosts"
    host_id = Column(Integer, primary_key=True)
    host_ip = Column(String)
    is_connected = Column(Boolean, default=False)
    has_connected = Column(Boolean, default=False)
    ip_id = Column(Integer, ForeignKey('ips.ip_id'), index=True)
    def __repr__(self):
        return ("<Hosts(host_ip=%r\n"
                "       is_connected=%r\n"
                "       has_connected=%r\n"
                ")>" % (self.host_ip, self.is_connected, self.has_connected))

    @property
    def url(self):
        return "http://%s:5050/satellite/" % self.host_ip

    def scan(self):
        wait()
        url = self.url
        session.add(self)
        try:
            data = json.dumps({"check_connection": 1})
            req = urllib2.Request(url, data,
                                  {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
            works = json.loads(response.read())
        except Exception as e:
            _print("FAILED:", e)
            self.is_connected = False
            ssr(created, session)
            return ""

        if works.get("FMP") != "CONNECTED":
            self.is_connected = False
            ssr(created, session)
            return

        self.is_connected = True
        self.has_connected = True
        _print("CONNECTED:", url)
        ssr(created, session)

class User(Base):
    __tablename__ = 'users'
    uid = Column(Integer, primary_key=True)
    uname = Column(String, index=True)
    last_time_cued = Column(DateTime, index=True)
    listening = Column(Boolean, index=True)
    preload = relationship("Preload", backref="user")
    preload_cache = relationship("PreloadCache", backref="user")
    history = relationship("UserHistory", backref="user")
    user_file_info = relationship("UserFileInfo", backref="user")
    def __repr__(self):

        return ("<User(uname=%r,\n"
                "      uid=%d,\n"
                "      listening=%d,\n"
                "      last_time_cued=%r\n"
                ")>" % (self.uname, self.uid, self.listening, 
                        self.last_time_cued))

class Preload(Base):
    __tablename__ = 'preload'
    plid = Column(Integer, primary_key=True)
    reason = Column(Text)
    fid = Column(Integer, ForeignKey('files.fid'), index=True)
    uid = Column(Integer, ForeignKey('users.uid'), index=True)
    def __repr__(self):
        return ("<Preload(user=%r,\n"
                "         file=%r,\n"
                "         fid=%r,\n"
                ")>" % (self.user.uname, self.file, self.fid))

    def download(self):
        self.file.download()

class PreloadCache(Base):
    __tablename__ = 'preload_cache'
    pcid = Column(Integer, primary_key=True)
    reason = Column(Text)
    fid = Column(Integer, ForeignKey('files.fid'), index=True)
    uid = Column(Integer, ForeignKey('users.uid'), index=True)

class Files(Base):
    __tablename__ = 'files'
    fid = Column(Integer, primary_key=True)
    preload = relationship("Preload", backref="file")
    preload_cache = relationship("PreloadCache", backref="file")
    artists = relationship("Artists",
                           secondary=artist_association_table)
    genres = relationship("Genres",
                          secondary=genre_association_table)
    title = Column(Text)
    user_file_info = relationship("UserFileInfo", backref="file")
    history = relationship("History", backref="file")
    last_seen = Column(DateTime)
    time_played = Column(DateTime)
    playing = relationship("Playing", uselist=False, backref="file")

    def __repr__(self):
        return ("<Files(fid=%r,\n"
                "       basename=%r\n"
                "       title=%r,\n"
                "       artists=%r,\n"
                ")>" % (self.fid, self.basename, self.title, self.artists, ))

    def mark_as_played(self, percent_played=None):
        session.add(self)
        most_recent = session.query(History)\
                             .order_by(desc(History.time_played))\
                             .first()

        if most_recent.fid == self.fid:
            most_recent.mark_as_played(percent_played=percent_played)
            ssr(created, session)
            return True

        history = self.history
        if not history:
            history = []

        today = date.today()
        item = None
        for h in history:
            if h.date_played == today:
                item = h
                break
            
        if not item:
            item = History(fid=self.fid)

        item.mark_as_played(percent_played=percent_played)
        session.add(item)
        session.commit()
        ssr(created, session)

    def mark_completed(self):
        self.mark_as_played(percent_played=100)

    def set_skip_delta(self, direction=0, commit=True):
        
        for h in self.history:
            h.set_skip_delta(direction=direction,
                             commit=commit)
        if commit:
            session.commit()
        ssr(created, session)

    @property
    def filename(self):
        return os.path.join(cache_dir, self.basename)

    @property
    def basename(self):
        return "file-%s" % self.fid

    @property
    def exists(self):
        return os.path.exists(self.filename)

    def download(self):
        wait()
        downloader.download(self)

    @property
    def url(self):
        return 'http://%s/download?fid=%s' % ("erm76:5050", self.fid)

class Artists(Base):
    __tablename__ = 'artists'
    aid = Column(Integer, primary_key=True)
    artist = Column(String)
    def __repr__(self):
        return ("<Artists(aid=%r,\n"
                "         artist=%r,\n"
                ")>" % (self.aid, self.artist))

class Genres(Base):
    __tablename__ = 'genres'
    gid = Column(Integer, primary_key=True)
    genre = Column(String)

class NetcastEpisode(Base):
    __tablename__ = 'netcast_episodes'
    eid = Column(Integer, primary_key=True)
    artist = Column(String)
    title = Column(String)
    last_seen = Column(DateTime)
    pub_date = Column(String)
    history = relationship("History", backref="episode")
    playing = relationship("Playing", uselist=False, backref="episode")

    def __repr__(self):
        return ("<NetcastEpisode(eid=%r,\n"
                "                basename=%r\n"
                "                artist=%r,\n"
                "                title=%r,\n"
                ")>" % (self.eid, self.basename, self.artist, self.title))

    @property
    def filename(self):
        return os.path.join(cache_dir, self.basename)

    @property
    def basename(self):
        return "netcast-%s" % self.eid

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def url(self):
        return 'http://%s/download?eid=%s' % ("erm76:5050", self.eid)

    def mark_as_played(self, percent_played=None):
        session.add(self)
        most_recent = session.query(History)\
                             .order_by(desc(History.time_played))\
                             .first()

        if most_recent.eid == self.eid:
            most_recent.mark_as_played(percent_played=percent_played)
            return True

        history = self.history
        if not history:
            history = []

        today = date.today()
        item = None
        for h in history:
            if h.date_played == today:
                item = h
                break
            
        if not item:
            item = History(eid=self.eid)

        item.mark_as_played(percent_played=percent_played)
        session.add(item)
        session.commit()

    def mark_completed(self):
        self.mark_as_played(percent_played=100)

    def download(self):
        downloader.download(self)

class History(Base):
    __tablename__ = 'history'
    hid = Column(Integer, primary_key=True)
    percent_played = Column(Float)
    date_played = Column(Date)
    time_played = Column(DateTime, index=True)
    fid = Column(Integer, ForeignKey('files.fid'), index=True)
    eid = Column(Integer, ForeignKey('netcast_episodes.eid'), index=True)
    skip_delta = Column(Integer, default=0)
    reported = Column(Boolean, default=False)
    played = Column(Boolean, default=False)
    user_history = relationship("UserHistory", backref="history")

    def json(self):
        user_history = []
        if self.user_history:
            for uh in self.user_history:
                user_history.append(uh.json())

        date_played = None
        if self.date_played:
            date_played = get_time(int(self.date_played.strftime("%s")))

        time_played = None
        if self.time_played:
            time_played = get_time(int(self.time_played.strftime("%s")))

        id_type = 'f'
        _id = self.fid
        if self.eid:
            id_type = 'e'
            _id = self.eid

        return {
            "new_history_format": True,
            "id": _id,
            "id_type": id_type,
            "listeners": user_history,
            "skip_delta": self.skip_delta,
            "date_played": date_played,
            "time_played": time_played,
            "time": time_played,
            "dirty": True,
            "percent_played": self.percent_played
        }

    def __repr__(self):
        if self.fid:
            obj = self.file
        if self.eid:
            obj = self.episode
        return ("<History(hid=%r,\n"
                "         fid=%r,\n"
                "         eid=%r,\n"
                "         date_played=%r,\n"
                "         time_played=%r,\n"
                "         percent_played=%r,\n"
                "         skip_delta=%r,\n"
                "         reported=%r,\n"
                "         played=%r,\n"
                "         obj=%r,\n"
                ")>" % (self.hid, self.fid, self.eid, self.date_played,
                        self.time_played, self.percent_played,
                        self.skip_delta, self.reported, self.played,
                        obj))

    def set_skip_delta(self, direction=0, commit=True):
        
        session.add(self)
        self.skip_delta = self.skip_delta + direction
        self.reported = False

        if commit:
            session.commit()

    def mark_as_reported(self):
        session.add(self)
        self.reported = True
        session.commit()

    def mark_as_played(self, percent_played=None):
        # _print("BEFORE history mark as played:", self)
        
        self.date_played = date.today()
        self.time_played = datetime.now()

        users = session.query(User)\
                       .filter(User.listening == True)

        if not self.user_history:
            self.user_history = []

        for user in users:
            found = False
            for user_history in self.user_history:
                if user.uid == user_history.uid:
                    found = True
                    break
            if not found:
                uh = UserHistory(uid=user.uid,
                                 hid=self.hid)
                session.add(uh)
                self.user_history.append(uh)

        if percent_played is not None:
            self.percent_played = percent_played

        self.played = True
        self.reported = False

        session.add(self)
        # session.commit()
        # _print("AFTER history mark as played:", self)

    @property
    def basename(self):

        if self.file:
            return self.file.basename

        if self.episode:
            return self.episode.basename

        return None

    @property
    def filename(self):
        if self.file:
            return self.file.filename

        if self.episode:
            return self.episode.filename

        return None

    @property
    def exists(self):

        if self.file:
            return self.file.exists

        if self.episode:
            return self.episode.exists

        return False

class UserHistory(Base):
    __tablename__ = 'user_history'
    uhid = Column(Integer, primary_key=True)
    hid = Column(Integer, ForeignKey('history.hid'))
    uid = Column(Integer, ForeignKey('users.uid'), index=True)

    def json(self):
        return {
            "uid": self.uid
        }

    def __repr__(self):
        return ("<UserHistory(uhid=%r,\n"
                "             user.uname=%r,\n"
                ")>" % (self.uhid, self.user.uname))

class UserFileInfo(Base):
    __tablename__ = 'user_file_info'
    usid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey('users.uid'), index=True)
    fid = Column(Integer, ForeignKey('files.fid'), index=True)
    rating = Column(Integer)
    score = Column(Integer)
    true_score = Column(Float)

    def __repr__(self):
        return ("<UserFileInfo(usid=%r,\n"
                "              user.uname=%r,\n"
                "              rating=%r,\n"
                "              true_score=%r,\n"
                "              score=%r,\n"
                ")>" % (self.usid, self.user.uname, self.rating,
                        self.true_score, self.score))

class Playing(Base):
    __tablename__ = 'playing'
    id = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files.fid'), index=True)
    eid = Column(Integer, ForeignKey('netcast_episodes.eid'), index=True)
    percent_played = Column(Float)
    state = Column(String, default='PAUSED')
    volume = Column(Float)

    def json(self):
        _id = None
        id_type = None
        if self.fid:
            _id = self.fid
            id_type = 'f'
        if self.eid:
            _id = self.eid
            id_type = 'e'
        return {
            "id": _id,
            "id_type": id_type,
            "percent_played": self.percent_played,
            "state": self.state,
        }

    def __repr__(self):
        return ("<Playing(fid=%r,\n"
                "         eid=%r,\n"
                "         percent_played=%r,\n"
                "         state=%r,\n"
                ")>" % (self.fid, self.eid, self.percent_played,
                        self.state))

    @property
    def filename(self):
        try:
            if self.file:
                return self.file.filename
            if self.episode:
                return self.episode.filename
        except DetachedInstanceError:
            session.add(self)
            filename = self.filename
            session.commit()
            return filename

        if self.eid:
            episode = session.query(NetcastEpisode)\
                             .filter(NetcastEpisode.eid == self.eid)\
                             .first()
            
            return episode.filename
        return ""

    @property
    def basename(self):
        if self.file:
            return self.file.basename
        if self.episode:
            return self.episode.basename
        
        return ""

    def set_playing(self, obj):
        
        session.add(self)
        self.fid = None
        self.eid = None
        self.file = None
        self.episode = None
        if hasattr(obj, 'file'):
            self.file = obj.file
        elif hasattr(obj, 'fid'):
            print "self.file = obj",obj
            self.fid = obj.fid

        if hasattr(obj, 'eid'):
            self.eid = obj.eid
        elif hasattr(obj, 'episode'):
            self.episode = obj.episode
        
        
        session.commit()
        ssr(created, session)

    def mark_as_played(self, percent_played=None):
        
        session.add(self)
        if self.file:
            self.file.mark_as_played(percent_played=percent_played)
        if self.episode:
            self.episode.mark_as_played(percent_played=percent_played)
        self.percent_played = percent_played
        ssr(created, session)

    def next(self):
        if self.file:
            self.file.set_skip_delta(direction=-1, 
                                     commit=False)
        self.inc_index()

    def prev(self):
        self.deinc_index()
        return

    def mark_completed(self):
        if self.file:
            self.file.set_skip_delta(direction=1)
            self.file.mark_completed()
        if self.episode:
            self.episode.mark_completed()
        self.inc_index()

    def time_to_cue_netcasts(self):
        
        recent_history = session.query(History)\
                                .order_by(desc(History.time_played))\
                                .limit(10)\
                                .offset(0)
        time_to_cue_netcast = True
        for h in recent_history:
            _print("RESENT:", h.episode)
            if h.episode:
                time_to_cue_netcast = False
                break;

        ssr(created, session)
        _print("time_to_cue_netcast:", time_to_cue_netcast)
        return time_to_cue_netcast

    def get_next_netcast(self):
        netcast = None
        
        unplayed_netcast = session.query(NetcastEpisode)\
                                  .filter(and_(
                                        NetcastEpisode.history == None
                                   ))\
                                  .order_by(NetcastEpisode.pub_date)\
                                  .first()

        if unplayed_netcast:
            _print ("unplayed_netcast:", unplayed_netcast)
            netcast = unplayed_netcast
            make_transient(netcast)
            session.query(NetcastEpisode)\
                   .filter(NetcastEpisode.eid == netcast.eid)\
                   .delete()
        return netcast

    def get_next_preload(self):
        item = None
        unplayed = None

        user = session.query(User)\
                      .filter(User.listening == True)\
                      .order_by(User.last_time_cued)\
                      .first()

        if user:
            
            try:
                unplayed, _file = session.query(Preload, Files)\
                                         .filter(and_(
                                            Files.history == None,
                                            Preload.uid == user.uid,
                                            Preload.fid == Files.fid))\
                                         .order_by(Preload.plid)\
                                         .first()
            except TypeError:
                unplayed = None
            if unplayed:
                session.add(unplayed)
                session.add(_file)
            # _print("UNPLAYED 1:", unplayed)

        if not unplayed:
            _print("FALLBACK")
            # Fall back to any user's plid
            try:
                unplayed, _file = session.query(Preload, Files)\
                                         .filter(and_(
                                            Files.history == None,
                                            Preload.fid == Files.fid))\
                                         .order_by(Preload.plid)\
                                         .first()
            except TypeError:
                unplayed = None

            # _print("UNPLAYED 2:", unplayed)
        if unplayed:
            item = unplayed
            unplayed.user.last_time_cued = datetime.now()
            session.add(unplayed.user)
            make_transient(item)
            session.query(Preload)\
                   .filter(Preload.fid == unplayed.fid)\
                   .delete()
            session.commit()
            session.add(item)

        return item

    def inc_index(self):
        
        if not hasattr(self, 'idx'):
            self.idx = 0
        self.set_playing_index()
        idx = self.idx + 1
        _print ("inc_index:", idx)
        self.percent_played = 0
        try:
            self.set_playing(self.history[idx])
            session.add(self.history[idx])
            # _print ("used idx:", self.history[idx])
            self.idx = idx
        except IndexError:
            print "IndexError:", idx
            # 1. Check if it's time to cue netcasts
            cue_item = None
            if self.time_to_cue_netcasts():
                cue_item = self.get_next_netcast()
                if cue_item:
                    session.add(cue_item)
            
            # 2. Cue Preload
            if not cue_item:
                cue_item = self.get_next_preload()
                if cue_item:
                    session.add(cue_item)
                    session.commit()

            if not cue_item:
                cue_item = self.get_next_netcast()
                if cue_item:
                    session.add(cue_item)

            print "CUE ITEM:", cue_item
            # 3. Recycle history
            if not cue_item:
                _print("RECYCLE HISTORY")
                self.set_playing(self.history[0])
            else:
                self.history.append(cue_item)
                self.set_playing(cue_item)

        self.set_playing_index()

    def deinc_index(self):
        
        if not hasattr(self, 'idx'):
            self.idx = 0
        self.set_playing_index()
        self.percent_played = 0
        idx = self.idx - 1
        if idx < 0:
            idx = len(self.history) - 1
        self.set_playing(self.history[idx])

    def same_file(self, obj1, obj2):
        if not obj1 and not obj2:
            print "NOT"
            return True

        if hasattr(obj1, 'file') and hasattr(obj2, 'file'):
            if hasattr(obj1.file, 'fid') and hasattr(obj2.file, 'fid'):
                return obj1.file.fid == obj2.file.fid

        if hasattr(obj1, 'episode') and hasattr(obj2, 'episode'):
            if hasattr(obj1.episode, 'eid') and hasattr(obj2.episode, 'eid'):
                return obj1.episode.eid == obj2.episode.eid
        
        return obj1 == obj2

    def gen_history(self, regen=False):
        if hasattr(self, 'history') and self.history and not regen:
            return
        
        self.history = []
        history = session.query(History)\
                         .order_by(desc(History.time_played))
        
        already_added_fid = []
        already_added_eid = []
        for h in history:
            if h.fid in already_added_fid:
                _print("ALREADY ADDED:", h.fid)
                continue
            if h.eid in already_added_eid:
               _print("ALREADY ADDED:", h.eid)
               continue
            if h.fid:
                self.history.append(h)
                already_added_fid.append(h.fid)
                continue
            if h.eid:
                self.history.append(h)
                already_added_eid.append(h.eid)

        self.history.reverse()
        for h in self.history:
            _print("h.time_played:", h.time_played, h.basename)
        ssr(created, session)

    def regen_history(self):
        self.gen_history(regen=True)
        self.set_playing_index()

    def set_playing_index(self):
        
        self.gen_history()
        if not hasattr(self, 'idx'):
            self.idx = 0
        idx = self.idx
        last_idx = len(self.history) - 1
        found = False
        # go the cheap route first, get the last_index and see if it's
        # the last file in our history.
        if last_idx > 0:
            last_item = self.history[last_idx]
            session.add(last_item)
            session.add(self)
            if self.same_file(self, last_item):
                found = True
                idx = last_idx

        if not found:
            # It wasn't the last file so keep going
            for i, h in enumerate(self.history):
                try:
                    session.add(h)
                except AssertionError:
                    print "AssertionError:"
                same_file = self.same_file(self, h)
                if same_file:
                    idx = i
                    found = True
                    # _print("found:", i, 'same_file:', same_file)


        self.idx = idx
        _print("SET IDX TO:", idx, found)
        session.add(self)
        session.commit()

    def download(self):
        session.add(self)
        if self.fid:
            self.file.download()
        if self.eid:
            self.episode.download()
        session.commit()

class Downloader():
    def __init__(self):
        self.objs = []
        self.download_thread = None
        self.host = 'erm76:5050'
        self.shutting_down = False

    def say(self, string):
        _print(string)

    def download(self, obj):
        wait()
        obj.last_seen = datetime.now()
        if obj.exists:
            return
        _print("downloading:", obj)
        tmp = obj.filename + ".tmp"
        exist_size = 0
        open_attrs = "wb"
        request = myURLOpener()
        artists = ""
        title = ""
        if os.path.exists(tmp):
            self.say("Resuming download %s - %s" % (artists, title))
            open_attrs = "ab"
            exist_size = os.path.getsize(tmp)
            #If the file exists, then only download the remainder
            request.addheader("Range","bytes=%s-" % (exist_size))
        try:
            print obj.url
            response = request.open(obj.url)
        except urllib2.HTTPError, err:
            self.say("Download failed %s - %s" % (artists, title))
            return
        
        content_length = int(response.headers['Content-Length'])
        if content_length == exist_size:
            print "File already downloaded"
            if os.path.exists(tmp):
                shutil.move(tmp, obj.filename)
            return

        CHUNK = 16 * 1024
        total = 0.0
        display_time = get_time()
        start_time = get_time()
        precent_complete = 0
        try:
            with open(tmp, open_attrs) as fp:
                while True:
                    if self.shutting_down:
                        return False
                    chunk = response.read(CHUNK)
                    if not chunk:
                        break
                    fp.write(chunk)
                    total += len(chunk)
                    if display_time <= get_time() - 1:
                        display_time = get_time()
                        precent_complete = (total / content_length) * 100
                        _print ("DL %s:%s %s%%" % (total, content_length, 
                                                   precent_complete))
                        wait()
                wait()
                os.fsync(fp.fileno())
            precent_complete = (total / content_length) * 100
        except:
            print "Error downloading:", sys.exc_info()[0]
            return

        running_time = get_time() - start_time
        _print ("%s:%s %s%% %s" % (total, content_length, 
                                   precent_complete, running_time))
        if os.path.exists(tmp):
            shutil.move(tmp, obj.filename)

    def download_all(self):
        self.download_table(table=Preload)
        self.download_table(table=NetcastEpisode)
        self.download_table(table=History)
        self.download_table(table=PreloadCache)

    def download_table(self, table=None):
        for obj in session.query(table):
            obj.download()

# Create an engine that stores data in the local directory's
# sqlalchemy_example.db file.
sqlite_file = 'sqlite:///%s' % os.path.join(config_dir, "satellite.sqlite.db")

# print sqlite_file
engine = create_engine(sqlite_file)

try:
    engine.raw_connection().connection.text_factory = unicode
except:
    pass

# Create all tables in the engine. This is equivalent to "Create Table"
# statements in raw SQL.
Base.metadata.create_all(engine)

session = scoped_session(sessionmaker(bind=engine))

def fetch_data():
    host = 'erm76:5050';
    url = 'http://%s/satellite/' % host
    data = {}
    try:
        req = urllib2.Request(url)
        response = urllib2.urlopen(req)
        response_string = response.read()
        
    except urllib2.URLError, err:
        print "urllib2.URLError:", err
        return True

    try:
        new_data = json.loads(response_string)
    except:
        _print("<<<%s>>>" % response_string)
        new_data = {}

    return new_data

def add_file(obj):
    item = session.query(Files)\
                  .filter(Files.fid == obj.get('fid'))\
                  .first()

    if not item:
        item = Files()

    item.fid = obj.get('fid')
    item.title = obj.get('title')

    session.add(item)
    session.commit()

    user_file_info = obj.get("user_file_info")

    if user_file_info:
        listeners = user_file_info.get('listeners', [])
        for user in listeners:
            add_user_file_info(user)
        non_listeners = user_file_info.get('non_listeners', [])
        
        for user in non_listeners:
            add_user_file_info(user)

def add_user_file_info(obj):
    ufi = session.query(UserFileInfo)\
                 .filter(and_(UserFileInfo.fid == obj.get('fid'),
                              UserFileInfo.uid == obj.get('uid')))\
                 .first()

    if not ufi:
        ufi = UserFileInfo()

    keys = ['fid', 'rating', 'true_score', 'score', 'uid']

    for k in keys:
        value = obj.get(k)
        setattr(ufi, k, value)

    session.add(ufi)
    session.commit()

def add_preload_item(obj):
    add_file(obj)
    preloadInfo = obj.get('preloadInfo')
    item = session.query(Preload)\
                  .filter(Preload.plid == preloadInfo.get('plid'))\
                  .first()

    if not item:
        item = Preload()

    item.plid = preloadInfo.get('plid')
    item.fid = preloadInfo.get('fid')
    item.uid = preloadInfo.get('uid')
    item.reason = preloadInfo.get('reason')

    session.add(item)
    session.commit()

def add_user(obj):
    user = session.query(User)\
                  .filter(User.uid == obj.get('uid'))\
                  .first()

    if not user:
        user = User()

    keys = ['admin', 'listening', 'uid', 'uname']

    # {u'admin': True, u'listening': True, u'uid': 1, u'uname': u'erm'}
    for k in keys:
        value = obj.get(k)
        setattr(user, k, value)

    session.add(user)
    session.commit()

def add_netcast(obj):
    netcastInfo = obj.get('netcastInfo')
    item = session.query(NetcastEpisode)\
                  .filter(NetcastEpisode.eid == netcastInfo.get('eid'))\
                  .first()

    if not item:
        item = NetcastEpisode()

    keys = {
        'eid': 'eid',
        'title': 'episode_title',
        'artist': 'netcast_name'
    }

    for attr_key, obj_key in keys.items():
        value = netcastInfo.get(obj_key)
        setattr(item, attr_key, value)

    session.add(item)
    session.commit()
    print "item:", item

def update_playing(obj, player_data):
    item = session.query(Playing)\
                  .first()

    if not item:
        item = Playing()

    item.fid = obj.get("fid")
    item.eid = obj.get("eid")
    ### TODO Separate state from player.
    item.percent_played = player_data.get('last_time_status',{})\
                                     .get('percent_played')
    # item.state = player_data.get('last_time_status',{}).get('state')
    session.add(item)
    session.commit()

def process_json(json_data):
    playlist = json_data.get('playlist', {})
    users = playlist.get('users')
    for user in users:
        add_user(user)

    for item in json_data.get('preload', []):
        add_preload_item(item)

    for item in playlist.get('files'):
        print("ITEM")
        pprint(item)
        if item.get('netcastInfo'):
            add_netcast(item)
        else:
            add_file(item)

    netcasts = playlist.get('netcasts')

    for item in netcasts:
        add_netcast(item)

    update_playing(playlist.get('player_playing', {}), playlist.get('player'))

class SatellitePlaylist(Playlist):
    __name__ = "SatellitePlaylist"
    def __init__(self, files=[], player=None, index=0):
        
        self.playing_file = session.query(Playing).first()
        uri = None
        if self.playing_file.episode:
            uri = self.playing_file.episode.filename
        if self.playing_file.file:
            uri = self.playing_file.file.filename
        self.index = index
        self.files = [uri]

        if player is None:
            self.player = Player()
        else:
            self.player = player

        try:
            self.set_player_uri()
        except IndexError:
            pass
        self.player.state = self.playing_file.state
        self.player.position = "%s%%" % self.playing_file.percent_played
        self.player.bus.connect('message::eos', self.on_eos)
        self.player.bus.connect('message::error', self.on_error)
        self.player.window.connect("key-press-event", self.on_key_press)
        self.player.prev_btn.connect("clicked", self.prev)
        self.player.next_btn.connect("clicked", self.next)
        self.player.connect('state-changed', self.on_state_change_signal)
        # self.player.connect('time-status', self.mark_as_played)
        self.init_connections()

    def on_state_change_signal(self, *args, **kwargs):
        session.add(self.playing_file)
        self.playing_file.state = self.player.state_string
        session.commit()

    def mark_as_played(self, player, time_status):
        Gdk.threads_leave()
        now = time()

        position = time_status['position']
        one_second = 1000000000.0
        drifted = (position - self.last_position) / one_second
        if drifted > 5 or drifted < -5:
            # The file was seeked.  Force a mark_as_played
            self.last_marked_as_played = 0

        # self.log_debug("drifted:%s seconds" % drifted)
        self.last_position = position
        if self.last_marked_as_played > now - 5:
            # self.log_debug("!.mark_as_played()")
            return
        self.log_debug(".mark_as_played()")
        self.last_marked_as_played = now
        try:
            self.files[self.index].mark_as_played(**time_status)
        except AttributeError:
            sys.exit()


if __name__ == "__main__":
    json_data = fetch_data()
    process_json(json_data)
    downloader = Downloader()
    downloader.download_all()
    session.commit()

    playlist = SatellitePlaylist()
    Gtk.main()