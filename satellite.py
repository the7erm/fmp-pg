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
        self.ip = []
        self.keystack = []
        self.host = ""
        self.sync_thread = False
        self.last_sync_ok = False
        self.write_lock = False
        self.player = None
        self.pico_thread = None
        self.pico_stack = []
        self.init_pico_thread()
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
            "ip_history": {}
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
        self.resume()
        if self.data['state'] == 'PLAYING':
            print "RESUME"
            self.player.player.set_state(player.PLAYING)
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
        if self.data['state'] == 'PLAYING':
            print "PLAYING"
            self.player.player.set_state(player.PLAYING)

    def get_ip(self):
        ip = []
        try:
            ip = subprocess.check_output(['hostname', '-I'])
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
        _print("IP HISTORY")
        _pprint(self.data.get('ip_history'))

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
            result = subprocess.check_output(["nmap","-sn", ip_range])
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
        self.interaction_tracker = InteractionTracker('client', self.player)
        return

    def init_pico_thread(self):
        self.pico_thread = threading.Thread(target=self.pico_loop)
        self.pico_thread.start()

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
                self.build_playlist()
                loaded = True
            except ValueError:
                pass
        return loaded
        

    @property
    def index(self):
        return self.data['index']

    @index.setter
    def index(self, value):
        self.data['index'] = value

    @property
    def playing(self):
        return self.data.get('playing', {})

    @playing.setter
    def playing(self, value):
        self.data['playing'] = value

    @property
    def playlist(self):
        return self.data.get('playlist', [])

    @playlist.setter
    def playlist(self, value):
        self.data['playlist'] = value

    @property
    def state(self):
        return self.data.get('state')

    @state.setter
    def state(self, value):
        self.data['state'] = value

    @property
    def preload(self):
        return self.data.get('preload', [])

    @preload.setter
    def preload(self, value):
        self.data['preload'] = value

    @property
    def netcasts(self):
        return self.data.get('netcasts', [])

    @netcasts.setter
    def netcasts(self, value):
        self.data['netcasts'] = value

    @property
    def history(self):
        return self.data.get('history', [])

    @history.setter
    def history(self, value):
        self.data['history'] = value

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
            fp.write(json_data)
            wait()
            os.fsync(fp.fileno())
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

        for i, p in enumerate(self.data['playlist']):
            self.data['playlist'][i]['dirty'] = False
            self.data['playlist'][i]['played'] = False
            self.data['playlist'][i]['listeners'] = {}

        for i, p in enumerate(self.data['satellite_history']):
            self.data['satellite_history'][i]['dirty'] = False
            self.data['satellite_history'][i]['played'] = False
            self.data['satellite_history'][i]['listeners'] = {}



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

        # TODO compare new_data with self.data
        _print("new_data")

        staging = deepcopy(self.data)
        
        sync_keys = ['preload', 'netcasts', 'history', 'listeners',
                     'preload_cache', 'users']

        remote_last_interaction = new_data.get('last_interaction', 0.0)
        remote_playing_state = new_data.get('playing', {})\
                                       .get('playingState', 'PAUSED')
        priority = self.interaction_tracker.get_priority(remote_last_interaction, remote_playing_state)

        if priority == 'server':
            _print("SYNCING PLAYING")
            sync_keys += ['playing', 'pos_data']
        else:
            _print("NOT SYNCING PLAYING")
            staging['playing'] = deepcopy(self.data['playing'])
            del staging['playing']['dirty']
            del staging['playing']['played']
            if not staging['playing'] or staging['playing'] == {}:
                sync_keys += ['playing']

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

        print("playing:", staging['playing'])
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
        for p in files_to_download:
            dst = self.get_dst(p)
            if not dst or os.path.exists(dst):
                continue
            missing_files.append(p)
        if missing_files:
            self.say("Cache downloads started", permanent=True)
            for f in missing_files:
                self.download(f)
            self.say("Cache downloads finished", permanent=True)
        
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

        prefix = "file"
        if id_type == 'e':
            prefix = 'netcast'

        filename = "{prefix}-{_id}".format(prefix=prefix, _id=_id)
        dst = os.path.join(cache_dir, filename)
        if filename not in self.files:
            self.files.append(filename)
        return os.path.join(cache_dir, filename)

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
        for root, dirs, files in os.walk(cache_dir):
            for f in files:
                if f not in self.files:
                    _print("REMOVE:", f)
                    os.unlink(os.path.join(root,f))

    def download(self, obj):
        if self.shutting_down:
            return False
        _id, id_type = get_id_type(obj)
        dst = self.get_dst(obj)
        if os.path.exists(dst):
            return
        artists = obj.get("artist_title",
                          obj.get('artist', 
                                  obj.get('artists', "")))
        title = obj.get('title', obj.get('episode_title', ""))
        #if title:
        #    self.say("downloading %s - %s" % (artists, title))
        pprint(obj)
        tmp = dst + ".tmp"
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
        display_time = time.time()
        start_time = time.time()
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
                    if display_time <= time.time() - 1:
                        display_time = time.time()
                        precent_complete = (total / content_length) * 100
                        _print ("DL %s:%s %s%%" % (total, content_length, 
                                                   precent_complete))
                        wait()
                wait()
                os.fsync(fp.fileno())
        except:
            print "Error downloading:", sys.exc_info()[0]
            return

        running_time = time.time() - start_time
        _print ("%s:%s %s%% %s" % (total, content_length, 
                                   precent_complete, running_time))
        shutil.move(tmp, dst)

    def quit(self, *args, **kwargs):
        pid = os.getpid()
        print "KILLING"
        os.kill(pid)
        gtk.main_quit()
        sys.exit()

    def on_keypress(self, widget, event):
        wait()
        keyname = gtk.gdk.keyval_name(event.keyval)
        self.keypress_label.set_text("%s %s" % (keyname, event.keyval))
        print "on_keypress:", keyname

        self.keystack.append(keyname)
        self.keystack = self.keystack[-5:]

        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space', 'KP_Enter',
                       'XF86AudioPlay'):
            self.pause()
            self.rating_user = False

        if keyname in ("KP_Divide", "XF86PowerOff"):
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

            self.rating_user = False
            been_down_for = (time.time() - self.start_power_down_timer)
            if not self.start_power_down_timer or been_down_for >= 5:
                self.start_power_down_timer = time.time()
            elif been_down_for >= 4 and been_down_for <= 5:
                self.shutdown()
        else:
            self.start_power_down_timer = 0

        if keyname in ('KP_Add', 'XF86AudioRaiseVolume'):
            self.volume_up()
            self.rating_user = False

        if keyname in ('KP_Subtract', 'XF86AudioLowerVolume'):
            self.volume_down()
            self.rating_user = False

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')

        if keyname in ('KP_Delete', 'period'):
            self.get_ip()
            now = datetime.now()
            self.say("The current time is %s" % now.strftime("%I:%M %p"), 
                     wait=True)

            weather = self.data.get("weather", "")
            weather_cache = self.data.get("weather_cache", 0)
            time_now = get_time()
            if self.ip and \
                weather_cache < time_now - 300:
                cmd = ["inxi","-c","0","-w", 
                       self.data.get('weather_city', 'Cheyenne,WY')]
                try:
                    weather = subprocess.check_output(cmd)
                    p = re.compile(r'([\d]+) (F) \(([\d]+) (C)\) \- (.*)\ '
                                    'Time\:(.*)')
                    weather = p.sub('\g<5>\n \g<1> Degrees Fahrenheit\n \g<3> '
                                    'Degrees Celsius', 
                                    weather)
                    self.data['weather'] = weather
                    self.data['weather_cache'] = time_now
                except:
                    pass

            self.say(weather)

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
            self.say("%s - %s %s" % (artist, title, reason), wait=True)
            self.last_sync_time = time.time()
            self.sync()
            self.rating_user = False

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
        subprocess.check_output(["sync"])
        self.say("Playlist written to disk", wait=True, permanent=True)
        subprocess.check_output(["sudo","poweroff"])
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

        if is_listening:
            move_to_preload_cache = []
            for f in self.data['preload']:
                if f.get('uid') == uid:
                    move_to_preload_cache.append(f)
            self.data['listeners'].remove(is_listening)
            self.data['preload_cache'] += move_to_preload_cache
            for f in move_to_preload_cache:
                self.data['preload'].remove(f)
            
        if not is_listening:
            move_to_preload = []
            for f in self.data['preload_cache']:
                if f.get('uid') == uid:
                    move_to_preload.append(f)
            self.data['playlist'] += move_to_preload
            for f in move_to_preload:
                self.data['preload_cache'].remove(f)
            for user in self.data['users']:
                if user['uid'] == uid:
                    self.data['listeners'].append(user)

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
        for p in self.data.get('satellite_history', []):
            _id, id_type = get_id_type(p)
            key = "%s-%s" % (id_type, _id)
            already_added.append(key)

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
        self.set_track(0)

    def append_new_preload_item(self, _list, already_added, new_preload):
        if not _list:
            return
        item = _list.pop(0)
        _id, id_type = get_id_type(item)
        key = "%s-%s" % (id_type, _id)
        if key not in already_added:
            new_preload.append(item)
            already_added.append(key)

    def say(self, string, wait=False, permanent=False):
        self.pico_say(string, permanent=permanent)
        return

    def pico_loop(self):
        rx = re.compile("\W+")
        while True:
            _print("PICO_LOOP")
            wait()
            if not self.pico_stack:
                time.sleep(1)
                continue
            string_data = self.pico_stack.pop(0)
            if not string_data or string_data == {} and\
               not string_data.get('string', ''):
                continue
            string = string_data.get('string', '').replace("_", ' ')
            string = string.strip()
            if not string:
                continue
            string = re.sub(rx, " ", string)
            _print("SAY:", string)
            wav = "%s.wav" % (hashlib.sha1(string).hexdigest(),)
            wav = os.path.join(self.pico_dir, wav)
            if not os.path.exists(wav):
                cmd = ['pico2wave', "--lang=en-GB", "-w", wav, string]
                subprocess.check_output(cmd)
            wait()
            cmd = ['aplay', wav]
            vol = -1
            if self.player:
                vol = self.player.player.get_property("volume")
                _print("VOL:", vol)
                self.player.player.set_property("volume", 0.4)
                wait()
            subprocess.check_output(cmd)
            wait()
            if self.player:
                _print ("VOL:", vol)
                if vol < 0:
                    vol = 1.0
                self.player.player.set_property("volume", vol)
                wait()
            if not string_data.get('permanent', False):
                os.unlink(wav)

    def pico_say(self, string, permanent=False):
        self.pico_stack.append({
            'string': string,
            'permanent': permanent
        })

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
        self.index = 0
        _id, id_type = get_id_type(self.data['playing'])
        if not _id:
            try:
                self.data['playing'] = self.data['playlist'][self.index]
            except IndexError:
                return
            _id, id_type = get_id_type(self.data['playing'])

        prefix = "file"
        if id_type == 'e':
            prefix = 'netcast'
        filename = "{prefix}-{_id}".format(prefix=prefix, _id=_id)
        path = os.path.join(cache_dir, filename)
        if not os.path.isfile(path):
            self.say("MISSING:%s" % filename)
            # self.inc_track()
            return
        self.player.filename = path
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
        if not self.data['netcasts']:
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

        _print ("self.data['index']:", self.data['index'])

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
        if len(self.data['satellite_history']) > 250:
            _print ("RESIZE")
            self.data['satellite_history'] = \
                self.data['satellite_history'][-250:]
        history_by_time = {}
        for h in self.data['satellite_history']:
            _time = h.get('time', 0)
            if _time not in history_by_time:
                history_by_time[_time] = []
            history_by_time[_time].append(h)
        keys = history_by_time.keys()
        keys.sort()
        zero_time = []
        new_history = []
        already_added = []
        for key in keys:
            files = history_by_time[key]
            for f in files:
                _id, id_type = get_id_type(f)
                id_type = "%s-%s" % (_id, id_type)
                if id_type not in already_added:
                    new_history.append(f)
                    already_added.append(id_type)

        self.data['satellite_history'] = new_history


    def set_track(self, direction=1):
        _print("set_track: direction:%s" % direction)

        if direction == 0:
            self.organize_history()

        current_song = deepcopy(self.data['playing'])
        index = -1
        indexes = self.get_indexes_for_item(current_song)
        for idx in indexes:
            self.data['satellite_history'][idx].update(current_song)
            index = idx

        if not indexes:
            self.data['satellite_history'].append(current_song)
            indexes = self.get_indexes_for_item(current_song)
            index = indexes.pop()

        if direction == 1:
            index = 0
            if self.data['netcasts'] and (
                    not self.data['preload'] or
                    self.time_to_cue_netcasts()
               ):
                    queue_netcast = self.data['netcasts'].pop(0)
                    print "CUE NETCAST:", queue_netcast
                    self.data['satellite_history'].append(queue_netcast)
                    indexes = self.get_indexes_for_item(queue_netcast)
                    index = indexes.pop()
            elif self.data['preload']:
                queue_song = self.data['preload'].pop(0)
                print "CUE SONG:", queue_song
                self.data['satellite_history'].append(queue_song)
                indexes = self.get_indexes_for_item(queue_song)
                index = indexes.pop()
            else:
                self.organize_history()
                
        elif direction == -1:
            index = index - 1

        last_item_index = (len(self.data['satellite_history']) - 1)
        
        if last_item_index < index:
            index = 0

        if index < 0:
            index = last_item_index

        self.data['index'] = index

        self.data['playing'] = self.data['satellite_history'][index]
        for i, p in enumerate(self.data['satellite_history']):
            if i == index:
                _print("*"*20, "INDEX", "*"*20)
                _print(i, "SH:", pformat(p))
                _print("playlist length:", len(self.data['satellite_history']))
                _print("*"*20, "/INDEX", "*"*20)
        self.write()

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
