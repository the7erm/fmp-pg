#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# player1.py -- gstreamer 1.0 player
#    Copyright (C) 2015 Eugene Miller <theerm@gmail.com>
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

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango,\
                          GLib, Gio, GdkPixbuf
GObject.threads_init()
Gst.init(None)
import sys
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import mutagen
import os
import urllib
import math
from random import shuffle
from pprint import pprint
from datetime import datetime
from copy import deepcopy
from time import sleep, time
from utils import utcnow

PLAYING = Gst.State.PLAYING
PAUSED = Gst.State.PAUSED
STOPPED = Gst.State.NULL
READY = Gst.State.READY

time_format = Gst.Format(Gst.Format.TIME)

from log_class import Log, logging
logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (
    '',
    '.avi',
    '.divx',
    '.flac',
    '.flv',
    '.m4a',
    '.m4v',
    '.mov',
    '.mp3',
    '.mp4',
    '.mpeg',
    '.mpg',
    '.ogg',
    '.vorb',
    '.vorbis',
    '.wav',
    '.wma',
    '.wmv',
)

debug_threads = False

def wait(*args):
    now = "%s " % datetime.now()
    msg = now + " ".join(map(str, args))
    if debug_threads:
        print "++START WAIT "+msg
    threads_leave("\t" + msg)
    threads_enter("\t" + msg)
    if Gtk.events_pending():
        while Gtk.events_pending():
            if debug_threads:
                print "\t\tevents_pending " + msg
            Gtk.main_iteration()
    threads_leave("\t" + msg)
    if debug_threads:
        print "--END WAIT "+msg

def threads_enter(*args):
    Gdk.threads_enter()
    if debug_threads:
        print "ENTER " + " ".join(map(str, args))

def threads_leave(*args):
    Gdk.threads_leave()
    if debug_threads:
        print "LEAVE " + " ".join(map(str, args))

TOP_SPAN = '<span foreground="black" size="large"><b>%s</b></span>'
PACK_PADDING = 0

class PlayerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Player(GObject.GObject, Log):
    __name__ = 'Player'
    logger = logger
    __gsignals__ = {
        'state-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                          (object,)),
        'uri-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                        (object,)),
        'time-status': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                        (object,)),
        'artist-title-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                                 (object,)),
        'hide-controls': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                          (object,)),
        'fullscreen': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                          (object,)),
        'show-controls': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE,
                          (object,)),
    }
    def __init__(self, uri=None, resume_percent=0, state='PLAYING'):
        # Player.__init__()
        GObject.GObject.__init__(self)
        self.fullscreen = False
        self.is_video = False
        self.showing_controls = True
        self.debug_messages = []
        self.artist_title = ""
        self.artist = ""
        self.title = ""
        self.use_state_cache_until = 0
        self.state_cache = False
        self.uri_path = ""
        self.last_time_status = {}
        self.duration_cache = {}
        self.pipeline = None
        self.filename = ""
        self.last_good_position = 0
        self.last_good_duration = 0
        self.last_state = None
        self.seek_lock = False
        self.svg_path = self.get_svg_path()
        self.init_window()

        self.init_player(uri=uri)

        self.state = state
        GObject.timeout_add_seconds(1, self.time_status)

    def init_window(self):
        # Player.init_window()

        self.pixbuf = GdkPixbuf.Pixbuf().new_from_file(self.svg_path)
        self.temp_height = 0
        self.temp_width = 0
        self.show_controls_time = 0
        self.window = Gtk.Window()
        self.init_window_image()
        self.window.set_default_size(400, 300)
        self.window.set_resizable(True)
        self.window.set_title("Video-Player")

        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK |
                               Gdk.EventMask.BUTTON_PRESS_MASK |
                               Gdk.EventMask.SCROLL_MASK |
                               Gdk.EventMask.SMOOTH_SCROLL_MASK |
                               Gdk.EventMask.POINTER_MOTION_MASK |
                               Gdk.EventMask.POINTER_MOTION_HINT_MASK)

        self.main_vbox = Gtk.VBox()
        self.window.add(self.main_vbox)

        self.init_top_hbox()
        self.init_stack()

        self.init_drawing_area()
        self.init_debug_window()

        self.init_bottom_hbox()

        self.init_window_connections()
        self.drawingarea.hide()

    def init_window_image(self):
        img_path = self.get_img_path()

        self.window.set_icon_from_file(os.path.join(img_path, "tv.png"))

    def init_top_hbox(self):
        # Player.init_top_hbox()
        self.top_hbox = Gtk.HBox()

        self.file_label = Gtk.Label()
        self.file_label.set_line_wrap(True)
        self.file_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.file_label.set_alignment(0, 0)
        self.file_label.set_ellipsize(Pango.EllipsizeMode.MIDDLE)

        self.time_label = Gtk.Label()
        self.time_label.set_line_wrap(True)
        self.time_label.set_line_wrap_mode(Pango.WrapMode.WORD_CHAR)
        self.time_label.set_alignment(1, 0)
        self.time_label.set_ellipsize(Pango.EllipsizeMode.START)
        self.top_hbox.pack_start(self.file_label, True, True, PACK_PADDING)
        self.top_hbox.pack_start(self.time_label, False, True, PACK_PADDING)
        self.main_vbox.pack_start(self.top_hbox, False, True, PACK_PADDING)

    def init_stack(self):
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        self.main_vbox.pack_start(self.stack_switcher, False, True,
                                  PACK_PADDING)
        self.main_vbox.pack_start(self.stack, True, True, PACK_PADDING)

    def init_drawing_area(self):

        self.drawingarea = Gtk.DrawingArea()
        self.init_alt_drawing_area()

        self.video_area_vbox = Gtk.VBox()
        self.video_area_vbox.pack_start(
            self.alt_drawingarea_vbox, True, True, PACK_PADDING)
        self.video_area_vbox.pack_start(self.drawingarea, True, True,
                                        PACK_PADDING)
        self.video_area_vbox.show_all()
        self.stack.add_titled(self.video_area_vbox, "Video", "Video")
        self.drawingarea.add_events(Gdk.EventMask.POINTER_MOTION_MASK |
                                    Gdk.EventMask.POINTER_MOTION_HINT_MASK)

        self.drawingarea.connect("motion-notify-event", self.show_controls)

    def init_alt_drawing_area(self):
        self.alt_drawingarea_vbox = Gtk.VBox()
        self.init_playing_image_sbox()

    def init_playing_image_sbox(self):
        self.playing_image_sbox = Gtk.ScrolledWindow()
        self.playing_image_sbox.set_policy(Gtk.PolicyType.AUTOMATIC,
                                           Gtk.PolicyType.AUTOMATIC)

        self.playing_image = Gtk.Image()
        self.playing_image_sbox.add_with_viewport(self.playing_image)
        self.alt_drawingarea_vbox.pack_start(
            self.playing_image_sbox, True, True, PACK_PADDING)

    def init_debug_window(self):
        self.debug_text_view = Gtk.TextView()
        self.debug_text_buffer = Gtk.TextBuffer()
        self.debug_scrolled_window = Gtk.ScrolledWindow()
        self.debug_scrolled_window.add(self.debug_text_view)
        self.debug_text_view.set_editable(False)
        self.debug_text_view.set_buffer(self.debug_text_buffer)
        self.debug_text_view.set_wrap_mode(Gtk.WrapMode.WORD)

        self.stack.add_titled(self.debug_scrolled_window, "Debug", "Debug")

    def init_bottom_hbox(self):
        # Controls
        self.init_controls()

        self.bottom_hbox = Gtk.HBox()
        self.status_bar = Gtk.Statusbar()
        self.bottom_hbox.pack_start(self.prev_btn, False, True, PACK_PADDING)
        self.bottom_hbox.pack_start(self.pause_btn, False, True, PACK_PADDING)
        self.bottom_hbox.pack_start(self.next_btn, False, True, PACK_PADDING)

        self.bottom_hbox.pack_start(self.status_bar, False, True, PACK_PADDING)
        self.main_vbox.pack_start(self.bottom_hbox, False, True, PACK_PADDING)
        self.push_status("Started")

    def init_controls(self):
        # Player.init_controls()
        self.prev_btn = Gtk.Button()
        prev_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PREVIOUS, Gtk.IconSize.BUTTON)
        self.prev_btn.set_image(prev_img)

        self.pause_btn = Gtk.Button()
        self.play_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON)
        self.pause_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON)

        self.pause_btn.set_image(self.play_img)

        self.next_btn = Gtk.Button()
        next_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_NEXT, Gtk.IconSize.BUTTON)
        self.next_btn.set_image(next_img)

        self.pause_btn.connect("clicked", self.pause)
        self.connect('state-changed', self.on_state_changed)

    def init_window_connections(self):
        self.window.connect('key-press-event', self.on_key_press)
        self.window.connect('motion-notify-event', self.show_controls)
        self.window.connect('button-press-event', self.pause)
        self.window.connect("scroll-event", self.on_scroll)
        self.window.connect('destroy', self.quit)
        self.window.connect("check_resize", self.on_check_resize)
        # self.window.connect("motion_notify_event", self.on_motion_notify)
        self.window.show_all()

        try:
            self.xid = self.drawingarea.get_property('window').get_xid()
        except AttributeError, e:
            print "AttributeError:", e



    def on_artist_title_changed(self, player, artist_title):
        # self.file_label.set_text(artist_title)
        self.file_label.set_markup(TOP_SPAN % self.escape(artist_title))

    def on_state_change(self, player, state):
        # Player.on_state_change()
        print "on_state_change"
        self.show_video_window()

    def show_video_window(self):
        print "show_video_window"
        if self.playbin.get_property('n-video'):
            self.drawingarea.show()
            self.alt_drawingarea_vbox.hide()
            self.is_video = True
        else:
            self.drawingarea.hide()
            self.alt_drawingarea_vbox.show()
            self.is_video = False

        self.hide_controls()
        return False


    def get_time_status(self):
        # Player.get_time_status()
        position = self.position
        duration = self.duration
        remaining = duration - position
        try:
            decimal = (position / float(duration))
        except:
            decimal = 0
        obj = {
            'position': position,
            'duration': duration,
            'remaining': remaining,
            'percent_played': decimal * 100,
            'decimal_played': decimal,
            'position_str': self.format_ns(position),
            'duration_str': self.format_ns(duration),
            'remaining_str': "-%s" % self.format_ns(remaining),
            'state': self.state_string
        }
        # print "self.state_string:",self.state_string
        return obj

    def escape(self, string):
        find_replace = (
            ("&","&amp;"),
            ("<","&lt;"),
            (">","&gt;"),
        )
        for find, replace in find_replace:
            string = string.replace(find, replace)

        return string

    def time_status(self):
        print "time_status()"
        # Player.time_status()
        Gdk.threads_leave()
        obj = self.get_time_status()

        if obj['state'] != self.last_state:
            self.last_state = self.state_string
            # self.file_label.set_text(self.filename)
            #if not self.seek_lock:
            #  self.emit('state-changed', self.state)
        #if obj == self.last_time_status:
        #    return True

        self.last_time_status = deepcopy(obj)
        obj['str'] = "%s %s/%s" % (
            obj['remaining_str'],
            obj['position_str'],
            obj['duration_str']
        );
        Gdk.threads_enter()
        self.time_label.set_markup(TOP_SPAN % self.escape(obj['str']))
        Gdk.threads_leave()
        # print "time status obj:", obj
        obj['now'] = utcnow()
        obj['now_iso'] = obj['now'].isoformat()
        self.emit('time-status', obj)
        GObject.idle_add(self.show_video_window)
        # self.show_video_window()

        return True

    def format_ns(self, ns):
        # Player.format_ns()
        if not ns:
            return "0:00"
        seconds = int(math.floor(ns / 1000000000))
        if not seconds:
            return "0:00"
        hours = math.floor(seconds / (60 * 60))
        seconds = seconds - (hours * 60 * 60)
        minutes = math.floor(seconds / 60)
        seconds = seconds - (minutes * 60)
        if not hours:
            return "%d:%02d" % (minutes, seconds)
        return "%d:%02d:%02d" % (hours, minutes, seconds)

    def on_window_resize(self, *args):
        # Player.on_window_resize()
        print "on_window_resize()"
        self.show_video_window()
        self.temp_height = 0
        self.temp_width = 0
        self.on_check_resize()

    def on_check_resize(self, *args):
        print "on_check_resize()"
        # Player.on_check_resize()
        if not hasattr(self, 'pixbuf'):
            return
        boxAllocation = self.playing_image_sbox.get_allocation()
        self.playing_image.set_allocation(boxAllocation)
        self.resizeImage(boxAllocation.width, boxAllocation.height)

    def resizeImage(self, allocation_width, allocation_height, force=False):
        print "resizeImage()"
        # Player.resizeImage()
        # allocation_height = allocation_height - 40
        if self.temp_height != allocation_height or self.temp_width != allocation_width or force:
            pb_width = self.pixbuf.get_width()
            pb_height = self.pixbuf.get_height()
            percent =  allocation_height / float(pb_height)
            width = int(percent * pb_width)
            height = int(percent * pb_height)

            if width > allocation_width:
                percent =  allocation_width / float(pb_width)
                width = int(percent * pb_width)
                height = int(percent * pb_height)

            self.temp_height = allocation_height
            self.temp_width = allocation_width

            pixbuf = self.pixbuf.scale_simple(
                width, height, GdkPixbuf.InterpType.BILINEAR)

            self.playing_image.set_from_pixbuf(pixbuf)
            self.playing_image.set_allocation(
                self.playing_image_sbox.get_allocation())

        # self.image.connect('expose-event', self.on_image_resize, self.window)

    def push_status(self, msg):
        # Player.push_status()
        self.log_debug(".push_status:%s", msg)
        # self.alt_drawingarea_vbox_label.set_text(msg)
        context_id = self.status_bar.get_context_id(msg)
        self.status_bar.push(context_id, msg)
        msg = "%s %s " % (datetime.now(), msg)
        self.debug_messages.insert(0, msg)
        if len(self.debug_messages) > 35:
            self.debug_messages = self.debug_messages[0:35]
        self.debug_text_buffer.set_text("\n".join(self.debug_messages))

    def on_key_press(self, widget, event):
        # Player.on_key_press()
        Gdk.threads_leave()
        keyname = Gdk.keyval_name(event.keyval)
        self.show_controls()
        self.log_debug(".on_key_press:%s", keyname)
        self.push_status("Player.on_key_press:"+keyname)
        if keyname in ('space', 'Return'):
            self.pause()
            return True

        if keyname in ('Up', 'KP_Up', 'AudioForward'):
            self.position = "+5"
            return True

        if keyname in ('Down', 'KP_Down', 'AudioRewind'):
            self.position = "-5"
            return True

        if keyname in ('Page_Up','KP_Page_Up'):
            self.position = "+30"
            return True

        if keyname in ('Page_Down','KP_Page_Down'):
            self.position = "-15"
            return True

        if keyname in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"):
            self.position = keyname+":00"
            return True

        if keyname in ("q", "Escape"):
            self.quit()
            return True

        if keyname in ('f', 'F'):
            if self.fullscreen:
                self.fullscreen = False
                self.window.unfullscreen()
            else:
                self.fullscreen = True
                self.window.fullscreen()
            self.show_video_window()
            self.show_controls()
            self.emit('fullscreen', self.fullscreen)

        return False

    def show_controls(self, *args, **kwargs):
        if self.is_video and self.fullscreen:
            self.show_controls_time = time()
            self.bottom_hbox.show()
            self.stack_switcher.show()
            self.top_hbox.show()
            self.emit('show-controls', {})

    def hide_controls(self, *args, **kwargs):
        self.log_debug(".hide_controls()")
        if self.is_video and self.fullscreen and self.show_controls_time < (time() - 5):
            self.showing_controls = False
            self.bottom_hbox.hide()
            self.stack_switcher.hide()
            self.top_hbox.hide()
            self.emit('hide-controls', {})
        else:
            self.showing_controls = True
            self.bottom_hbox.show()
            self.stack_switcher.show()
            self.top_hbox.show()
            self.emit('show_controls', {})

    def pause(self, *args, **kwargs):
        # Player.pause()
        Gdk.threads_leave()
        self.state = 'TOGGLE'
        self.show_controls()

    def on_scroll(self, widget, event):
        # Player.on_scroll()
        Gdk.threads_leave()
        if event.direction == Gdk.ScrollDirection.UP:
            self.position = "+5"
        if event.direction == Gdk.ScrollDirection.DOWN:
            self.position = "-5"
        self.show_controls()

    @property
    def position(self):
        # Player.position()
        Gdk.threads_leave()
        try:
           res, position = self.pipeline.query_position(time_format)
        except Exception as e:
            self.log_error(".position ERROR GETTING POSITION:%s", e)
            return self.last_good_position

        if res and position:
            self.last_good_position = position
        else:
            self.log_error(".position FAIL GETTING RES:%s %s", res, position)
        return self.last_good_position

    @position.setter
    def position(self, position):
        # Player.position()
        Gdk.threads_leave()
        if self.seek_lock:
            return
        self.seek_lock = True
        if isinstance(position, (str, unicode)):
            position = self.parse_position_string(position)

        if position < 0:
            position = 0

        if self.duration == 0:
            self.log_error("DURATION IS 0")
            self.seek_lock = False
            return
        """


        self_duration = self.duration
        if position > self_duration:
            position = self_duration
        """
        Gdk.threads_enter()
        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH,
            position
        )
        self.push_status("SEEK:%s" % (self.format_ns(position)))
        Gdk.threads_leave()
        print "self.state:", self.state_string
        self.use_state_cache_until = 0
        self.last_good_position = position
        self.seek_lock = False

    def parseInt(self, string):
        # Player.parseInt()
        value = 0
        try:
            value = int(string)
        except:
            pass
        return value

    def parse_minutes_seconds(self, position):
        # Player.parse_minutes_seconds()
        parts = position.split(':')
        part_len = len(parts)
        seconds = 0
        minutes = 0
        hours = 0
        if part_len == 3:
            hours = self.parseInt(parts[0])
            minutes = self.parseInt(parts[1])
            seconds = self.parseInt(parts[2])
        elif part_len == 2:
            minutes = self.parseInt(parts[0])
            seconds = self.parseInt(parts[1])
        return (
                 (hours * 3600) +
                 (minutes * 60) +
                 seconds
               ) * Gst.SECOND

    def parse_percent(self, position):
        # Player.parse_percent()
        print "BEFORE:", position[:-1]
        try:
            percent = float(position[:-1]) * 0.01
        except:
            percent = 0
        print "AFTER:", percent
        if percent < 0 or percent > 1:
            self.seek_lock = False
            raise PlayerError('invalid percent %r' % position)
        duration = self.duration
        print "DURATION:", duration
        if duration == 0:
            return 0
        seek_to = duration * percent
        print "SEEK_TO:", seek_to
        return seek_to

    def parse_pos_negative_position(self, position):
        # Player.parse_pos_negative_position()
        seconds = int(position[1:])
        if position.startswith("-"):
            seconds = -seconds
        if seconds:
            seek_to = self.position + (seconds * Gst.SECOND)
            self.seek_lock = False
            return seek_to

        return int(position)

    def parse_position_string(self, position):
        # Player.parse_position_string()
        if ':' in position:
            position = self.parse_minutes_seconds(position)
        elif position.startswith("+") or position.startswith("-"):
            position = self.parse_pos_negative_position(position)
        elif position.endswith("%"):
            try:
                position = self.parse_percent(position)
            except PlayerError, e:
                self.log_error("PlayerError:%s", e)
                return 0
        else:
            position = int(position)
        return position

    @property
    def duration(self):
        # Player.duration()
        Gdk.threads_leave()
        cnt = 0
        res = False
        duration = 0
        if self.uri in self.duration_cache:
            return self.duration_cache[self.uri]
        try:
            Gdk.threads_enter()
            while cnt < 100 and not (res and duration):
                res, duration = self.pipeline.query_duration(time_format)
                sleep(0.1)
                cnt += 1
            if cnt > 1:
                print "TRIES:", cnt
            Gdk.threads_leave()
        except:
            print "ERROR GETTING DURATION"
            Gdk.threads_leave()
            return self.last_good_duration

        if res and duration:
            self.duration_cache[self.uri] = duration
            self.last_good_duration = duration

        return self.last_good_duration

    def init_player(self, uri=None):
        # Player.init_player()
        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)
        self.bus.connect('message::tag', self.on_tag)

        # This is needed to make the video output in our DrawingArea:
        self.bus.enable_sync_message_emission()
        self.bus.connect('sync-message::element', self.on_sync_message)

        # Create GStreamer elements
        self.playbin = Gst.ElementFactory.make('playbin', None)

        # Add playbin to the pipeline
        self.pipeline.add(self.playbin)

        # Set properties
        if uri is not None:
            self.uri = uri
            self.playbin.set_property('uri', self.uri)
            self.state = PLAYING

        self.connect('artist-title-changed', self.on_artist_title_changed)
        self.connect("state-changed", self.on_state_change)

    def quit(self, *args, **kwargs):
        # Player.quit()
        Gdk.threads_leave()
        Gdk.threads_enter()
        self.pipeline.set_state(STOPPED)
        Gtk.main_quit()
        Gdk.threads_leave()

    @property
    def uri(self):
        # Player.uri()
        return self.uri_path

    def get_img_path(self):
        img_path = ""
        possible_paths = [
            os.path.join(sys.path[0],"static", "images"),
            os.path.join(sys.path[0], "..", "static", "images"),
            os.path.join(sys.path[0], "..", "images")
        ]
        for p in possible_paths:
            if os.path.exists(p):
                img_path = p
                break
        return img_path

    def get_svg_path(self):
        img_path = self.get_img_path()
        svg_path = os.path.join(img_path, "fmp-logo.svg")
        return svg_path

    @uri.setter
    def uri(self, value):
        # Player.uri()
        if not value:
            return
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
            self.svg_path, 800, 600, preserve_aspect_ratio=True)
        self.temp_width = 0
        self.temp_height = 0
        self.on_check_resize()
        Gdk.threads_leave()
        if value is None:
            return
        uri = value
        if os.path.exists(value):
            value = os.path.realpath(value)
            self.filename = value
            uri = "file://" + urllib.quote(value)
        else:
            self.filename = ""

        changed = uri != self.uri
        self.uri_path = uri
        if not uri:
            return

        if changed:
            Gdk.threads_enter()
            self.playbin.set_property('uri', self.uri)
            Gdk.threads_leave()
            self.push_status("uri:%s" % urllib.unquote(self.uri))
            self.artist = ""
            self.title = ""
            self.artist_title = urllib.unquote(os.path.basename(self.uri))
            self.emit('uri-changed', self.uri)
            self.emit('artist-title-changed', self.artist_title)
            self.on_check_resize()

    @property
    def state(self):
        print "state()"
        # Player.state()
        Gdk.threads_leave()
        self.pipeline_ready()
        if self.use_state_cache_until < time() or not self.state_cache:
            Gdk.threads_enter()
            self.state_cache = self.playbin.get_state(0)
            Gdk.threads_leave()
        else:
            log_debug(" USING STATE CACHE self.state_cache %s",
                      self.state_cache[1])
        return self.state_cache[1]

    @state.setter
    def state(self, value=None):
        # Player.state()
        Gdk.threads_leave()
        self.pipeline_ready()
        self.log_info(' SET STATE:%s', value)
        if value not in (PLAYING, PAUSED, STOPPED):
            self.state_string = value
            return

        old_state = self.state
        Gdk.threads_enter()
        self.pipeline.set_state(value)
        Gdk.threads_leave()
        self_state = self.state
        if old_state != self_state or value != self_state:
            self.last_state = value
            self.emit('state-changed', value)
        self.log_info(' /SET STATE:%s', value)

    def on_state_changed(self, player, value):
        print "on_state_changed()"
        # Player.on_state_changed()
        Gdk.threads_leave()
        state = self.state
        Gdk.threads_enter()
        if state in(PAUSED, STOPPED, READY):
            logger.debug("SET IMAGE: PLAY")
            self.pause_btn.set_image(self.play_img)
        elif state == PLAYING:
            logger.debug("SET IMAGE: PAUSE")
            self.pause_btn.set_image(self.pause_img)
        else:
            logger.debug("INVALID STATE: %s" % state)
        Gdk.threads_leave()
        self.push_status("state-changed:%s" % self.state_to_string(value))

    def pipeline_ready(self):
        # Player.pipeline_ready()
        Gdk.threads_leave()
        if not self.pipeline:
            raise PlayerError('Player.player is %r\nInfo:%s' % (
                self.pipeline, sys.exc_info()[0]))

    @property
    def state_string(self):
        # Player.state_string()
        return self.state_to_string(self.state)

    def state_to_string(self, state):
        # Player.state_to_string()
        if state == PLAYING:
            return "PLAYING"
        if state == PAUSED:
            return "PAUSED"
        if state == STOPPED:
            return "STOPPED"
        if state == READY:
            return "READY"
        return "ERROR"

    @state_string.setter
    def state_string(self, value=''):
        # Player.state_string()
        Gdk.threads_leave()
        if not value:
            raise ValueError('Invalid state_string %r' % value)
        value_upper = str(value).upper()
        if value_upper == 'READY':
            value_upper = 'PLAYING'

        if value_upper not in ('PLAY', 'PLAYING', 'PAUSED', 'PAUSE',
                               'STOPPED', 'STOP', 'START', 'TOGGLE'):
            raise ValueError('Invalid state_string %r' % value)

        if value_upper in ('TOGGLE',):
            state = self.state
            if state == PLAYING:
                self.state = PAUSED
                return
            if state in (STOPPED, PAUSED, READY):
                self.state = PLAYING
                return
            return

        if value_upper in ('PLAYING', 'PLAY', 'START'):
            self.state = PLAYING
            return

        if value_upper in ('PAUSE', 'PAUSED'):
            self.state = PAUSED
            return

        if value_upper in ('STOP', 'STOPPED'):
            self.state = STOPPED
            return

        raise ValueError('Invalid state_string %r nothing found for %r' %
            (value, value))

    def on_sync_message(self, bus, msg):
        # Player.on_sync_message()
        Gdk.threads_leave()
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print "-"*100
            print('prepare-window-handle')
            Gdk.threads_enter()
            msg.src.set_window_handle(self.xid)
            Gdk.threads_leave()

    def on_eos(self, bus, msg):
        # Player.on_eos()
        Gdk.threads_leave()
        print('Player.on_eos(): seeking to start of video')

    def print_tag(self, tag_list, tag_name):
        # Player.print_tag()
        if tag_name == 'artist':
            res, artist = tag_list.get_string(tag_name)
            if res and artist:
                self.artist = artist

        if tag_name == 'title':
            res, title = tag_list.get_string(tag_name)
            if res and title:
                self.title = title

        if tag_name in ('artist', 'title') and self.artist and self.title:
            self.artist_title = "%s - %s" % (self.artist, self.title)
            self.emit('artist-title-changed', self.artist_title)

        if tag_name == 'image':
            if os.path.exists(self.filename):
                media_tags = MediaTags(self.filename)
                # print "tags_hard.get('APIC'):", media_tags.tags_combined.get('image')
                image = media_tags.tags_combined.get('image')
                if image:
                    if isinstance(image, list):
                        image = image[0]
                        if not hasattr(image, 'data'):
                            print "NO DATA:",image.data
                            return
                    print "WRITING IMAGE"
                    fp = open("/tmp/tmp.img", 'wb')
                    fp.write(image.data)
                    fp.close()
                    self.set_image()
        else:
            try:
                print "tag_list.get_string(%s):%s" % (tag_name,
                    tag_list.get_string(tag_name))
            except Exception as e:
                print "Exception:", e


    def set_image(self):
        # Player.set_image()
        print "set_image()"
        self.pixbuf = GdkPixbuf.Pixbuf.new_from_file("/tmp/tmp.img")
        self.temp_width = 0
        self.temp_height = 0
        self.on_check_resize()

    def on_tag(self, bus, msg):
        # Player.on_tag()
        print "ON_TAG", bus, msg
        tag_list = msg.parse_tag()
        tag_list.foreach(self.print_tag)


    def on_error(self, bus, msg):
        # Player.on_error()
        Gdk.threads_leave()
        error = msg.parse_error()
        print 'Player.on_error():', error[0]


