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
            "preload": []
        }
        self.time_to_update = 0
        self.player = player.Player()
        self.load_playlist()
        self.download()
        self.sync()
        self.init_player()
        self.init_window()

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

    def init_player(self):
        self.player.filename = self.playing['satelite-cache']
        self.player.start()
        if self.playing.get('playing'):
            for r in self.playing['ratings']:
                self.player.seek("%s%%" % r['percent_played'])
                break

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
        # if keyname in ('f','F'):
            #self.toggle_full_screen()

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')
                
        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space'):
            # self.show_controls()
            self.player.pause()
            
        if keyname == 'Up':
            self.player.seek("+5")
        
        if keyname == 'Down':
            self.player.seek("+5")
            
        if keyname == 'Right':
            self.next()
        
        if keyname == 'Left':
            self.prev()

    def on_mouse_move(self, *args, **kwargs):
        print "self.on_mouse_move:", args, kwargs

    def on_mouse_click(self, *args, **kwargs):
        print "self.on_mouse_click:", args, kwargs
        self.player.pause()

    def on_scroll(self, widget, event):
        print "on_scroll:"
        gtk.gdk.threads_leave()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.player.seek("+5")
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.player.seek("-5")
        print "/on_scroll"

    def download(self):
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
        else:
            self.download_preload()
        self.download()

    def download_preload(self):
        response = urllib2.urlopen(
            'http://erm:5050/preload?s=0&l=300&o=plid')
        contents = response.read()
        self.preload = json.loads(contents)
        print "SET PRELOAD",contents
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
        self.time_to_update = 5


    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, 
                       pos_str, dur_str, left_str, percent):

        self.set_percent_played(decimal * 100)
        # pprint(self.playing)
        self.playing['playing'] = True
        if self.time_to_update <= 0:
            self.write_playlist()
            self.time_to_update = 5

        self.time_to_update -= 1


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
            r['ultp'] = time.time()
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
        url = 'http://erm:5050/sync/'
        data = json.dumps(self.playlist)
        req = urllib2.Request(url, data, {'Content-Type': 'application/json'})
        response = urllib2.urlopen(req)
        the_page = response.read()
        print "the_page", the_page

playlist = Playlist()

gtk.main()
