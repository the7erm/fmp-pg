import urllib
import urllib2
import json
import os
import signal
import sys
import select
import shutil
import gtk
import gobject
import time
from datetime import datetime
import satellite_player as player
from pprint import pprint, pformat
import alsaaudio
from copy import deepcopy
import subprocess
from interaction_tracker import InteractionTracker
from config_dir import config_dir
import threading
import re
import hashlib

if __name__ == "__main__":
    gobject.threads_init()

def wait(*args, **kwargs):
    # _print ("wait()", args, kwargs)
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # _print("gtk.events_pending():", gtk.events_pending())
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"
    #  _print ("/wait()", args, kwargs)
    return True

def get_time():
    local_offset = time.timezone
    if time.daylight:
        local_offset = time.altzone
    return time.time() + local_offset

def get_id_type(obj):
    if not obj or obj == {}:
        return None, None

    _id = int(obj.get('id', -1))
    id_type = obj.get('id_type', None)

    if _id not in (-1, None) and id_type in ('f', 'e'):
        return _id, id_type

    fid = int(obj.get('fid', -1))
    eid = int(obj.get('eid', -1))

    if fid not in (-1, None):
        return fid, 'f'

    if eid not in (-1, None):
        return eid, 'e'

    return None, None

satellite_json = os.path.join(config_dir,"satellite.json")