class Playlist(Log):
    __name__ == 'Playlist'
    logger = logger
    def __init__(self, files=[], player=None, index=0):
        self.index = index
        self.files = files
        if player is None:
            self.player = Player()
        else:
            self.player = player

        try:
            self.set_player_uri()
        except IndexError:
            pass
        self.player.state = 'PLAYING'
        self.player.bus.connect('message::eos', self.on_eos)
        self.player.bus.connect('message::error', self.on_error)
        self.player.window.connect("key-press-event", self.on_key_press)
        self.player.prev_btn.connect("clicked", self.prev)
        self.player.next_btn.connect("clicked", self.next)
        self.init_connections()

    def init_connections(self):
        return

    def on_key_press(self, widget, event):
        Gdk.threads_leave()
        keyname = Gdk.keyval_name(event.keyval)
        self.log_debug(".on_key_press keyname:%s", keyname)

        if keyname in ('Right', 'KP_Right', 'AudioNext'):
            self.next()
            return True

        if keyname in ('Left', 'KP_Left', 'AudioPrev'):
            self.prev()
            return True

        return False

    def next(self, *args, **kwargs):
        # TODO emit next()
        self.inc_index()
        self.player.push_status("Next")

    def prev(self, *args, **kwargs):
        # TODO emit prev()
        self.deinc_index()
        self.player.push_status("Prev")

    def on_eos(self, bus, msg):
        self.log_debug(".on_eos()")
        self.inc_index()
        self.player.push_status("End of stream")

    def on_error(self, bus, msg):
        error = msg.parse_error()[0]
        self.log_error("*"*100)
        self.log_error(".on_error ERROR:%s", error.message)
        self.log_error(".on_error CODE:%s", error.code)
        self.player.push_status("----------------")
        self.player.push_status("Filename     :%s" % self.player.filename)
        self.player.push_status("URI          :%s" % self.player.uri)
        self.player.push_status("Error message:%s" % error.message)
        self.player.push_status("Error code   :%s" % error.code)
        self.player.push_status("----------------")
        codes = [
            'CODEC_NOT_FOUND',
            'DECODE',
            'DECRYPT',
            'DECRYPT_NOKEY',
            'DEMUX',
            'ENCODE',
            'FAILED',
            'FORMAT',
            'MUX',
            'NOT_IMPLEMENTED',
            'NUM_ERRORS',
            'TOO_LAZY',
            'TYPE_NOT_FOUND',
            'WRONG_TYPE',
        ]

        for code in codes:
            if error.code == getattr(Gst.StreamError, code):
                self.log_error(".on_error CODE TYPE:%s", code)

        self.log_error(".player.filename:%s", self.player.filename)
        if error.code in(Gst.StreamError.TYPE_NOT_FOUND,
                         Gst.StreamError.WRONG_TYPE):
            self.set_error_message(error)
            self.inc_index()
            return

        if error.code in (Gst.StreamError.NOT_IMPLEMENTED,):
            if not self.player.uri:
                self.player.show_video_window()
                msg = "No Uri"
                self.player.push_status(msg)
            else:
                self.set_error_message(error)
            return

        # import pdb; pdb.set_trace()
        #if 'Could not determine type of stream.' in msg.parse_error():
        #    inc_index();

    def set_error_message(self, error):
        self.player.show_video_window()
        msg = "%s\n\t%s" % (error.message,
                          self.player.uri.replace("%20", " "))
        self.player.push_status(msg)

    def inc_index(self):
        # todo pre_inc_index()
        self.index += 1
        self.sanity_check()

    def deinc_index(self):
        # todo pre_deinc_index()
        self.index -= 1
        self.sanity_check()

    def sanity_check(self):
        last_index = len(self.files) - 1
        if self.index > last_index:
            self.index = 0

        if self.index < 0:
            self.index = last_index

        self.player.state = STOPPED
        self.set_player_uri()
        # print "SANITY CHECK", self.player.uri
        self.log_debug(".sanity_check:%s", self.player.uri)
        self.player.state = PLAYING

    def set_player_uri(self):
        self.player.uri = self.files[self.index]

