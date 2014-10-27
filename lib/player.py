#!/usr/bin/env python2
# lib/player.py -- main gstreamer player
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
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

## TODO: add appindicator in __main__ section

from gtk_utils import gtk_main_quit
import sys 
import os 
import time 
import thread 
import signal 
import urllib
import gc
import gobject
import pygst
import pygtk
import gtk
import pango
import base64
import hashlib
import subprocess
import re
from time import sleep
# gobject.threads_init()
pygst.require("0.10")
import gst

import thread

STOPPED = gst.STATE_NULL
PAUSED = gst.STATE_PAUSED
PLAYING = gst.STATE_PLAYING

class Player(gobject.GObject):
    __gsignals__ = {
        'error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,str)),
        'end-of-stream': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'show-window': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'time-status': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                        (gobject.TYPE_INT64, gobject.TYPE_INT64, 
                         gobject.TYPE_INT64, gobject.TYPE_DOUBLE, str, str, str, 
                         str)), # pos, length, left, decimal, pos_formatted, 
                                # length_formatted, left_formatted, 
                                # percent_formatted
        'state-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'tag-received': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                         (str, object)),
        'missing-plugin': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, 
                           (object,)),
    }
    
    def __init__(self, filename=None, alt_widget=None):
        gobject.GObject.__init__(self)
        self.showing_controls = False
        self.filename = filename
        self.playingState = STOPPED
        self.fullscreen = False
        self.seek_locked = False
        self.hide_timeout = None
        self.pos_data = {}
        self.dur_int = 0
        self.pos_int = 0
        self.volume = 1.0
        self.alt_widget = alt_widget
        self.time_format = gst.Format(gst.FORMAT_TIME)
        self.init_window()
        self.init_main_event_box()
        self.init_main_vbox()
        self.init_time_label()
        self.init_movie_window()
        self.init_controls()
        self.init_player()
        self.init_connections()
        self.hide_controls()
        self.calculate_thread = None
        if self.alt_widget:
            self.alt_vbox.pack_start(self.alt_widget, True, True)
        else:
            self.alt_vbox.hide()
        if filename is not None:
            self.start()

    def init_connections(self):
        self.window.connect("destroy", gtk_main_quit)
        self.window.connect('key-press-event', self.on_key_press)
        self.window.connect('motion-notify-event', self.show_controls)
        self.window.connect('button-press-event', self.pause)
        self.window.connect("scroll-event", self.on_scroll)
        # self.window.connect('button-press-event', self.show_controls)
        # self.window.connect('key-press-event', self.show_controls)
        # self.movie_window.connect('key-press-event', self.on_key_press)
        self.main_event_box.connect('motion-notify-event', self.show_controls)
        self.movie_window.connect('motion-notify-event', self.show_controls)

        self.connect('time-status', self.on_time_status)
        self.connect('state-changed', self.show_hide_play_pause)

        # Controls
        self.pause_button.connect('clicked', self.pause)
        self.play_button.connect('clicked', self.pause)
        self.fs_button.connect('clicked', self.toggle_full_screen)
        self.unfs_button.connect('clicked', self.toggle_full_screen)

    def init_window(self):
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Video-Player")
        
        img_path = ""
        possible_paths = [
            os.path.join(sys.path[0],"images"),
            os.path.join(sys.path[0], "..", "images"),
            os.path.join(sys.path[0], "..")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                img_path = p
                break

        self.window.set_icon_from_file(os.path.join(img_path, "tv.png"));

        self.set_style(self.window)
        self.window.add_events(gtk.gdk.KEY_PRESS_MASK |
                               gtk.gdk.POINTER_MOTION_MASK |
                               gtk.gdk.BUTTON_PRESS_MASK |
                               gtk.gdk.SCROLL_MASK)
        
        self.window.set_title("Video-Player")
        self.window.set_default_size(600, 400)

    def init_main_event_box(self):
        #main Event Box
        self.main_event_box = gtk.EventBox()
        self.set_style(self.main_event_box)
        self.window.add(self.main_event_box)

    def set_style(self, widget):
        widget.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        widget.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))

    def init_main_vbox(self):
        # main box
        self.main_VBox = gtk.VBox()
        self.main_VBox.show()
        self.main_event_box.add(self.main_VBox)

    def init_time_label(self):
        ## Time label ##
        self.time_label = gtk.Label()
        self.set_style(self.time_label)
        self.time_label.modify_font(pango.FontDescription("15"))
        self.time_label.set_property('xalign', 1.0)
        self.main_VBox.pack_start(self.time_label, False, True)
        self.time_label.show()

    def e_hb(self):
        hb = gtk.HBox()
        e = gtk.EventBox()
        e.add(hb)
        self.set_style(e)
        return e, hb

    def init_movie_window(self):
        ## movie_window
        self.movie_window = gtk.DrawingArea()
        self.set_style(self.movie_window)
        self.movie_window.add_events(gtk.gdk.KEY_PRESS_MASK | 
                                     gtk.gdk.POINTER_MOTION_MASK)

        self.movie_window.show()
        self.main_VBox.pack_start(self.movie_window, True, True)
        self.alt_vbox = gtk.VBox()
        self.main_VBox.pack_start(self.alt_vbox, True, True)
        self.alt_vbox.hide()

    def init_controls(self):
        ### SET UP CONTROLS ###
        self.controls = gtk.HBox()
        self.prev_button = gtk.Button('', gtk.STOCK_MEDIA_PREVIOUS)
        self.pause_button = gtk.Button('', gtk.STOCK_MEDIA_PAUSE)
        self.play_button = gtk.Button('', gtk.STOCK_MEDIA_PLAY)
        self.next_button = gtk.Button('', gtk.STOCK_MEDIA_NEXT)
        
        self.fs_button = gtk.Button('', gtk.STOCK_FULLSCREEN)
        self.unfs_button = gtk.Button('', gtk.STOCK_LEAVE_FULLSCREEN)

        e, hb = self.e_hb()
        hb.pack_start(self.prev_button, False, False)
        hb.pack_start(self.pause_button, False, False)
        hb.pack_start(self.play_button, False, False)
        hb.pack_start(self.next_button, False, False)
        
        self.controls.pack_start(e, False, False)
        
        e, hb = self.e_hb()
        hb.pack_start(self.fs_button, False, False)
        hb.pack_start(self.unfs_button, False, False)
        
        self.controls.pack_end(e, False, False)
        #### END OF SETTING UP CONTROLS ## ##

        self.main_VBox.pack_end(self.controls, False, True)

    def init_player(self):
        self.player = gst.element_factory_make("playbin2", "player")
        vol = self.player.get_property("volume")
        print "Xx"*20
        print "DEFAULT VOLUME:", vol
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        
        pix_data = """/* XPM */
static char * invisible_xpm[] = {
"1 1 1 1",
"       c None",
" "};"""
        color = gtk.gdk.Color()
        pix = gtk.gdk.pixmap_create_from_data(None, pix_data, 1, 1, 1, color, 
                                              color)
        self.invisble_cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)
        
        self.window.show_all()
        self.pause_button.hide()
        self.play_button.hide()
        self.controls.hide()
        self.show_hide_play_pause()
        if not self.alt_widget:
            self.window.hide()
        
        gobject.timeout_add(1000, self.update_time)
    
    def to_dict(self):
        # "tags": self.tags
        imgHash = ""
        if 'image' in self.tags:
            m = hashlib.md5()
            m.update(self.tags['image'])
            imgHash = m.hexdigest()
        if 'preview-image' in self.tags:
            m = hashlib.md5()
            m.update(self.tags['preview-image'])
            imgHash = m.hexdigest()
        return {
            "filename": self.filename,
            "pos_data": self.pos_data,
            "playingState": self.state_to_string(self.playingState),
            "imgHash": imgHash
        }

    def state_to_string(self, state):
        if state == PLAYING:
            return "PLAYING"
        if state == PAUSED:
            return "PAUSED"
        if state == STOPPED:
            return "STOPPED"
        return "ERROR"
        
    def show_hide_play_pause(self, *args):    
        if self.playingState in (STOPPED, PAUSED):
            self.play_button.show()
            self.pause_button.hide()
        else:
            self.play_button.hide()
            self.pause_button.show()
        if self.fullscreen:
            self.fs_button.hide()
            self.unfs_button.show()
        else:
            self.fs_button.show()
            self.unfs_button.hide()
        self.next_button.show()
        self.prev_button.show()
            
    def toggle_full_screen(self, *args):
        if self.fullscreen:
            self.fullscreen = False
            self.window.unfullscreen()
            self.movie_window.window.set_cursor(None)
        else:
            self.fullscreen = True
            self.window.fullscreen()
            self.movie_window.window.set_cursor(self.invisble_cursor)
        
        self.show_hide_play_pause()
        self.window.emit('check-resize')
    
    def on_scroll(self, widget, event):
        print "on_scroll:"
        gtk.gdk.threads_leave()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.seek("+5")
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.seek("-5")
        print "/on_scroll"

    def ind_on_scroll(self, widget, steps, direction):
        if direction == 0:
            self.seek("+5")
        else:
            self.seek("-5")
    
    def show_controls(self,*args):
        # print "show_controls"
        self.controls.show()
        self.time_label.show()
        self.show_hide_play_pause()
        if self.hide_timeout:
            gobject.source_remove(self.hide_timeout)
            self.hide_timeout = None
        self.hide_timeout = gobject.timeout_add(3000, self.hide_controls)
        # if self.fullscreen:
        self.movie_window.window.set_cursor(None)
        self.showing_controls = True

    def hide_controls(self):
        self.showing_controls = False
        self.controls.hide()
        self.time_label.hide()
        self.hide_timeout = None
        #if self.fullscreen:
        self.movie_window.window.set_cursor(self.invisble_cursor)

    def on_key_press(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname in ('f','F'):
            self.toggle_full_screen()

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')
                
        if keyname in ('Return', 'p', 'P', 'a', 'A', 'space'):
            self.show_controls()
            self.pause()
            
        if keyname == 'Up':
            self.seek("+5")
        
        if keyname == 'Down':
            self.seek("-5")
            
        if keyname == 'Right':
            self.next_button.emit('clicked')
        
        if keyname == 'Left':
            self.prev_button.emit('clicked')

    def next(self, *args, **kwargs):
        self.next_button.emit("clicked")

    def prev(self, *args, **kwargs):
        self.prev_button.emit('clicked')

    def start(self, *args, **kwargs):
        print "="*80
        self.tags = {}
        gc.collect()
        uri = self.filename
        if os.path.isfile(self.filename):
            self.filename = os.path.realpath(self.filename)
            if self.calculate_thread:
                print "self.calculate_thread:", self.calculate_thread
            else:
                self.calculate_thread = thread.start_new_thread(self.calculate_level)
            uri = "file://" + urllib.quote(self.filename)
            # print "QUOTED:%s" % urllib.quote(self.filename);
            uri = uri.replace("\\'", "%27")
            uri = uri.replace("'", "%27")
        if uri == "":
            print "empty uri"
            return
        print "playing uri:", uri
        self.player.set_state(STOPPED)
        self.player.set_property("uri", uri)

        # self.player.set_property("volume",self.volume)
        self.player.set_state(PLAYING)
        self.emit('state-changed', PLAYING)
        self.playingState = self.player.get_state()[1]
        try:
            self.dur_int = self.player.query_duration(self.time_format, None)[0]
        except gst.QueryError, e:
            print "gst.QueryError:", e
            self.dur_int = 0

        self.update_time()
        self.should_hide_window()

    def calculate_level(self):
        # gst-launch-1.0 -t filesrc location=/home/erm/dwhelper/test.mp4 ! decodebin ! audioconvert ! audioresample ! rganalysis ! fakesink
        cmd = [
            'gst-launch-1.0',
            '-t',
            'filesrc',
            'location=%s' % self.filename,
            '!',
            'decodebin',
            '!',
            'audioconvert',
            '!',
            'audioresample',
            '!',
            'rganalysis',
            '!',
            'fakesink'
        ]

        print "cmd:", cmd
        output = subprocess.check_output(cmd)
        """
        replaygain track peak: 1.000000
        replaygain track gain: -8.410000
        replaygain reference level: 89.000000"""
        print "output:", output

        match = re.search("replaygain\ track\ gain\:\ ([0-9\-\.]+)", output)
        print "match:", match
        print match.groups()
        gain = float(match.group(1))

        match = re.search("replaygain\ reference\ level:\ ([0-9\-\.]+)", output)
        print "match:", match
        print match.groups()
        reference_level = float(match.group(1))

        target_volume = reference_level + gain

        print "target_volume:", target_volume

        print "based on 1.0:", target_volume / 100.0
        self.player.set_property("volume", self.volume)
        # self.set_volume(target_volume)
        self.calculate_thread = None

    def should_hide_window(self):
        if self.player.get_property('n-video') > 0:
            self.alt_vbox.hide()
            self.movie_window.show()
            if not self.alt_widget:
                self.window.show()
                try:
                    self.window.set_size(self.width, self.height)
                    self.window.set_position(self.x, self.y)
                except:
                    pass
        else:
            self.alt_vbox.show()
            self.movie_window.hide()
            if not self.alt_widget:
                self.width, self.height = self.window.get_size()
                self.x, self.y = self.window.get_position()
                self.window.hide()

    def stop(self):
        self.player.set_state(STOPPED)
        
    def set_volume(self, widget, value):
        self.volume = value
        print "set_volume:", self.volume
        self.player.set_property("volume", self.volume)
        
    def convert_ns(self, time_int):
        time_int = time_int / 1000000000

        _hours = time_int / 3600
        time_int = time_int - (_hours * 3600)
        _mins = time_int / 60
        time_int = time_int - (_mins * 60)
        _secs = time_int
        
        if _hours:
            return "%d:%02d:%02d" % (_hours, _mins, _secs)

        if _mins:
            return "%d:%02d" % (_mins, _secs)

        return "0:%02d" % (_secs)

    def update_time(self, retry=True):
        #if self.playingState != PLAYING :
        #    print "update_time:NOT PLAYING"
        #    return True

        # print 'update_time';
        try:
            dur_int = self.player.query_duration(self.time_format, None)[0]
            dur_str = self.convert_ns(dur_int)
            self.dur_int = dur_int
        except:
            return True
        
        try:
            pos_int = self.player.query_position(self.time_format, None)[0]
        except:
            pos_int = 0

        if pos_int == 0 and retry:
            sleep(0.1)
            self.update_time(retry=False)
            return True
            
        pos_str = self.convert_ns(pos_int)
        left_int = (dur_int - pos_int)
        left_str = self.convert_ns(left_int)
        decimal = float(pos_int) / dur_int
        percent = "%.2f%%" % (decimal * 100)
        try:
            # print pos_int, dur_int, left_int, decimal, pos_str, dur_str, left_str, percent
            self.pos_int = pos_int
            self.left_int = left_int
            self.emit('time-status', pos_int, dur_int, left_int, decimal, 
                      pos_str, dur_str, left_str, percent)
            self.pos_data = {
                "pos_str": pos_str, 
                "dur_str": dur_str, 
                "left_str": left_str,
                "percent": percent,
                "pos_int": pos_int,
                "dur_int": dur_int,
                "left_int": left_int,
                "decimal": decimal,
                "min": 0,
                "max": dur_int,
                "value": pos_int,
                "playingState": self.state_to_string(self.playingState)
            }
        except TypeError, e:
            print "TypeError:",e
        
        return True
        
    def pause(self, *args, **kwargs):
        self.playingState = self.player.get_state()[1]
        if self.playingState == STOPPED:
            self.start()
        elif self.playingState == PLAYING:
            self.player.set_state(PAUSED)
        elif self.playingState == PAUSED:
            self.player.set_state(PLAYING)
            
        self.playingState = self.player.get_state()[1]
        self.emit('state-changed', self.playingState)
        self.update_time()

    def debug_message(self, gst_message):
        attribs_to_check = ['parse_clock_lost', 'parse_clock_provide',
                  'parse_duration', 'parse_error', 'parse_new_clock',
                  'parse_segment_done', 'parse_segment_start', 
                  # 'parse_state_changed', 
                  'parse_tag', 
                  'parse_warning']

        for k in attribs_to_check:
            try:
                res = getattr(gst_message, k)()
                print "-"*40,gst_message.type,"-"*40
                print k, res
                print "-"*40,'/',gst_message.type,"-"*40
            except:
                pass
    
    def on_message(self, bus, message):
        t = message.type
        # print "on_message:",t
        # self.debug_message(message)
        if t == gst.MESSAGE_STATE_CHANGED:
            # print "on_message parse_state_changed()", 
            # print message.parse_state_changed()
            return

        if t == gst.MESSAGE_STREAM_STATUS:
            # print "on_message parse_state_changed()", 
            # print message.parse_state_changed()
            return

        if t == gst.MESSAGE_EOS:
            print "END OF STREAM"
            self.player.set_state(STOPPED)
            self.emit('end-of-stream')
            return 

        if t == gst.MESSAGE_ERROR:
            self.player.set_state(STOPPED)
            err, debug = message.parse_error()
            print "Error: '%s'" % err, "debug: '%s'" % debug
            if err == 'Resource not found.':
                print "RETURNING"
                return
            self.emit('error', err, debug)
            return

        if t == gst.MESSAGE_TAG:
            for key in message.parse_tag().keys():
                msg = message.structure[key]
                if isinstance(msg, (gst.Date, gst.DateTime)):
                    self.tags[key] = "%s" % msg
                elif key not in ('image','private-id3v2-frame', 'preview-image',
                                 'private-qt-tag'):
                    print "tags[%s]=%s" % (key, msg )
                    self.tags[key] = "%s" % msg
                else:
                    if key == 'image':
                        self.tags["image-raw"] = msg
                    elif key == "preview-image":
                        self.tags["preview-image-raw"] = msg
                    print "tags[%s]=%s" % (key,"[Binary]")
                    data = {}
                    if isinstance(msg, list):
                        for i, v in enumerate(msg):
                            data[i] = base64.b64encode(msg[i])
                            data["%s-raw" % i] = msg[i]
                    elif isinstance(msg, dict):
                        for k, v in enumerate(msg):
                            data[k] = base64.b64encode(msg[k])
                            data[k+"-raw"] = msg[k]
                    else:
                        print "%s" % msg[0:10]
                        data = base64.b64encode(msg)
                    self.tags[key] = data

                    print self.tags[key]

                self.emit('tag-received', key, message.structure[key])
                return
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        print "on_sync_message:",message_name
        
        if message_name == "prepare-xwindow-id":
            print "*"*80
            self.window.show_all()
            self.imagesink = message.src
            self.imagesink.set_property("force-aspect-ratio", True)
            self.imagesink.set_xwindow_id(self.movie_window.window.xid)
            if self.fullscreen:
                gobject.idle_add(self.window.fullscreen)
            gobject.idle_add(self.emit,'show-window')
        elif message_name == 'missing-plugin':
            print "MISSING PLUGGIN"
            self.emit('missing-plugin')
        if message_name == 'playbin2-stream-changed':
            print "-"*80
            
    def control_seek(self, w, seek):
        print "control_seek:", seek
        self.seek(seek)
    
    def seek_ns(self, ns):
        ns = int(ns)
        print "SEEK_NS:", ns
        self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, ns)
        self.update_time()
    
    def seek(self, string):
        if self.pos_int <= 0:
            print "self.pos_int <= 0"
            return
        if self.seek_locked:
            return
        self.seek_locked = True

        string = str(string)
        string = string.strip()
        firstChar = string[0]
        lastChar = string[-1]
        seek_ns = None
        
        if firstChar in ('+','-'):
            # skip ahead x xeconds
            skip_second = int(string[1:]) * 1000000000
            if firstChar == '+':
                seek_ns = self.pos_int + skip_second
            else:
                seek_ns = self.pos_int - skip_second
        elif lastChar == '%':
            seek_ns = int(float(string[0:-1]) * 0.01 * self.dur_int)
        else:
            seek_ns = int(string) * 1000000000
        
        if seek_ns < 0:
            seek_ns = 0
        elif seek_ns > self.dur_int:
            self.seek_locked = False
            return
        
        try:
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, 
                                    seek_ns)
        except:
            print "ERROR SEEKING"
            self.seek_locked = False
            return
            
        self.pos_int = seek_ns
        print "SEEK_NS:",seek_ns
        self.seek_locked = False

    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, 
                       pos_str, dur_str, left_str, percent):
        if not self.showing_controls:
            return
        
        self.time_label.set_text(" -%s %s/%s" % (left_str, pos_str, dur_str) )