cache_dir = os.path.join(config_dir, 'satellite-cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)

debug = True

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

class myURLOpener(urllib.FancyURLopener):
    """Create sub-class in order to overide error 206.  This error means a
       partial file is being sent,
       which is ok in this case.  Do nothing with this error.
    """
    # http://code.activestate.com/recipes/83208-resuming-download-of-a-file/
    def http_error_206(self, url, fp, errcode, errmsg, headers, data=None):
        pass

class Satellite:
    def __init__(self):
        self.files = []
        self.download_thread = False
        self.downloading_cache = False
        self.saying_something = False
        self.saying_status = False
        self.ip = []
        self.keystack = []
        self.host = ""
        self.sync_thread = False
        self.last_sync_ok = False
        self.write_lock = False
        self.player = None
        self.pico_thread = None
        self.pico_stack = []
        self.say("initializing player", permanent=True)
        start = time.time()
        self.last_sync_time = 0
        self.sync_response_string = ""
        self.shutting_down = False
        self.start_power_down_timer = 0
        self.time_to_save = 5
        self.sync_locked = False
        self.rating_user = False
        self.rating = False
        self.real_history = []
        self.files_to_download = []
        self.data = {
            "preload": [],
            "playing": {},
            "netcasts": [],
            "history": [],
            "state": "PLAYING",
            "listeners": [],
            "index": -1,
            "playlist": [],
            "preload_cache": [],
            "users": [],
            "volume": 100,
            "satellite_history": [],
            "weather": '',
            "weather_cache": 0,
            "weather_city": "Cheyenne,WY",
            "ip_history": {},
            "last_seen_times": {},
            "cue_netcasts": True
        }
        self.pico_dir = os.path.join(config_dir, 'pico-wav')
        print "PICO_DIR:", self.pico_dir
        if not os.path.exists(self.pico_dir):
            print "MKDIR:"
            os.makedirs(self.pico_dir)
        _print("init_window()")
        self.init_window()
        _print("init_player()")
        self.init_player()
        _print("load()")
        self.load()
        self.set_track(0)
        volume = self.data.get('volume', 100)
        self.set_volume(volume)
        self.play()
        if self.data['state'] == 'PLAYING':
            print "RESUME"
            self.player.playingState = player.PAUSED
        self.resume()
        if self.data['state'] == 'PLAYING':
            print "RESUME"
            self.player.playingState = player.PLAYING
        _print("sync(just_playing=True)")
        self.sync(just_playing=True)
        _print("self.data['state']:", self.data['state'])
        self.player.connect('time-status', self.on_time_status)
        self.player.connect('end-of-stream', self.on_end_of_stream)
        _print("sync(just_playing=False)")
        self.sync()
        gobject.timeout_add(15000, self.sync)
        gobject.timeout_add(60000, self.fsync)
        print "DONE"
        self.set_track(0)
        self.say("player initialization complete", permanent=True)
        

    def get_ip(self):
        ip = []
        try:
            ip = self.check_output(['hostname', '-I'])
            ip = ip.strip()
            if " " in ip:
                ip = ip.split(" ")
            else:
                ip = [ip]
        except:
            self.host = ""

        if self.ip != ip:
            self.host = ""
        self.ip = ip

    def set_host(self, ip, server_ip):
        # ip = this machine's ip
        host = "%s:5050" % (server_ip,)
        url = "http://%s/satellite/" % host
        _print("SCANNING:", url)
        data = json.dumps(self.data)
        try:
            req = urllib2.Request(url, data,
                                  {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
            _print("CONNECTED:", url)
            works = json.loads(response.read())
        except Exception as e:
            _print("FAILED:", e)
            return ""
        if self.host != host:
            self.say("Connected to F M P server", permanent=True)
        self.host = host
        _print("FOUND:", host)
        if 'ip_history' not in self.data:
            self.data['ip_history'] = {}

        if ip not in self.data.get('ip_history', {}):
            self.data['ip_history'][ip] = []
        if server_ip not in self.data['ip_history'][ip]:
            self.data['ip_history'][ip].append(server_ip)
        _print("IP HISTORY")
        _pprint(self.data.get('ip_history'))
        self.write()
        return host

    def scan_ips(self):
        self.host = ""
        self.get_ip()
        if not self.ip:
            return

        for ip in self.ip:
            ip_history = self.data.get('ip_history', {})
            print "ip_history:", ip_history
            if ip in ip_history:
                print "USING HOST CACHE"
                for server_ip in ip_history[ip]:
                    if self.set_host(ip, server_ip):
                        return

        for ip in self.ip:
            if (not ip.startswith("192.168.") and 
                not ip.startswith("10.") and
                not ip.startswith("172.")):
                    continue
            
            if ip.startswith("172."):
                is_172 = False
                for i in range(16, 32):
                    if ip.startswith("172.%s." % i):
                        is_172 = True
                        break
                if not is_172:
                    continue

            parts = ip.split(".")
            if not parts:
                continue
            parts.pop() # remove that last element
            parts.append("0")
            ip_range = "%s/24" % (".".join(parts))
            result = self.check_output(["nmap","-sn", ip_range])
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
            for server_ip in ips_to_check:
                if self.set_host(ip, server_ip):
                    break

    def wait(self, *args, **kwargs):
        wait()

    def fsync(self, *args, **kwargs):
        wait()
        # _print("FSYNC")
        # subprocess.Popen(['sync'])
        return True

    def init_window(self):
        self.window = gtk.Window()
        self.event_box = gtk.EventBox()
        self.keypress_label = gtk.Label()
        self.event_box.add(self.keypress_label)
        self.window.add(self.event_box)
        self.window.show_all()
        self.window.add_events(gtk.gdk.KEY_PRESS_MASK |
                               gtk.gdk.POINTER_MOTION_MASK |
                               gtk.gdk.BUTTON_PRESS_MASK |
                               gtk.gdk.SCROLL_MASK)
        self.window.connect("destroy", self.quit)
        self.window.connect('key-press-event', self.on_keypress)
        self.window.connect('motion-notify-event', self.on_mouse_move)
        self.window.connect('button-press-event', self.on_mouse_click)
        self.window.connect("scroll-event", self.on_scroll)
        self.window.maximize()

    def init_player(self):
        self.player = player.Player()
        self.player.connect('missing-plugin', self.on_missing_plugin)
        self.interaction_tracker = InteractionTracker('client', self.player)
        return

    def on_missing_plugin(self, *args, **kwargs):
        state = self.data['state']
        self.set_track(1)
        start = False
        if state == 'PLAYING':
            start = True
        self.play(start)

    def load(self):
        if self.load_json(satellite_json):
            _print("LOADED:", satellite_json)
            return
        self.load_json(satellite_json+".bak")


    def load_json(self, filename):
        if not os.path.exists(filename):
            return False
        loaded = False
        with open(filename, 'r') as fp:
            try:
                self.data = json.loads(fp.read())
                if not self.data.get('satellite_history',[]):
                    self.data['satellite_history'] = \
                            self.data.get('history', [])
                if 'last_seen_times' not in self.data:
                    self.data['last_seen_times'] = {}
                self.build_playlist()
                loaded = True
            except ValueError:
                pass
        return loaded

    def data_setter(self, key, value):
        _print("SET:", key,'=', value)
        self.data[key] = value

    def data_getter(self, key, default=None):
        res = self.data.get(key, default)
        _print("GET:", key, '=', pformat(res))
        return res

    @property
    def index(self):
        return self.data_getter('index', 0)

    @index.setter
    def index_setter(self, value):
        self.data_setter('index', value)

    @property
    def playing(self):
        return self.data_getter('playing', {})

    @playing.setter
    def playing_setter(self, value):
        self.data_setter('playing', value)

    @property
    def playlist(self):
        return self.data_getter('playlist', [])

    @playlist.setter
    def playlist_setter(self, value):
        self.data_setter('playlist', value)

    @property
    def state(self):
        return self.data_getter('state', 'PLAYING')

    @state.setter
    def state_state(self, value):
        self.data_setter('state', value)

    @property
    def preload(self):
        return self.data.get('preload', [])

    @preload.setter
    def preload(self, value):
        self.data['preload'] = value

    @property
    def netcasts(self):
        return self.data_getter('netcasts', [])

    @netcasts.setter
    def netcasts(self, value):
        self.data_setter('netcasts', value)

    @property
    def history(self):
        return self.data_getter('history', [])

    @history.setter
    def history(self, value):
        self.data_setter('history', value)

    def write(self):
        if self.write_lock:
            return
        self.write_lock = True
        self.time_to_save = 5
        wait()
        _print("*WRITE*")
        start = time.time()
        with open(satellite_json, 'wb') as fp:
            self.data['playlist'] = []
            self.data['last_written'] = time.time()
            self.data['last_interaction'] = \
                self.interaction_tracker.last_interaction
            json_data = json.dumps(self.data,
                                   sort_keys=True,
                                   indent=4,
                                   separators=(',', ': '))
            wait()
            self.time_to_save = 5
            fp.write(json_data)
            # wait()
            # os.fsync(fp.fileno())
        wait()
        shutil.copy2(satellite_json, satellite_json+".bak")
        wait()
        _print("/*WRITE* ", time.time() - start)
        self.time_to_save = 5
        self.write_lock = False

    def clean(self):
        self.data['playing']['dirty'] = False
        self.data['playing']['played'] = False
        self.data['playing']['listeners'] = []

        for i, p in enumerate(self.data['satellite_history']):
            self.data['satellite_history'][i]['dirty'] = False
            self.data['satellite_history'][i]['played'] = False
            self.data['satellite_history'][i]['listeners'] = []


    def sync(self, just_playing=False, *args, **kwargs):
        if self.shutting_down:
            return False
        _print("SYNC 1")
        if just_playing:
            try:
                self.sync_worker(just_playing=just_playing, *args, **kwargs)
            except Exception as e:
                print "SYNC Exception:",e
            return True
        if self.sync_locked:
            return True
        self.sync_thread = threading.Thread(target=self.sync_worker)
        self.sync_thread.start()
        _print("SYNC 2")
        return True

    def unlock_sync(self, last_sync_ok=False):
        self.last_sync_ok = last_sync_ok
        self.sync_locked = False
        if self.sync_thread:
            self.sync_thread = False

    def sync_worker(self, just_playing=False, *args, **kwargs):
        wait()
        self.get_ip()
        if not self.ip:
            self.unlock_sync(False)
            return True

        if not self.host:
            self.scan_ips()

        if not self.host:
            self.unlock_sync(False)
            return True

        _print("SYNC_WORKER")
        if self.sync_locked:
            _print("LOCKED")
            return True
        self.last_sync_ok = False
        self.sync_locked = time.time()
        self.files = []
        self.data['last_interaction'] = \
            self.interaction_tracker.last_interaction
        data = json.dumps(self.data)
        url = 'http://%s/satellite/' % self.host
        start = time.time()
        if self.last_sync_time < (start - 5):
            try:
                _print("STARTING REQUEST")
                req = urllib2.Request(url, data, 
                                      {'Content-Type': 'application/json'})
                response = urllib2.urlopen(req)
                wait()
            except urllib2.URLError, err:
                print "urllib2.URLError:", err
                self.build_playlist()
                self.unlock_sync(False)
                _print("END REQUEST ERROR", time.time() - start)
                self.host = ""
                return True
            except:
                self.host = ""
                self.unlock_sync(False)
                _print("END REQUEST ERROR 2", time.time() - start)
                return True
            self.sync_response_string = response.read()
            self.last_sync_time = time.time()
            try:
                new_data = json.loads(self.sync_response_string)
            except:
                _print("JSON DECODE ERROR", time.time() - start)
                _print("<<<%s>>>" % response_string)
                self.unlock_sync(False)
                return True
            # only clean after a successful connection.
            self.clean()
            wait("SYNC_WORKER /clean")

        _print("END REQUEST", time.time() - start)

        new_data = json.loads(self.sync_response_string)

        staging = deepcopy(self.data)
        
        sync_keys = ['preload', 'netcasts', 'history',
                     'preload_cache', 'users']

        remote_last_interaction = new_data.get('last_interaction', 0.0)
        remote_playing_state = new_data.get('playing', {})\
                                       .get('playingState', 'PAUSED')
        priority = self.interaction_tracker.get_priority(remote_last_interaction, remote_playing_state)

        if priority == 'server':
            _print("SYNCING PLAYING")
            sync_keys += ['playing', 'pos_data', 'listeners']
        else:
            _print("NOT SYNCING PLAYING")
            staging['playing'] = deepcopy(self.data.get('playing', {}))
            try:
                del staging['playing']['dirty']
            except KeyError:
                pass
            try:
                del staging['playing']['played']
            except KeyError:
                pass
            if not staging['playing'] or staging['playing'] == {}:
                sync_keys += ['playing', 'pos_data', 'listeners']

        for key in sync_keys:
            if key in new_data:
                staging[key] = new_data[key]

        self.set_staging_playing_index(staging)
        """
        _print ("[NEW DATA]")
        
        for k, v in staging.items():
            if k == 'playlist':
                continue
            _print("K:",k, "v:",pformat(v))

        for i, v in enumerate(staging.get('playlist', [])):
            if i == staging['playlist_index']:
                _print("="*20,"INDEX","="*20)
            _print("I:", str(i), "V:", pformat(v))
            if i == staging['playlist_index']:
                _print("="*20,"/INDEX","="*20)
        _print ("[/NEW DATA]")
        """
        
        # Make sure anything that's changed since the original copy
        # was made is over written with new data.
        for key in self.data.keys():
            if key not in sync_keys:
                staging[key] = self.data[key]

        _print("playing:", staging['playing'])
        self.download(staging['playing'])

        if just_playing:
            # Just update the current 'playing' data and not self.ip.startswith("10.")) and
            self.data.update(staging)
            self.unlock_sync(False)
            return True

        _history = staging.get('history',[])
        _history.reverse()
        for h in _history:
            indexes = self.get_indexes_for_item(h)
            if not indexes:
                h['time'] = h['date_played']
                self.data['index'] += 1
                self.data['satellite_history'].insert(0, h)

        files_to_download = self.data.get('playlist', []) + \
                            staging.get('playlist', []) + \
                            self.data.get('preload', []) + \
                            staging.get('preload', []) + \
                            self.data.get('preload_cache', []) + \
                            staging.get('preload_cache', []) + \
                            self.data.get('satellite_history', []) + \
                            self.data.get('history', []) + \
                            staging.get('history',[]) + \
                            self.data.get('netcasts', []) + \
                            staging.get('netcasts', [])

        missing_files = []
        _time = get_time()
        for p in files_to_download:
            dst = self.get_dst(p)
            if dst:
                self.data['last_seen_times'][dst] = _time
            if not dst or os.path.exists(dst):
                continue
            if p not in self.files_to_download:
                self.files_to_download.append(p)

        if self.files_to_download and not self.download_thread:
            self.download_thread = threading.Thread(
                target=self.download_worker)
            self.download_thread.start()


        # Make sure anything that's changed since the original copy
        # was made is over written with new data.
        for key in self.data.keys():
            if key not in sync_keys:
                staging[key] = self.data[key]
        self.data.update(staging)
        self.clear_cache()
        if priority == 'server':
            _print("*"*20,"PRIORITY SERVER");
            # self.set_percent_played()
            self.play()
            self.resume()
        else:
             _print("*"*20,"PRIORITY SELF");
        self.set_track(0)
        self.unlock_sync(True)
        return True

    def get_dst(self, obj):
        _id, id_type = get_id_type(obj)
        if _id is None or id_type is None:
            return False
        filename = self.make_key(_id, id_type)
        dst = os.path.join(cache_dir, filename)
        if filename not in self.files:
            self.files.append(filename)
        dst = os.path.join(cache_dir, filename)
        return dst

    def resume(self):
        _print("*"*20,"RESUME", "*"*20)
        pos_data = self.data['playing'].get('pos_data', {})
        _print("pos_data:")
        pprint(pos_data)
        pos_data_percent_played = pos_data.get('percent_played', '0%')
        percent_played = self.playing.get('percent_played',
                                          pos_data_percent_played)

        if self.interaction_tracker.priority == 'server':
            percent_played = pos_data_percent_played
        
        if not isinstance(percent_played, (str, unicode)):
            percent_played = str(percent_played)

        if not percent_played.endswith("%"):
            percent_played = percent_played+"%"
        
        print "***percent_played:", percent_played
        self.player.seek(percent_played)

    def build_playlist(self):
        if not self.data.get('playlist', []):
            self.data['playlist'] = []


    def in_playlist(self, obj):
        _id, id_type = get_id_type(obj)
        if _id is None or id_type is None:
            return False

        found = False
        for f in self.data['playlist']:
            f_id, f_id_type = get_id_type(f)
            if _id == f_id and id_type == f_id_type:
                found = True
                break

        return found

    def clear_cache(self):
        if not self.files:
            _print("NO FILES")
            return
        last_seen_times = self.data.get('last_seen_times', {})
        now = get_time()
        expire_time = now - (60 * 60 * 1)
        for root, dirs, files in os.walk(cache_dir):
            for f in files:
                if f not in self.files:
                    dst = os.path.join(root, f)
                    if dst in last_seen_times:
                        last_seen = self.data['last_seen_times'][dst]
                        if last_seen > expire_time:
                            # It's been downloaded in the last 24 hours
                            # so skip it.
                            _print("NOT REMOVING:", f, now - last_seen, "delete in:", last_seen - expire_time)
                            continue
                        del self.data['last_seen_times'][dst]
                    _print("REMOVE:", f)
                    if os.path.exists(dst):
                        os.unlink(dst)

    def download_worker(self):
        started_download_time = get_time()
        
        self.say("Cache downloads started", permanent=True)
        cnt = 0
        while self.files_to_download:
            cnt += 1
            f = self.files_to_download.pop(0)
            self.download(f)
            try:
                self.download(f)
            except Exception as e:
                _print("ERROR WHILE DOWNLOADING:", e)
        download_time = get_time() - started_download_time
        _print("download_time:", download_time)
        _print("#files", cnt)
        self.say("Cache downloads finished", permanent=True)
        self.download_thread = False
        self.write()

    def download(self, obj):
        if self.shutting_down:
            return False
        _id, id_type = get_id_type(obj)
        dst = self.get_dst(obj)
        if os.path.exists(dst):
            self.data['last_seen_times'][dst] = get_time()
            return
        
        artists = obj.get("artist_title",
                          obj.get('artist', 
                                  obj.get('artists', "")))
        title = obj.get('title', obj.get('episode_title', ""))
        #if title:
        #    self.say("downloading %s - %s" % (artists, title))
        pprint(obj)
        tmp = dst + ".tmp"
        self.data['last_seen_times'][tmp] = get_time()
        exist_size = 0
        open_attrs = "wb"
        request = myURLOpener()
        if os.path.exists(tmp):
            self.say("Resuming download %s - %s" % (artists, title))
            open_attrs = "ab"
            exist_size = os.path.getsize(tmp)
            #If the file exists, then only download the remainder
            request.addheader("Range","bytes=%s-" % (exist_size))
        url = 'http://%s/stream/%s/' % (self.host, _id)
        if id_type == 'e':
            url = 'http://%s/stream-netcast/%s/' % (self.host, _id)
        _print("DOWNLOAD URL:", url)
        
        try:
            response = request.open(url)
        except urllib2.HTTPError, err:
            self.say("Download failed %s - %s" % (artists, title))
            return
        
        content_length = int(response.headers['Content-Length'])
        if content_length == exist_size:
            print "File already downloaded"
            if os.path.exists(tmp):
                shutil.move(tmp, dst)
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
            self.data['last_seen_times'][dst] = get_time()
            del self.data['last_seen_times'][tmp]
            shutil.move(tmp, dst)

    def quit(self, *args, **kwargs):
        pid = os.getpid()
        print "KILLING"
        os.kill(pid)
        gtk.main_quit()
        sys.exit()

    def wait_for_empty_pico_stack(self):
        while self.pico_stack or self.saying_something:
            wait()
            time.sleep(1)

    def on_keypress(self, widget, event):
        wait()
        keyname = gtk.gdk.keyval_name(event.keyval)
        self.keypress_label.set_text("%s %s" % (keyname, event.keyval))
        _print("="*20, "ON_KEYPRESS:", keyname, keyname.upper())
        _print("="*20, "ON_KEYPRESS:", event)
        _print(dir(event))
        _print('event.string:', event.string)
        _print('event.state:', event.state)
        _print('event.hardware_keycode', event.hardware_keycode)
        _print('event.group', event.group)

        self.keystack.append(keyname)
        self.keystack = self.keystack[-5:]

        if keyname in ('XF86Tools',):
            self.rating_user = False
            if self.data.get('cue_netcasts', True):
                self.data['cue_netcasts'] = False
                self.say("Don't Cue Netcasts", permanent=True)
            else:
                self.data['cue_netcasts'] = True
                self.say("Cue Netcasts", permanent=True)
            self.write()
            return True

        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space', 'KP_Enter',
                       'XF86AudioPlay'):
            self.pause()
            self.rating_user = False
            return

        if keyname == 'XF86HomePage':
            self.set_track(0)
            self.rating_user = False
            return

        if keyname in ("KP_Divide", "XF86PowerOff"):
            self.rating_user = False
            all_same = True
            for k in self.keystack:
                if not all_same:
                    break
                for k2 in self.keystack:
                    if k != k2:
                        all_same = False
                        break
            if all_same:
                self.shutdown()
                return
            been_down_for = (time.time() - self.start_power_down_timer)
            if not self.start_power_down_timer or been_down_for >= 5:
                self.start_power_down_timer = time.time()
            elif been_down_for >= 4 and been_down_for <= 5:
                self.shutdown()
        else:
            self.start_power_down_timer = 0

        if keyname in ('KP_Add', 'XF86AudioRaiseVolume'):
            self.rating_user = False
            self.volume_up()
            return

        if keyname in ('KP_Subtract', 'XF86AudioLowerVolume'):
            self.rating_user = False
            self.volume_down()
            return

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')
            return

        if keyname in ('KP_Delete', 'period'):
            self.rating_user = False
            if self.saying_status:
                return
            self.interaction_tracker.mark_interaction()
            self.saying_status = True
            now = datetime.now()
            now = now.strftime("%I:%M %p")
            now = now.lstrip('0')
            self.say("The current time is %s" % now, wait=True)
            weather = self.data.get("weather", "")
            weather_cache = self.data.get("weather_cache", 0)
            weather_cache = 0
            time_now = get_time()
            self.get_ip()
            
            if self.ip and \
                weather_cache < time_now - 300:
                cmd = ["inxi","-c","0","-w", 
                       self.data.get('weather_city', 'Cheyenne,WY')]
                try:
                    weather = self.check_output(cmd)
                    p = re.compile(r'([\d]+) (F) \(([\d]+) (C)\) \- (.*)\ '
                                    'Time\:(.*)')
                    weather = p.sub('\g<5>\n: \g<1> Degrees Fahrenheit\n: \g<3>: '
                                    'Degrees Celsius', 
                                    weather)
                    if 'error' not in weather.lower():
                        self.data['weather'] = weather
                        self.data['weather_cache'] = time_now
                    else:
                        weather = self.data.get("weather", "")
                except:
                    pass

            self.say(weather)
            if self.host:
                self.host = ""
            self.sync(just_playing=True)
            _print("PLAYING:", self.data['playing'])

            artist = self.data['playing'].get("artist_title", "")
            title = ""
            if not artist:
                artist = self.data['playing'].get('artist', "")
                artists = self.data['playing'].get("artists", [])
                if artists:
                    if isinstance(artists, list):
                        artist = artists[0]['artist']
                    elif isinstance(artists, (str, unicode)):
                        artist = artists
                title = self.data['playing'].get('title', "")
                if not title:
                    title = self.data['playing'].get("episode_title", "")

            reason = self.data['playing'].get("reason", "")
            if artist or title:
                self.say("%s - %s" % (artist, title), wait=True)
            self.say(reason, permanent=True)
            listeners = []
            for l in self.data['listeners']:
                listeners.append(l['uname'])
            if listeners:
                self.say("Listeners before sync: %s" % ", ".join(listeners))
            self.sync()
            listeners = []
            for l in self.data['listeners']:
                listeners.append(l['uname'])
            if listeners:
                self.say("Listeners after sync: %s" % ", ".join(listeners))
            self.wait_for_empty_pico_stack()
            self.saying_status = False
            return

        if keyname == "KP_Multiply":
            self.say("rate", permanent=True)
            self.rating_user = True

        if self.rating_user:
            self.rating_on_keypress(keyname)
            return

        if keyname in ('KP_Begin',):
            self.pause()
            
        if keyname in ('Up', 'KP_Up', 'XF86AudioForward'):
            self.player.seek("+5")

        if keyname in ("Page_Up", "KP_Page_Up"):
            self.player.seek("+30")
        
        if keyname in ('Down', 'KP_Down', 'XF86AudioRewind'):
            self.player.seek("-5")

        if keyname in ("Page_Down", "KP_Page_Down"):
            self.player.seek("-30")
            
        if keyname in ('Right', 'KP_Right', 'XF86AudioNext'):
            self.next()
        
        if keyname in ('Left', 'KP_Left', 'XF86AudioPrev'):
            self.prev()

        for l in self.data.get('users'):
            if keyname in ("%s" % l['uid'], "KP_%s" % l['uid']):
                self.set_listening(l['uid'])

    def shutdown(self):
        if self.shutting_down:
            return
        self.shutting_down = True
        _print ("SHUTDOWN")
        self.say("Shutting down", wait=True, permanent=True)
        self.write()
        self.check_output(["sync"])
        self.say("Playlist written to disk", wait=True, permanent=True)
        self.wait_for_empty_pico_stack()
        self.check_output(["sudo","poweroff"])
        sys.exit()


    def rating_on_keypress(self, keyname):
        keys = [
            ("0", "KP_0", "KP_Insert"),
            ("1", "KP_1", "KP_End"),
            ("2", "KP_2", "KP_Down"),
            ("3", "KP_3", "KP_Page_Down"),
            ("4", "KP_4", "KP_Left"),
            ("5", "KP_5", "KP_Begin"),
            ("6", "KP_6", "KP_Right"),
            ("7", "KP_7", "KP_Home"),
            ("8", "KP_8", "KP_Up"),
            ("9", "KP_9", "KP_Page_Up")
        ]
        value = -1
        for i, row in enumerate(keys):
            if keyname in row:
                value = i
                break
        if isinstance(self.rating_user, bool):
            for l in self.data.get('users'):
                if l['uid'] == value:
                    self.rating_user = l
                    self.say(l['uname'], permanent=True)
                    break
        elif value != -1:
            self.rate(value)

    def rate(self, rating):
        rating = int(rating)
        if rating <= 5:
            if not 'rated' in self.data['playing']:
                self.data['playing']['rated'] = {}
            uid = self.rating_user['uid']
            self.data['playing']['rated'][uid] = rating
            self.say("Rated %s for %s" % (rating, self.rating_user['uname']))
            self.set_playing_data('dirty', True)
            self.rating_user = False


    def set_listening(self, uid):
        while self.sync_locked:
            _print("Waiting for sync to unlock")
            time.sleep(0.25)
        self.sync_locked = True

        is_listening = False
        for l in self.data['listeners']:
            if l['uid'] == uid:
                is_listening = l
                break

        uname = "ERROR"
        for u in self.data['users']:
            if u['uid'] == uid:
                uname = u['uname']
                break

        if not self.data.get('preload_cache', []):
            self.data['preload_cache'] = []

        if is_listening:
            self.data['listeners'].remove(is_listening)
            move_to_preload_cache = []
            for f in self.data['preload']:
                if f.get('uid') == uid:
                    move_to_preload_cache.append(f)
        
            for f in move_to_preload_cache:
                self.data['preload_cache'].append(f)
                _print("append to preload_cache f:",f)
                try:
                    self.data['preload'].remove(f)
                except ValueError, e:
                    print "ValueError:",e
                    print "f:",f
            
            
        if not is_listening:
            for user in self.data['users']:
                if user['uid'] == uid:
                    user['listening'] = True
                    self.data['listeners'].append(user)
            move_to_preload = []
            for f in self.data['preload_cache']:
                if f.get('uid') == uid:
                    move_to_preload.append(f)

            for f in move_to_preload:
                self.data['preload'].append(f)
                try:
                    _print("remove from preload_cache f:",f)
                    self.data['preload_cache'].remove(f)
                except ValueError, e:
                    print "ValueError:",e
                    print "f:",f

        # Restructure playlist
        preload = deepcopy(self.data['preload'])

        partitioned = {}
        uids = []
        for l in self.data['listeners']:
            uids.append(l['uid'])
            partitioned[l['uid']] = []

        netcasts = []

        partitioned['others'] = []

        for p in preload:
            if p.get('uid') in uids:
                partitioned[p['uid']].append(p)

        new_preload = []
        already_added = []
        # self.organize_history()
        for p in self.data.get('satellite_history', []):
            already_added.append(self.make_key(item=p))

        still_data = True
        while still_data:
            still_data = False
            for _uid in partitioned.keys():
                if partitioned[_uid]:
                    still_data = True
                    self.append_new_preload_item(partitioned[_uid],
                                                 already_added, 
                                                 new_preload)

        self.data['preload'] = new_preload
        if is_listening:
            self.say("Set %s to not listening" % uname, permanent=True)
        else:
            self.say("Set %s to listening" % uname, permanent=True)
        
        self.sync_locked = False
        self.set_track(0)
        self.sync()

    def append_new_preload_item(self, _list, already_added, new_preload):
        if not _list:
            return
        item = _list.pop(0)
        key = self.make_key(item=item)
        if key not in already_added:
            new_preload.append(item)
            already_added.append(key)

    def make_key(self, _id=None, id_type=None, item=None):
        if item is not None:
            _id = item.get('id')
            id_type = item.get('id_type')
        prefix = 'file'
        if id_type == 'e':
            prefix = 'netcast'
        res = "%s-%s" % (prefix, _id)
        return res

    def say(self, string, wait=False, permanent=False):
        string = string.replace("halle", "hally")
        self.pico_say(string, permanent=permanent)
        return

    def pico_worker(self):
        rx = re.compile("\W+")
        paused = False
        while self.pico_stack:
            _print("PICO WORKER")
            wait()
            self.saying_something = True
            string_data = self.pico_stack.pop(0)
            if not string_data or string_data == {} and\
               not string_data.get('string', ''):
                continue

            string = string_data.get('string', '').replace("_", ' ')
            # string = re.sub(rx, " ", string)
            string = string.strip()
            if not string:
                continue
            _print("SAY:", string)
            wav = "%s.wav" % (hashlib.sha1(string).hexdigest(),)
            wav = os.path.join(self.pico_dir, wav)
            if not os.path.exists(wav):
                cmd = ['pico2wave', "--lang=en-GB", "-w", wav, string]
                self.check_output(cmd)
            if self.player and self.player.playingState == player.PLAYING:
                paused = True
                self.player.pause()
            cmd = ['aplay', wav]
            self.check_output(cmd)
            if not string_data.get('permanent', False):
                os.unlink(wav)

        if self.player and self.player.playingState == player.PAUSED and paused:
            self.player.pause()
        self.pico_thread = None
        self.saying_something = False

    def check_output(self, cmd):
        wait()
        res = subprocess.check_output(cmd)
        wait()
        return res

    def pico_say(self, string, permanent=False):
        self.pico_stack.append({
            'string': string,
            'permanent': permanent
        })
        if not self.pico_thread:
            self.pico_thread = threading.Thread(target=self.pico_worker)
            self.pico_thread.start()

    def pause(self):
        _print("PAUSE CALLED")
        self.player.pause()
        if self.player.playingState != player.PLAYING:
            self.data['state'] = 'PAUSED'
        else:
            self.data['state'] = 'PLAYING'
            pos_int = self.player.player.query_position(
                self.player.time_format, None)[0]
            self.player.seek_ns(pos_int)
        self.write()
        self.sync()
        # wait()

    def on_mouse_move(self, *args, **kwargs):
        # print "self.on_mouse_move:", args, kwargs
        return

    def get_volume(self):
        cards = alsaaudio.cards()
        for i, c in enumerate(cards):
            try:
                m = alsaaudio.Mixer('Master', cardindex=i)
                result = m.getvolume()
                volume = result.pop()
                return volume
            except alsaaudio.ALSAAudioError:
                continue
        return -1

    def volume_up(self):
        self.set_volume("+")
        return

    def volume_down(self):
        self.set_volume("-")
        return

    def set_volume(self, vol):
        cards = alsaaudio.cards()
        _print("SET_VOLUME:",vol)
        _print("type:",type(vol))
        if isinstance(vol, str) or isinstance(vol,unicode):
            _print("SET_VOLUME2:",vol)
            if vol in ("-","+"):
                cur_vol = self.get_volume()
                if vol == "-":
                    vol = cur_vol - 3
                else:
                    vol = cur_vol + 3

                if vol < 0:
                    vol = 0
                if vol > 100:
                    vol = 100
            _print("SET_VOLUME3:",vol)
        try:
            vol=int(vol)
        except:
            _print("FAIL:", vol)
            return

        if vol < 0 or vol > 100:
            return;
        for i, c in enumerate(cards):
            try:
                m = alsaaudio.Mixer('Master',cardindex=i)
                m.setvolume(vol)
            except alsaaudio.ALSAAudioError:
                continue

        self.data['volume'] = vol
        self.write()


    def on_mouse_click(self, *args, **kwargs):
        wait()
        _print("self.on_mouse_click:", args, kwargs)
        self.pause()

    def on_scroll(self, widget, event):
        _print ("on_scroll:")
        wait()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.player.seek("+5")
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.player.seek("-5")
        _print ("/on_scroll")

    def next(self):
        self.set_playing_data('played', True)
        self.set_playing_data('skip_score', -1)
        self.player.stop()
        self.inc_track()
        self.play(True)
        self.interaction_tracker.mark_interaction()

    def prev(self):
        self.set_playing_data('played', True)
        self.player.stop()
        self.deinc_track()
        self.play(True)
        self.interaction_tracker.mark_interaction()

    def play(self, start=False):
        _id, id_type = get_id_type(self.data['playing'])
        if not _id:
            try:
                # self.organize_history()
                self.index = len(self.data['satellite_history']) - 1
                self.data['playing'] = self.data['satellite_history'][self.index]
            except IndexError:
                return
            _id, id_type = get_id_type(self.data['playing'])
        filename = self.get_dst(self.data['playing'])
        if not os.path.isfile(filename):
            self.say("MISSING:%s" % os.path.basename(filename))
            return
        self.player.filename = filename
        self.player.prepare()
        if start:
            self.player.start()
        return

    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, 
                       pos_str, dur_str, left_str, percent):
        wait()
        self.set_percent_played(decimal * 100)
        self.time_to_save -= 1
        if self.time_to_save <= 0:
            self.time_to_save = 5
            self.write()

    def on_end_of_stream(self, *args, **kwargs):
        gtk.gdk.threads_leave()
        _print ("on_end_of_stream: END OF STREAM")
        self.set_playing_data('skip_score', 1)
        self.set_percent_played(100)
        self.inc_track()
        self.play(True)

    def set_percent_played(self, percent_played):
        self.set_playing_data('percent_played', percent_played)
        self.set_playing_data('time', get_time())

    def time_to_cue_netcasts(self):
        if not self.data['netcasts'] or not self.data.get('cue_netcasts', True):
            return False
        time_to_cue = True
        for p in self.data['satellite_history'][-10:]:
            _id, id_type = get_id_type(p)
            if id_type == 'e':
                time_to_cue = False
                break
        return time_to_cue

    def set_playing_data(self, key, value):
        _print(key,'=',value)
        if key != 'skip_score':
            self.data['playing'][key] = value
        else:
            if 'skip_score' not in self.data['playing']:
                self.data['playing']['skip_score'] = 0
            self.data['playing']['skip_score'] += value
            self.data['playing']['played'] = True
        self.data['playing']['dirty'] = True

        if not self.data['playing'].get('listeners'):
            self.data['playing']['listeners'] = []

        for l2 in self.data['listeners']:
            if l2 not in self.data['playing']['listeners']:
                self.data['playing']['listeners'].append(deepcopy(l2))

        _print ("self.index", self.index)
        _print ("self.data['index']:", self.data['index'])
        _print ("len(self.data['satellite_history'])", 
            len(self.data['satellite_history']))

        indexes = self.get_indexes_for_item(self.data['playing'])
        if not indexes:
            self.data['satellite_history'].append(self.data['playing'])
            indexes = self.get_indexes_for_item(self.data['playing'])
            indexes2 = deepcopy(indexes)
            self.data['index'] = indexes2.pop()

        for idx in indexes:
            self.data['satellite_history'][idx].update(self.data['playing'])

    def inc_track(self):
        self.set_track(1)

    def deinc_track(self):
        self.set_track(-1)

    def get_indexes_for_item(self, item, _list=None):
        if _list is None:
            _list = self.data.get('satellite_history', [])

        _id, id_type = get_id_type(item)
        indexes = []
        for i, list_item in enumerate(_list):
            item_id, item_id_type = get_id_type(list_item)
            if _id == item_id and item_id_type == id_type:
                indexes.append(i)
        return indexes

    def organize_history(self):
        if len(self.data['satellite_history']) > 200:
            _print ("RESIZE")
            self.data['satellite_history'] = \
                self.data['satellite_history'][-200:]
        history_by_time = {}
        for h in self.data['satellite_history']:
            _time = h.get('time', 0)
            if _time not in history_by_time:
                history_by_time[_time] = []
            history_by_time[_time].append(h)
        already_added = []
        new_list  = self.unique_list(history_by_time, already_added)
        self.data['satellite_history'] = new_list

    def unique_list(self, _list, already_added=[]):
        if not _list:
            return []
        new_list = []
        if isinstance(_list, dict):
            keys = _list.keys()
            keys.sort()
            for key in keys:
                sub_list = _list[key]
                new_list = new_list + self.unique_list(
                    sub_list, already_added=already_added)

            return new_list
        else:
            for f in _list:
                key = self.make_key(item=f)
                if key not in already_added:
                    new_list.append(f)
                    already_added.append(key)
        return new_list


    def set_track(self, direction=1):
        _print("set_track: DIRECTION:%s" % direction)
        # 2 is a `special` direction
        #if direction in (0, 2):
        #    self.organize_history()

        current_song = deepcopy(self.data['playing'])
        index = -1
        indexes = self.get_indexes_for_item(current_song)
        for idx in indexes:
            self.data['satellite_history'][idx].update(current_song)
            index = idx
        _print("current_song", current_song)
        _print("current_song index:", index)

        if not indexes or index == -1:
            self.data['satellite_history'].append(current_song)
            indexes = self.get_indexes_for_item(current_song)
            index = indexes.pop()

        if direction in (1,):
            if index == -1:
                index = len(self.data['satellite_history']) - 1
            index = index + 1
            try:
                test_index = self.data['satellite_history'][index]
            except IndexError:
                _print("INDEX ERROR (Try to cue fallback to index 0)")
                index = 0
                if (
                        self.data['netcasts'] and 
                        self.data.get('cue_netcasts', True)
                   ) and (
                        not self.data['preload'] or
                        self.time_to_cue_netcasts()
                   ):
                        result, index = self.cue_from('netcasts')
                elif self.data['preload']:
                    result, index = self.cue_from('preload')
                else:
                    self.organize_history()
                
        elif direction == -1:
            index = index - 1

        last_item_index = (len(self.data['satellite_history']) - 1)
        
        if last_item_index < index:
            index = 0

        if index < 0:
            index = last_item_index

        self.index = index
        self.data['playing'] = self.data['satellite_history'][index]
        _print("*"*20, "INDEX", "*"*20)
        _print(index, "SH:", pformat(self.data['satellite_history'][index]))
        _print("playlist length:", len(self.data['satellite_history']))
        _print("*"*20, "/INDEX", "*"*20)
        self.write()

    def cue_from(self, key):
        cued = False
        while self.data[key] and not cued:
            item = self.data[key].pop(0)
            cued, index = self.cue_if_not_played(item)
        if cued:
            _print("CUE %s:" % key.upper())
        else:
            _print("FAIL TO CUE:%s" % key.upper())
        return cued, index

    def cue_if_not_played(self, item):
        indexes = self.get_indexes_for_item(item)
        _print("INDEXES:", indexes)
        if indexes:
            _print("ALREADY PRESENT:", item)
            return False, 0
        # self.organize_history()
        self.data['satellite_history'].append(item)
        indexes = self.get_indexes_for_item(item)
        index = indexes.pop()
        return True, index

    def set_staging_playing_index(self, staging=None):
        if staging is None:
            staging = deepcopy(self.data)

        indexes = self.get_indexes_for_item(staging['playing'],
                                            staging['playlist'])
        for idx in indexes:
            staging['playlist'][idx].update(staging['playing'])

        if indexes:
            staging['playlist_indexs'] = deepcopy(indexes)
            staging['playlist_index'] = indexes.pop()
            return True

        staging['playlist_indexs'] = [-1]
        staging['playlist_index'] = 0
        return False



if __name__ == "__main__":
    try:
        s = Satellite()
        gtk.main()
    except KeyboardInterrupt:
        pid = os.getpid()
        try:
            s.write()
        except:
            pass
        try:
            gtk.main_quit()
        except:
            pass
        os.kill(pid, signal.SIGTERM)
