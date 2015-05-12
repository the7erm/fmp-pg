import urllib
import urllib2
import json
import os
import sys
import select
import shutil
import gtk
import gobject
import time
import satellite_player as player
from pprint import pprint, pformat
import alsaaudio
from copy import deepcopy
import subprocess
from interaction_tracker import InteractionTracker
from config_dir import config_dir
import threading

if __name__ == "__main__":
    gobject.threads_init()
    HOST = "erm:5050"

def wait(*args, **kwargs):
    _print ("wait()", args, kwargs)
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
    _print ("/wait()", args, kwargs)
    return True


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
    if debug:
        for arg in args:
            print arg,
        if kwargs != {}:
            print kwargs
        print
        sys.stdout.flush()

def _pprint(*args, **kwargs):
    if debug:
        pprint(*args, **kwargs)
        sys.stdout.flush()

class Satellite:
    def __init__(self):
        start = time.time()
        self.say("initializing player", wait=True)
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
            "satellite_playlist": [],
            "preload_cache": [],
            "users": [],
            "volume": 100
        }
        _print("init_window()")
        self.init_window()
        _print("init_player()")
        self.init_player()
        _print("load()")
        self.load()
        volume = self.data.get('volume', 100)
        self.set_volume(volume)
        _print("sync(just_playing=True)")
        self.sync(just_playing=True)

        print "self.data['state']:", self.data['state']
        self.play()
        self.resume()
        if self.data['state'] == 'PLAYING':
            print "RESUME"
            self.player.player.set_state(player.PLAYING)
        
        self.player.connect('time-status', self.on_time_status)
        self.player.connect('end-of-stream', self.on_end_of_stream)
        _print("sync(just_playing=False)")
        self.sync()
        gobject.timeout_add(15000, self.sync)
        gobject.timeout_add(30000, self.fsync)
        print "DONE"
        self.say("Player ready")

    def wait(self, *args, **kwargs):
        _print("self.wait()")
        wait()
        _print("/self.wait()")

    def fsync(self, *args, **kwargs):
        # _print("FSYNC")
        # subprocess.Popen(['sync'])
        return True

    def init_window(self):
        self.window = gtk.Window()
        self.event_box = gtk.EventBox()
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

    def load(self):
        if self.load_json(satellite_json):
            return
        self.load_json(satellite_json+".bak")


    def load_json(self, filename):
        if not os.path.exists(filename):
            return False
        loaded = False
        with open(filename, 'r') as fp:
            try:
                self.data = json.loads(fp.read())
                last_interaction = self.data.get('last_interaction')
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
        wait()
        _print("*WRITE*")
        start = time.time()
        with open(satellite_json, 'wb') as fp:
            self.data['last_written'] = time.time()
            self.data['last_interaction'] = \
                self.interaction_tracker.last_interaction
            json_data = json.dumps(self.data,
                                   sort_keys=True,
                                   indent=4,
                                   separators=(',', ': '))
            fp.write(json_data)
            os.fsync(fp.fileno())
        wait()
        shutil.copy2(satellite_json, satellite_json+".bak")
        wait()
        _print("/*WRITE*", time.time() - start)
        self.time_to_save = 5

    def clean(self):
        self.data['playing']['dirty'] = False
        self.data['playing']['played'] = False
        self.data['playing']['listeners'] = []

        for i, p in enumerate(self.data['playlist']):
            self.data['playlist'][i]['dirty'] = False
            self.data['playlist'][i]['played'] = False
            self.data['playlist'][i]['listeners'] = {}

    def sync(self, just_playing=False, *args, **kwargs):
        if self.shutting_down:
            return False
        _print("SYNC 1")
        if just_playing:
            self.sync_worker(just_playing=just_playing, *args, **kwargs)
            return True
        t = threading.Thread(target=self.sync_worker)
        t.start()
        _print("SYNC 2")
        return True

    def sync_worker(self, just_playing=False, *args, **kwargs):
        _print("SYNC_WORKER")
        if self.sync_locked:
            _print("LOCKED")
            return
        self.data['index'] = 0
        self.sync_locked = True
        self.files = []
        self.data['last_interaction'] = \
            self.interaction_tracker.last_interaction
        data = json.dumps(self.data)
        url = 'http://%s/satellite/' % HOST
        start = time.time()
        try:
            _print("STARTING REQUEST")
            req = urllib2.Request(url, data, 
                                  {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
        except urllib2.URLError, err:
            print "urllib2.URLError:", err
            self.build_playlist()
            self.sync_locked = False
            _print("END REQUEST ERROR", time.time() - start)
            return True
        _print("END REQUEST", time.time() - start)
        self.clean()
        wait("SYNC_WORKER /clean")

        new_data = json.loads(response.read())
        # TODO compare new_data with self.data
        _print("new_data")

        staging = deepcopy(self.data)
        
        sync_keys = ['preload', 'netcasts', 'history', 'listeners',
                     'playlist', 'preload_cache', 'users']

        remote_last_interaction = new_data.get('last_interaction', 0.0)
        remote_playing_state = new_data.get('playing', {})\
                                       .get('playingState', 'PAUSED')
        priority = self.interaction_tracker.get_priority(remote_last_interaction, remote_playing_state)

        if priority == 'server':
            print "SYNCING PLAYING"
            sync_keys += ['playing']
        else:
            print "NOT SYNCING PLAYING"
            staging['playing'] = deepcopy(self.data['playing'])
            del staging['playing']['dirty']
            del staging['playing']['played']
            if not staging['playing'] or staging['playing'] == {}:
                sync_keys += ['playing']

        for key in sync_keys:
            staging[key] = new_data[key]

        self.set_playing_index(staging)

        _print ("[NEW DATA]")
        for k, v in staging.items():
            if k == 'playlist':
                continue
            print "K:",k, "v:",pformat(v)

        for i, v in enumerate(staging.get('playlist', [])):
            if i == staging['index']:
                print "="*20, 'INDEX', "="*20
            print "I:", str(i), "V:", pformat(v)
            if i == staging['index']:
                print "="*20, '/INDEX', "="*20
        _print ("[/NEW DATA]")
        _print("playing:", staging['playing'])
        self.download(staging['playing'])
        if just_playing:
            self.sync_locked = False
            self.data.update(staging)
            return True
        
        for p in staging['playlist']:
            # _print("playlist:", p)
            self.download(p)

        for p in staging['preload_cache']:
            self.download(p)

        self.data.update(staging)
        self.clear_cache()
        _print("index:", staging['index'])
        
        if priority == 'server':
            self.play()
            self.resume()
        self.write()
        self.sync_locked = False
        return True

    def resume(self):
        print "RESUME"
        pos_data = self.data['playing'].get('pos_data')
        print "pos_data:"
        pprint(pos_data)
        percent_played = self.playing.get('percent_played')
        if pos_data and 'percent_played' in pos_data:
            self.player.seek(pos_data['percent_played'])
        elif percent_played:
            self.player.seek(str(percent_played)+"%")


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
            print "NO FILES"
            return
        for root, dirs, files in os.walk(cache_dir):
            for f in files:
                if f not in self.files:
                    print "REMOVE:", f
                    os.unlink(os.path.join(root,f))

    def download(self, obj):
        if self.shutting_down:
            return False
        _id, id_type = get_id_type(obj)
        if _id is None or id_type is None:
            return

        prefix = "file"
        if id_type == 'e':
            prefix = 'netcast'

        filename = "{prefix}-{_id}".format(prefix=prefix, _id=_id)
        dst = os.path.join(cache_dir, filename)
        self.files.append(filename)
        if os.path.exists(dst):
            print "EXISTS", filename
            return
        title = obj.get('title', obj.get('episode_title'))
        if title:
            self.say("downloading %s" % title)
        _print("DOWNLOAD:", filename)
        pprint(obj)
        tmp = dst + ".tmp"
        url = 'http://%s/stream/%s/' % (HOST, _id)
        if id_type == 'e':
            url = 'http://%s/stream-netcast/%s/' % (HOST, _id)
        _print("url:", url)
        CHUNK = 16 * 1024
        try:
            response = urllib2.urlopen(url)
        except urllib2.HTTPError, err:
            return
        start = time.time()
        total = 0
        with open(tmp, 'wb') as fp:
            while True:
                if self.shutting_down:
                    return False
                chunk = response.read(CHUNK)
                if not chunk: 
                    break
                fp.write(chunk)
                if start <= time.time() - 1:
                    start = time.time()
                    _print (total)
                    wait()
                total += CHUNK
            os.fsync(fp.fileno())
        shutil.move(tmp, dst)

    def quit(self, *args, **kwargs):
        gtk.main_quit()
        sys.exit()

    def on_keypress(self, widget, event):
        wait()
        keyname = gtk.gdk.keyval_name(event.keyval)
        print "on_keypress:", keyname

        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space', 'KP_Enter'):
            self.pause()

        if keyname == "KP_Divide":
            if not self.start_power_down_timer:
                self.start_power_down_timer = time.time()
            elif (time.time() - self.start_power_down_timer) >= 3:
                if self.shutting_down:
                    return
                self.shutting_down = True
                _print ("SHUTDOWN")
                self.say("Shutting down", wait=True)
                self.write()
                self.say("Playlist written to disk", wait=True)
                subprocess.check_output(["sudo","poweroff"])
                sys.exit()
        else:
            self.start_power_down_timer = 0

        if keyname == 'KP_Add':
            self.volume_up()

        if keyname == 'KP_Subtract':
            self.volume_down()

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')

        if keyname == "KP_Multiply":
            self.say("rate")
            self.rating_user = True

        if self.rating_user:
            self.rating_on_keypress(keyname)
            return

        if keyname in ('KP_Begin',):
            self.pause()
            
        if keyname in ('Up', 'KP_Up'):
            self.player.seek("+5")

        if keyname in ("Page_Up", "KP_Page_Up"):
            self.player.seek("+30")
        
        if keyname in ('Down', 'KP_Down'):
            self.player.seek("-5")

        if keyname in ("Page_Down", "KP_Page_Down"):
            self.player.seek("-30")
            
        if keyname in ('Right', 'KP_Right'):
            self.next()
        
        if keyname in ('Left', 'KP_Left'):
            self.prev()

        for l in self.data.get('users'):
            if keyname in ("%s" % l['uid'], "KP_%s" % l['uid']):
                self.set_listening(l['uid'])


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
                    self.say(l['uname'])
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
        is_lisening = False
        for l in self.data['listeners']:
            if l['uid'] == uid:
                is_lisening = l
                break

        uname = "ERROR"
        for u in self.data['users']:
            if u['uid'] == uid:
                uname = u['uname']
                break

        if is_lisening:
            move_to_preload_cache = []
            for f in self.data['playlist']:
                if f.get('uid') == uid:
                    move_to_preload_cache.append(f)
            self.data['listeners'].remove(is_lisening)
            self.data['preload_cache'] += move_to_preload_cache
            for f in move_to_preload_cache:
                self.data['playlist'].remove(f)
            
        if not is_lisening:
            move_to_playlist = []
            for f in self.data['preload_cache']:
                if f.get('uid') == uid:
                    move_to_playlist.append(f)
            self.data['playlist'] += move_to_playlist
            for f in move_to_playlist:
                self.data['preload_cache'].remove(f)
            for user in self.data['users']:
                if user['uid'] == uid:
                    self.data['listeners'].append(user)

        # Restructure playlist
        playlist = deepcopy(self.data['playlist'])

        partitioned = {}
        uids = []
        for l in self.data['listeners']:
            uids.append(l['uid'])
            partitioned[l['uid']] = []

        partitioned['others'] = []

        for p in playlist:
            if p.get('uid') in uids:
                partitioned[p['uid']].append(p)
            else:
                partitioned['others'].append(p)

        new_playlist = []
        already_added = []
        still_data = True
        while still_data:
            still_data = False
            for _uid in partitioned.keys():
                if partitioned[_uid]:
                    still_data = True
                    item = partitioned[_uid].pop(0)
                    _id, id_type = get_id_type(item)
                    key = "%s-%s" % (id_type, _id)
                    if key not in already_added:
                        new_playlist.append(item)
                        already_added.append(key)

        self.data['playlist'] = new_playlist

        if is_lisening:
            self.say("Set %s to not listening" % uname)
        else:
            self.say("Set %s to listening" % uname)

    def say(self, string, wait=False):
        cmd = ["espeak", "-a", "200", string]
        if wait:
            subprocess.check_output(cmd)
        else:
            subprocess.Popen(cmd)

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
        print "SET_VOLUME:",vol
        print "type:",type(vol)
        if isinstance(vol, str) or isinstance(vol,unicode):
            print "SET_VOLUME2:",vol
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
            print "SET_VOLUME3:",vol
        try:
            vol=int(vol)
        except:
            print "FAIL:",vol
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
        print "self.on_mouse_click:", args, kwargs
        self.pause()

    def on_scroll(self, widget, event):
        print "on_scroll:"
        wait()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.player.seek("+5")
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.player.seek("-5")
        print "/on_scroll"

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
        print "END OF STREAM"
        self.set_playing_data('skip_score', 1)
        self.set_percent_played(100)
        self.inc_track()
        self.play(True)

    def set_percent_played(self, percent_played):
        self.set_playing_data('percent_played', percent_played)
        local_offset = time.timezone
        if time.daylight:
            local_offset = time.altzone
            
        self.set_playing_data('time', time.time() + local_offset)

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

        print "self.data['index']:", self.data['index']
        found = []

        playing_id, playing_id_type = get_id_type(self.data['playing'])
        for i, p in enumerate(self.data['playlist']):
            item_id, item_id_type = get_id_type(p)
            # print "i:",i
            if item_id == playing_id and playing_id_type == item_id_type:
                _print ("set_playing_data UPDATE:", i, "self.data['index']:",
                        self.data['index'])
                found.append(i)
                self.data['playlist'][i].update(self.data['playing'])

    def inc_track(self, direction=1):
        current_song = deepcopy(self.data['playing'])
        playing_id, playing_id_type = get_id_type(current_song)
        
        found = []

        for i, p in enumerate(self.data['playlist']):
            item_id, item_id_type = get_id_type(p)
            if item_id == playing_id and playing_id_type == item_id_type:
                print "inc_track UPDATE:",i
                found.append(i)
                self.data['playlist'][i].update(current_song)

        if not found:
            self.data['playlist'].append(current_song)

        if direction == 1:
            print "POP", self.data['playlist'][0]
            self.data['playing'] = self.data['playlist'].pop(0)
            self.data['playlist'].append(self.data['playing'])
        elif direction == -1:
            self.data['playing'] = self.data['playlist'].pop()
            self.data['playlist'].insert(0, self.data['playing'])
        for i, p in enumerate(self.data['playlist']):
            print i, "P:", p
        self.write()

    def deinc_track(self):
        self.inc_track(-1)

    def set_playing_index(self, staging=None):
        if staging is None:
            staging = deepcopy(self.data)
        current_song = deepcopy(staging['playing'])
        playing_id, playing_id_type = get_id_type(current_song)
        found = []

        playing_id, playing_id_type = get_id_type(staging['playing'])
        for i, p in enumerate(staging['playlist']):
            item_id, item_id_type = get_id_type(p)
            if item_id == playing_id and playing_id_type == item_id_type:
                _print ("set_playing_index UPDATE:",i)
                found.append(i)
                staging['playlist'][i].update(staging['playing'])

        if found:
            print "FOUND:",found
            staging['index'] = found[0]
            return True

        return False



if __name__ == "__main__":
    s = Satellite()
    gtk.main()