class TrayIcon(Log):
    __name__ = 'TrayIcon'
    logger = logger
    def __init__(self, player=None, playlist=None, state="PLAYING"):
        self.player = player
        self.playlist = playlist
        self.pause_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                                 Gtk.IconSize.BUTTON)
        self.play_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                  Gtk.IconSize.BUTTON)
        if player is None:
            self.player = self.playlist.player
        self.init_icon(state)
        self.init_menu(state)
        self.player.connect("state-changed", self.on_state_change)
        self.player.connect('artist-title-changed',
            self.on_artist_title_changed)

    def init_icon(self, state="PLAYING"):
        self.ind = Gtk.StatusIcon()
        if state != 'PLAYING':
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PLAY)
        else:
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PAUSE)
        self.ind.set_name("player.py")
        self.ind.set_title("player.py")
        self.ind.connect("button-press-event", self.on_button_press)
        self.ind.connect("scroll-event", self.player.on_scroll)
        self.ind.set_tooltip_text(self.player.artist_title)


    def on_artist_title_changed(self, player, artist_title):
        self.ind.set_tooltip_text(artist_title)

    def on_state_change(self, player, state):
        self.log_debug('.on_state_change: player:%s  state:%s', player, state)
        if state != PLAYING:
            play_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY,
                                                 Gtk.IconSize.BUTTON)
            self.play_pause_item.set_label('Play')
            self.play_pause_item.set_image(play_img)
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PLAY)
        else:
            self.play_pause_item.set_label('Pause')
            pause_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE,
                                                 Gtk.IconSize.BUTTON)
            self.play_pause_item.set_image(pause_img)
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PAUSE)
        self.log_debug('/.on_state_change')

    def on_button_press(self, icon, event, **kwargs):
        self.log_info(".on_button_press: %s, %s", icon, event)
        if event.button == 1:
            self.menu.popup(None, None, None, None, event.button, event.time)

    def init_menu_next(self):
        next_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_NEXT,
                                            Gtk.IconSize.BUTTON)
        next_item = Gtk.ImageMenuItem("Next")
        next_item.set_image(next_img)
        next_item.connect("activate", self.on_menuitem_clicked)
        next_item.show()
        self.menu.append(next_item)

    def init_menu_play(self, state):
        self.play_pause_item = Gtk.ImageMenuItem("Pause")
        if state == 'PLAYING':
            img = self.pause_img
        else:
            img = self.play_img
        self.play_pause_item.set_image(img)
        self.play_pause_item.connect("activate", self.on_menuitem_clicked)
        self.play_pause_item.show()
        self.menu.append(self.play_pause_item)

    def init_menu_prev(self):
        prev_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PREVIOUS,
                                            Gtk.IconSize.BUTTON)
        prev_item = Gtk.ImageMenuItem("Prev")
        prev_item.set_image(prev_img)
        prev_item.connect("activate", self.on_menuitem_clicked)
        prev_item.show()
        self.menu.append(prev_item)

    def init_menu_quit(self):
        quit_item = Gtk.ImageMenuItem("Quit")
        quit_item.connect("activate", self.on_menuitem_clicked)
        img = Gtk.Image.new_from_stock(Gtk.STOCK_QUIT,
                                       Gtk.IconSize.BUTTON)
        quit_item.set_image(img)
        quit_item.show()
        self.menu.append(quit_item)

    def init_menu(self, state):
        self.menu = Gtk.Menu()
        self.init_menu_play(state)
        self.init_menu_next()
        self.init_menu_prev()
        self.init_menu_quit()

    def on_menuitem_clicked(self, item):
        label = item.get_label()
        if label == 'Pause':
            self.player.pause()
        elif label == 'Play':
            self.player.pause()
        elif label == 'Next':
            self.playlist.next()
        elif label == 'Prev':
            self.playlist.prev()
        elif label == 'Quit':
            self.player.quit()
        print "CLICKED:%s " % (item.get_label())