if __name__ == '__main__':

    import random
    gobject.threads_init()

    def next(*args):
        print "play_files"
        if len(files) == 0:
            print "done playing files"
            return
        f = files.pop(0)
        if currentFile:
            prevFiles.append(currentFile.pop())
        currentFile.append(f)
        print "f:",f
        if not f:
            print "f was empty"
            return
        player.filename = f
        player.start()


    def prev(*args):
        if not prevFiles:
            return
        if currentFile:
            files.insert(0,currentFile.pop())
        f = prevFiles.pop()
        currentFile.append(f)
        player.filename = f
        player.start()


    def status(w, *args):
        """ (56525313000L, 217583333333L, 161058020333L, 0.25978696131790086, 
             '00:56', '03:37', '02:41', '25.98%') """
        # print "status:", args
        return

    
    def error_msg(player, msg,debug):
        print "ERROR MESSAGE:", msg, ',', debug
        if not os.path.isfile(player.filename):
            player.emit('end-of-stream')


    def on_menuitem_clicked(item):
        label = item.get_label()
        if label == 'Pause':
            player.pause()
        elif label == 'Play':
            player.pause()
        elif label == 'Next':
            next()
        elif label == 'Prev':
            prev()
        elif label == 'Quit':
            gtk_main_quit()
        
        print "CLICKED:%s " % (item.get_label())


    def on_playing_state_changed(p, state):
        if state == gst.STATE_PLAYING:
            play_pause_item.set_label('Pause')
            play_pause_item.set_image(pause_img)
        elif state == gst.STATE_PAUSED:
            play_pause_item.set_label('Play')
            play_pause_item.set_image(play_img)


    def on_button_press(icon, event, **kwargs):
        print "on_button_press:",icon, event
        if event.button == 1:
            menu.popup(None, None, None, event.button, event.get_time())


    ind = gtk.StatusIcon()
    ind.set_name("player.py")
    ind.set_title("player.py")
    ind.connect("button-press-event", on_button_press)
    ind.set_from_stock(gtk.STOCK_MEDIA_PLAY)

    pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, 
                                         gtk.ICON_SIZE_BUTTON)
    play_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, 
                                        gtk.ICON_SIZE_BUTTON)
    
    menu = gtk.Menu()

    play_pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, 
                                              gtk.ICON_SIZE_BUTTON)
    play_pause_item = gtk.ImageMenuItem("Pause")
    play_pause_item.set_image(play_pause_img)
    play_pause_item.connect("activate", on_menuitem_clicked)
    play_pause_item.show()
    menu.append(play_pause_item)

    next_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, 
                                        gtk.ICON_SIZE_BUTTON)
    next_item = gtk.ImageMenuItem("Next")
    next_item.set_image(next_img)
    next_item.connect("activate", on_menuitem_clicked)
    next_item.show()
    menu.append(next_item)

    prev_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, 
                                        gtk.ICON_SIZE_BUTTON)
    prev_item = gtk.ImageMenuItem("Prev")
    prev_item.set_image(prev_img)
    prev_item.connect("activate", on_menuitem_clicked)
    prev_item.show()
    menu.append(prev_item)

    quit_item = gtk.ImageMenuItem("Quit")
    quit_item.connect("activate", on_menuitem_clicked)
    img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)
    quit_item.set_image(img)
    quit_item.show()
    menu.append(quit_item)

    prevFiles = []
    currentFile = []
    files = []
    args = sys.argv[1:]
    cwd = os.getcwd()
    shuffle = False

    for arg in args:
        if os.path.exists(arg) or arg.startswith("rtsp://") or \
           arg.startswith("rtmp://") or arg.startswith("http://") or \
           arg.startswith("https://"):
            print "file:%s" % arg
            files.append(arg)
        elif arg in ('-s', '--shuffle', '-shuffle'):
            shuffle = True

    if shuffle:
        print "SHUFFLE"
        random.shuffle(files)

    player = Player()
    player.connect('end-of-stream', next)
    player.connect('time-status', status)
    player.connect('error', error_msg)
    ind.connect('scroll-event', player.on_scroll)
    player.connect('state-changed', on_playing_state_changed)

    player.next_button.connect('clicked', next)
    player.prev_button.connect('clicked', prev)
    gobject.idle_add(next)
    while gtk.events_pending(): 
        gtk.main_iteration(False)
    gtk.main()
