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
from lib import player
from pprint import pprint, pformat
import alsaaudio
gobject.threads_init()


config_dir = os.path.expanduser("~/.fmp")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)

playlist_file = os.path.join(config_dir,"satelite-playlist.json")

cache_dir = os.path.join(config_dir, 'satelite-cache')
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)


class Playlist(object):
    def __init__(self):
        self.playlist = {
            "idx": 0,
            "preload": [],
            "playing_state": 'PLAYING'
        }
        self.initialized = False
        self.time_to_update = 0
        self.time_to_sync = 60
        self.player = player.Player()
        self.load_playlist()
        self.download_files()
        self.sync()
        self.init_player()
        self.init_window()
        self.init_timers()

    def init_timers(self):
        gobject.timeout_add(5000, self.write_playlist)
        gobject.timeout_add(10000, self.sync)

    @property
    def idx(self):
        return self.playlist['idx']
    
    @idx.setter
    def idx(self, value):
        value = int(value)
        self.playing['played'] = True
        self.playing['playing'] = False
        try:
            self.playlist['idx'] = value
            self.playing['playing'] = True
        except IndexError as err:
            print "IndexError: %s" % err
            pprint(self.playlist)
            sys.exit()

    @property
    def playing(self):
        return self.playlist['preload'][self.idx]

    @playing.setter
    def playing(self, value):
        print "PLAYING SETTER:", value
        self.playlist[self.idx] = value

    @property
    def preload(self):
        return self.playlist['preload']

    @preload.setter
    def preload(self, value):
        self.playlist['preload'] = value

    @property
    def playing_state(self):
        return self.playlist.get('playing_state', 'PLAYING')

    @playing_state.setter
    def playing_state(self, value):
        self.playlist['playing_state'] = value


    def init_player(self):
        print "init_player()"
        self.player.filename = self.playing['satelite-cache']
        self.player.prepare()
        print "PREPARED"

        if self.playing.get('playing'):
            for r in self.playing['ratings']:
                self.player.seek("%s%%" % r['percent_played'])
                break
            
        if self.playing_state == 'PLAYING' and self.player.playingState != player.PLAYING:
            self.player.pause()

        if not self.initialized:
            self.initialized = True
            self.player.connect('time-status', self.on_time_status)
            self.player.connect('end-of-stream', self.on_end_of_stream)

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
            
        if keyname == 'Up':
            self.player.seek("+5")
        
        if keyname == 'Down':
            self.player.seek("+5")
            
        if keyname == 'Right':
            self.next()
        
        if keyname == 'Left':
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
            self.playing_state = 'PAUSED'
        else:
            self.playing_state = 'PLAYING'
        self.write_playlist()

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

    def download_files(self):
        for p in self.preload:
            # pprint(p)
            root, ext = os.path.splitext(p['locations'][0]['basename'])
            filename = "{fid}{ext}".format(fid=p['fid'], ext=ext)
            dst = os.path.join(cache_dir, filename)
            tmp = dst + ".tmp"
            print "filename:%s" % filename
            print "dst:%s" % dst
            p['satelite-cache'] = dst
            if os.path.exists(dst):
                continue

            url = 'http://erm:5050/stream/%s/' % p['fid']
            print "url:", url
            response = urllib2.urlopen(url)
            fp = open(tmp, "w")
            fp.write(response.read())
            fp.close()
            shutil.move(tmp, dst)

        print len(self.preload)

    def load_playlist(self):
        # self.download_preload()
        if os.path.exists(playlist_file):
            fp = open(playlist_file, "r")
            contents = fp.read()
            fp.close()
            self.playlist = json.loads(contents)
            if 'idx' not in self.playlist:
                self.idx = 0

            # TODO post preload data to server, and download the new preload
        self.download_preload()
        self.download_files()

    def download_preload(self):
        status = None
        self_preload_fids = []
        server_preload_fids = []
        if self.playing_state != 'PLAYING':
            try:
                response = urllib2.urlopen('http://erm:5050/status/')
            except urllib2.URLError, err:
                print "urllib2.URLError:", err
                return
            contents = response.read()
            _status = json.loads(contents)
            # print "_status:", pformat(_status)
            status = _status['extended']
            status['plid'] = '0'
            status['playing'] = True
            for p in self.preload:
                p['playing'] = False
            self.preload[0] = status
            server_preload_fids.append(status['id'])


        print "download_preload"
        try:
            response = urllib2.urlopen(
                'http://erm:5050/preload?s=0&l=300&o=plid')
        except urllib2.URLError, err:
            print "urllib2.URLError:", err
            return
        contents = response.read()
        print "read contents"
        server_preload = json.loads(contents)
        if not self.preload:
            self.preload = server_preload
        else:

            for p in self.preload:
                self_preload_fids.append(int(p['plid']))
            for p in server_preload:
                server_preload_fids.append(int(p['plid']))

            keep = [val for val in self_preload_fids if val in server_preload_fids]
            append = set(server_preload_fids) - set(self_preload_fids)
            print "keep:", keep
            print "append:", append

            new_preload = []
            for p in self.playlist['preload']:
                if (p['plid'] in keep or 
                    p['plid'] in append or 
                    p.get('playing')):
                        new_preload.append(p)
                else:
                    root, ext = os.path.splitext(p['locations'][0]['basename'])
                    filename = "{fid}{ext}".format(fid=p['fid'], ext=ext)
                    cache_filename = os.path.join(cache_dir, filename)
                    if os.path.exists(cache_filename):
                        print "remove:", cache_filename
                        os.unlink(cache_filename)

            print "********"
            self.preload = new_preload
            for p in server_preload:
                if p['plid'] not in keep:
                    self.preload.append(p)
            # print "self.preload:", pformat(self.playlist['preload'])

        # print "SET PRELOAD",contents
        self.idx = 0
        self.write_playlist()

    def write_playlist(self):
        print "="*20
        print "write_playlist"
        tmp = playlist_file+".tmp"
        fp = open(tmp, 'w')
        self.playing['playing'] = True
        fp.write(json.dumps(self.playlist,
                            sort_keys=True,
                            indent=4,
                            separators=(',', ': ')))
        fp.close()
        shutil.move(tmp, playlist_file)
        # pprint(self.playing)
        return True


    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, 
                       pos_str, dur_str, left_str, percent):

        self.set_percent_played(decimal * 100)
        # pprint(self.playing)
        self.playing['playing'] = True


    def on_end_of_stream(self, *args, **kwargs):
        print "END OF STREAM"
        self.set_percent_played(100)
        self.update_skip_score(1) #increment the skip_score
        self.idx += 1
        self.play()

    def dirty_rating(self, rating, key):
        if 'updated' not in rating:
            rating['updated'] = []
        if key not in rating['updated']:
            rating['updated'].append(key)

    def set_percent_played(self, percent_played):
        for r in self.playing['ratings']:
            r['percent_played'] = percent_played
            r['ultp'] = time.time() + time.timezone
            self.dirty_rating(r, 'percent_played')
            self.dirty_rating(r, 'ultp')

    def next(self):
        self.update_skip_score(-1) # de-inc the score
        self.idx += 1
        self.player.stop()
        self.play()

    def prev(self):
        self.idx -= 1
        self.player.stop()
        self.play()

    def update_skip_score(self, value):
        for r in self.playing['ratings']:
            r['score'] += value
            if r['score'] < 0:
                r['score'] = 0
            if r['score'] > 10:
                r['score'] = 10
            self.dirty_rating(r, 'score')

    def play(self):
        self.playing['playing'] = True
        self.write_playlist()
        self.player.filename = self.playing['satelite-cache']
        self.player.start()

    def sync(self):
        self.download_preload()
        if self.playing_state != 'PLAYING':
            self.download_files()
            self.init_player()

        url = 'http://erm:5050/sync/'
        data = json.dumps(self.playlist)
        try:
            req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
            response = urllib2.urlopen(req)
        except urllib2.URLError, err:
            print "urllib2.URLError:", err
            return True
        
        the_page = response.read()
        print "the_page", the_page
        return True

playlist = Playlist()

gtk.main()
