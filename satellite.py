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
gobject.threads_init()

def wait():
    _print ("wait()")
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"
    _print ("/wait()")


config_dir = os.path.expanduser("~/.fmp")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

satelite_json = os.path.join(config_dir,"satelite.json")

cache_dir = os.path.join(config_dir, 'satelite-cache')
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
        self.data = {
            "preload": [],
            "playing": {},
            "netcasts": [],
            "history": [],
            "state": "PLAYING",
            "listeners": [],
            "index": 0,
            "playlist": []
        }
        _print("init_window()")
        self.init_window()
        _print("init_player()")
        self.init_player()
        _print("load()")
        self.load()
        _print("sync()")
        self.sync()
        print "self.data['state']:", self.data['state']
        self.play()
        self.resume()
        if self.data['state'] == 'PLAYING':
            print "RESUME"
            self.player.player.set_state(player.PLAYING)
        
        self.player.connect('time-status', self.on_time_status)
        self.player.connect('end-of-stream', self.on_end_of_stream)
        gobject.timeout_add(10000, self.sync)
        print "DONE"

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

    def init_player(self):
        self.player = player.Player()
        return

    def load(self):
        if not os.path.exists(satelite_json):
            return
        fp = open(satelite_json, 'r')
        try:
            self.data = json.loads(fp.read())
            self.build_playlist()
        except ValueError:
            pass
        fp.close()

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
        fp = open(satelite_json, 'w')
        self.data['last_written'] = time.time()
        fp.write(json.dumps(self.data,
                            sort_keys=True,
                            indent=4,
                            separators=(',', ': ')))
        fp.close()

    def clean(self):
        self.data['playing']['dirty'] = False
        self.data['playing']['played'] = False

        for i, p in enumerate(self.data['playlist']):
            self.data['playlist'][i]['dirty'] = False
            self.data['playlist'][i]['played'] = False

    def sync(self, *args, **kwargs):
        gtk.gdk.threads_leave()
        self.files = []
        data = json.dumps(self.data)
        url = 'http://erm:5050/sattelite/'
        try:
            req = urllib2.Request(url, data, 
                                  {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
        except urllib2.URLError, err:
            print "urllib2.URLError:", err
            self.build_playlist()
            _print("index:", self.data['index'])
            return True

        self.clean()

        new_data = json.loads(response.read())
        # TODO compare new_data with self.data
        _print("new_data")
        
        sync_keys = ['preload', 'netcasts', 'history', 'listeners',
                     'playlist']

        if not self.data['state'] or self.data['state'] == 'PAUSED':
            print "SYNCING PLAYING"
            sync_keys += ['playing', 'index']
        else:
            print "NOT SYNCING PLAYING"

        for key in sync_keys:
            self.data[key] = new_data[key]

        playing_id, playing_id_type = self.get_id_type(self.data['playing'])
        for i, p in enumerate(self.data['playlist']):
            p_id, p_id_type = self.get_id_type(p)
            if playing_id == p_id and playing_id_type == p_id_type:
                print "INDEX:", i
                self.index = i


        _print ("[NEW DATA]")
        _pprint(self.data)
        for k, v in self.data.items():
            print "K:",k
        _print ("[/NEW DATA]")
        _print("playing:", self.data['playing'])
        self.download(self.data['playing'])
        
        for p in self.data['playlist']:
            # _print("playlist:", p)
            self.download(p)

        self.clear_cache()
        
        _print("index:", self.data['index'])
        
        if not self.data['state'] or self.data['state'] == 'PAUSED':
            self.play()
            self.resume()
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
        _id, id_type = self.get_id_type(obj)
        if _id is None or id_type is None:
            return False

        found = False
        for f in self.data['playlist']:
            f_id, f_id_type = self.get_id_type(f)
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
                

    def get_id_type(self, obj):
        if not obj or obj == {}:
            return None, None

        _id = int(obj.get('id', -1))
        id_type = obj.get('id_type', 'f')
        fid = int(obj.get('fid', -1))
        eid = int(obj.get('eid', -1))

        if fid == -1:
            fid = None

        if fid is not None:
            _id = fid
            id_type = 'f'

        if eid == -1:
            eid = None

        if eid is not None:
            _id = eid
            id_type = 'e'

        if _id == -1:
            _id = None
            id_type = None

        return _id, id_type

    def download(self, obj):
        _id, id_type = self.get_id_type(obj)
        if _id is None or id_type is None:
            return

        prefix = "file"
        if id_type == 'e':
            prefix = 'netcast'

        filename = "{prefix}-{_id}".format(prefix=prefix, _id=_id)
        dst = os.path.join(cache_dir, filename)
        self.files.append(filename)
        if os.path.exists(dst):
           #  print "EXISTS", filename
            return
        _print("DOWNLOAD:", filename)
        pprint(obj)
        tmp = dst + ".tmp"
        url = 'http://erm:5050/stream/%s/' % _id
        if id_type == 'e':
            url = 'http://erm:5050/stream-netcast/%s/' % _id
        _print("url:", url)
        response = urllib2.urlopen(url)
        fp = open(tmp, "wb")
        fp.write(response.read())
        fp.close()
        shutil.move(tmp, dst)

    def quit(self, *args, **kwargs):
        gtk.main_quit()
        sys.exit()

    def on_keypress(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        print "on_keypress:", keyname
        # if keyname in ('f','F'):
            #self.toggle_full_screen()

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')
                
        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space', 'KP_Enter'):
            # self.show_controls()
            self.pause()
            
        if keyname in ('Up', 'KP_Up'):
            self.player.seek("+5")
        
        if keyname in ('Down', 'KP_Down'):
            self.player.seek("+5")
            
        if keyname in ('Right', 'KP_Right'):
            self.next()
        
        if keyname in ('Left', 'KP_Left'):
            self.prev()

        if keyname == 'KP_Add':
            self.volume_up()

        if keyname == 'KP_Add':
            self.volume_up()

        if keyname == 'KP_Subtract':
            self.volume_down()

    def pause(self):
        self.player.pause()
        if self.player.playingState != player.PLAYING:
            self.data['state'] = 'PAUSED'
        else:
            self.data['state'] = 'PLAYING'
        self.write()

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
        return -1;

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

    def on_mouse_click(self, *args, **kwargs):
        print "self.on_mouse_click:", args, kwargs
        self.pause()

    def on_scroll(self, widget, event):
        print "on_scroll:"
        gtk.gdk.threads_leave()
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

    def prev(self):
        print "PREV"
        self.set_playing_data('played', True)
        self.player.stop()
        self.deinc_trac()
        self.play(True)

    def play(self, start=False):
        _id, id_type = self.get_id_type(self.data['playing'])
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
        self.set_playing_data('time', time.time() + time.timezone)

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
        print "self.data['index']:", self.data['index']

        self.data['playlist'][self.data['index']].update(self.data['playing'])
        self.write()

    def inc_track(self):
        self.data['playlist'][self.data['index']].update(self.data['playing'])
        self.data['index'] = self.data['index'] + 1
        if self.data['index'] >= len(self.data['playlist']):
            self.data['index'] = 0
        self.data['playing'] = self.data['playlist'][self.data['index']]
        self.write()

    def deinc_trac(self):
        self.data['playlist'][self.data['index']].update(self.data['playing'])
        self.data['index'] = self.data['index'] - 1
        if self.data['index'] <= 0:
            self.data['index'] = len(self.data['playlist']) - 1
        self.data['playing'] = self.data['playlist'][self.data['index']]
        self.write()

s = Satellite()
gtk.main()