reported_ext = []

def get_files_in_dir(folder):
    result = []
    for root, dirs, files in os.walk(folder):
        for name in files:
            base, ext = os.path.splitext(name)
            ext = ext.lower()
            if ext not in SUPPORTED_EXTENSIONS:
                if ext not in reported_ext:
                    print "SKIP ext:", ext
                    print "root:", root
                    print "base:", base
                    reported_ext.append(ext)
                continue
            result.append(os.path.realpath(os.path.join(root, name)))
    return result

audio_ext = ['.mp3','.wav','.ogg','.wma','.flac', '.m4a']
audio_with_tags = ['.mp3','.ogg','.wma','.flac', '.m4a']
video_ext = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv',
             '.mp4', '.mov', '.m4v']

def is_video(ext=None):
    return ext.lower() in video_ext


def is_audio(ext=None):
    return ext.lower() in audio_ext


def has_tags(ext=None):
    return ext.lower() in audio_with_tags


class MediaTags(object):
    def __init__(self, filename=None):
        self.filename = filename
        self.direction = os.path.dirname(filename)
        self.basename = os.path.basename(filename)
        self.tags_easy = None
        self.tags_hard = None
        self.base, self.ext = os.path.splitext(self.basename)
        self.has_tags = has_tags(self.ext)
        self.is_audio = is_audio(self.ext)
        self.is_video = is_video(self.ext)
        self.tags_combined = {}
        self.exists = os.path.exists(self.filename)
        self.get_tags()

    def get_easy_tags(self):
        if not self.exists or not self.has_tags or self.tags_easy is not None:
            return
        try:
            self.tags_easy = mutagen.File(self.filename, easy=True)
            print "GET_TAGS EASY"
            if self.tags_easy:
                self.combine_tags(self.tags_easy)

        except mutagen.mp3.HeaderNotFoundError, e:
            print "mutagen.mp3.HeaderNotFoundError:",e
            self.tags_easy = None
        except KeyError, e:
            print "KeyError:", e
            # if self.tags_easy:
            # self.tags_easy = None

    def combine_tags(self, tags):
        artist_keys = ('artist', 'author', 'wm/albumartist', 'albumartist',
                       'tpe1', 'tpe2', 'tpe3')
        title_keys = ('title', 'tit2')
        album_keys = ('album', 'wm/albumtitle', 'albumtitle', 'talb')
        year_keys = ('year', 'wm/year', 'date', 'tdrc', 'tdat', 'tory', 'tdor',
                     'tyer')
        genre_keys = ('genre', 'wm/genre', 'wm/providerstyle', 'providerstyle',
                      'tcon')
        track_keys = ('wm/tracknumber', 'track', 'trck')
        image_keys = ('apic:', 'apic')
        for k in tags:
            print "k:",k
            # print "k:",k,":",tags[k]
            self.add_to_combined(k, tags[k])
            k_lower = k.lower()
            if k_lower in artist_keys:
                self.add_to_combined('artist', tags[k])
            if k_lower in title_keys:
                self.add_to_combined('title', tags[k])
            if k_lower in album_keys:
                self.add_to_combined('album', tags[k])
            if k_lower in year_keys:
                self.add_to_combined('year', tags[k])
            if k_lower in genre_keys:
                self.add_to_combined('genre', tags[k])
            if k_lower in track_keys:
                self.add_to_combined('track', tags[k])
            if k_lower in image_keys:
                print "FOUND IMAGE"
                self.add_to_combined('image', tags[k], convert_to_string=False)
            if k_lower.startswith('apic:'):
                self.add_to_combined('image', tags[k], convert_to_string=False)

    def add_to_combined(self, tag, value, convert_to_string=True):
        if tag not in self.tags_combined:
            self.tags_combined[tag] = []
        if value not in self.tags_combined[tag]:
            if isinstance(value, list):
                for v in value:
                    if isinstance(v, list):
                        for _v in value:
                            if _v not in self.tags_combined[tag]:
                                print "_v:", _v
                                if convert_to_string:
                                    vs = "%s" % _v
                                    vs = vs.replace("\x00", "")
                                else:
                                    vs = _v
                                self.tags_combined[tag].append(vs)
                    elif v not in self.tags_combined[tag]:
                        try:
                            if convert_to_string:
                                vs = "%s" % v
                                vs = vs.replace("\x00", "")
                            else:
                                vs = v
                            self.tags_combined[tag].append(vs)
                        except TypeError:
                            continue
                return
            if convert_to_string:
                self.tags_combined[tag].append("%s" % value)
            else:
                self.tags_combined[tag].append(value)

    def get_hard_tags(self):
        if not self.exists or not self.has_tags or self.tags_hard is not None:
            return
        try:
            self.tags_hard = mutagen.File(self.filename)
            print "GET_TAGS HARD"
            if self.tags_hard:
                self.combine_tags(self.tags_hard)
        except mutagen.mp3.HeaderNotFoundError, e:
            print "mutagen.mp3.HeaderNotFoundError:",e
            self.tags_hard = None

    def get_tags(self, easy=True, hard=True):
        if easy:
            self.get_easy_tags()
        if hard:
            self.get_hard_tags()

if __name__ == "__main__":
    files = []
    shuffle_args = ["--shuffle", "--random", "-s", "-r"]
    no_shuffle_args = ["--no-shuffle", "--no-random"]
    commands = shuffle_args + no_shuffle_args
    shuffle_files = True
    for arg in sys.argv[1:]:
        if arg in shuffle_args:
            shuffle_files = True
            continue

        if arg in no_shuffle_args:
            shuffle_files = False
            continue

        if arg in commands:
            continue

        if os.path.exists(arg):
            arg = os.path.realpath(arg)
            if os.path.isfile(arg):
                files.append(arg)
            if os.path.isdir(arg):
                print "scanning:", arg
                files += get_files_in_dir(arg)
        else:
            files.append(arg)

    if shuffle_files:
        shuffle(files)

    playlist = Playlist(files=files)
    tray_icon = TrayIcon(playlist=playlist)
    Gtk.main()

