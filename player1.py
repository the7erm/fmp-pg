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
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango
GObject.threads_init()
Gst.init(None)
import sys
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
import os
import urllib
import math
from random import shuffle
from pprint import pprint
from datetime import datetime

PLAYING = Gst.State.PLAYING
PAUSED = Gst.State.PAUSED
STOPPED = Gst.State.NULL
READY = Gst.State.READY

time_format = Gst.Format(Gst.Format.TIME)

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
    '.vorb'
    '.vorbis',
    '.wav',
    '.wma',
    '.wmv',
)

class PlayerError(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Player(GObject.GObject):
    __gsignals__ = {
        'state-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                          (object,)),
        'uri-changed': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                        (object,)),
        'time-status': (GObject.SIGNAL_RUN_LAST, GObject.TYPE_NONE, 
                        (object,)),
    }
    def __init__(self, uri=None, resume_percent=0):
        GObject.GObject.__init__(self)
        self.uri_path = ""
        self.pipeline = None
        self.filename = ""
        self.last_good_position = 0
        self.last_good_duration = 0
        self.last_state = None
        self.seek_lock = False
        self.init_window()
        self.init_player(uri=uri)
        self.last_time_status = {}
        self.connect("state-changed", self.on_state_change)
        # uri has to be set after the player is initialized.
        self.uri = uri
        GObject.timeout_add(1000, self.time_status)

    def on_state_change(self, player, state):
        self.show_video_window()

    def show_video_window(self):
        if self.playbin.get_property('n-video'):
            self.drawingarea.show()
            self.alt_drawingarea_vbox.hide()
        else:
            self.drawingarea.hide()
            self.alt_drawingarea_vbox.show()
        # self.window.show_all()
        # self.top_hbox.hide()

    def time_status(self):
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
            'remaining_str': "-"+self.format_ns(remaining),
            'state': self.state_string
        }

        if obj['state'] != self.last_state:
            self.last_state = self.state_string
            # self.file_label.set_text(self.filename)
            self.emit('state-changed', self.state)
        
        if obj != self.last_time_status:
            self.time_label.set_text("%s %s/%s" % (
                obj['remaining_str'], 
                obj['position_str'], 
                obj['duration_str']))
            
            self.emit('time-status', obj)
            # self.show_video_window()
        self.last_time_status = obj
        return True

    def format_ns(self, ns):
        if not ns:
            return "0:00"
        seconds = int(math.floor(ns / 1000000000))
        if not seconds:
            return "0:00"
        minutes = math.floor(seconds / 60)
        seconds = seconds - (minutes * 60)
        return "%d:%02d" % (minutes, seconds)

    def init_window(self):
        self.debug_messages = []
        self.window = Gtk.Window()
        self.window.set_default_size(400, 300)
        self.window.set_resizable(True)
        self.window.set_title("Video-Player")
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(
            Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack_switcher = Gtk.StackSwitcher()
        self.stack_switcher.set_stack(self.stack)
        
        self.window.add_events(Gdk.EventMask.KEY_PRESS_MASK |
                               Gdk.EventMask.POINTER_MOTION_MASK |
                               Gdk.EventMask.BUTTON_PRESS_MASK |
                               Gdk.EventMask.SCROLL_MASK |
                               Gdk.EventMask.SMOOTH_SCROLL_MASK )

        self.window.connect('key-press-event', self.on_key_press)
        self.window.connect('motion-notify-event', self.show_controls)
        self.window.connect('button-press-event', self.pause)
        self.window.connect("scroll-event", self.on_scroll)


        
        self.window.connect('destroy', self.quit)
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

        self.window.set_icon_from_file(os.path.join(img_path, "tv.png"))
        self.main_vbox = Gtk.VBox()
        
        self.init_top_hbox()

        self.drawingarea = Gtk.DrawingArea()
        self.alt_drawingarea_vbox = Gtk.VBox()
        self.alt_drawingarea_vbox_label = Gtk.Label()
        self.alt_drawingarea_vbox_label.set_line_wrap_mode(
            Pango.WrapMode.WORD_CHAR)
        self.alt_drawingarea_vbox_label.set_ellipsize(
            Pango.EllipsizeMode.MIDDLE)
        
        self.window.add(self.main_vbox)
        
        self.main_vbox.pack_start(self.top_hbox, False, True, 0)
        self.main_vbox.pack_start(self.stack_switcher, False, True, 0)
        self.main_vbox.pack_start(self.stack, True, True, 1)
        

        self.alt_drawingarea_vbox.pack_start(
            self.alt_drawingarea_vbox_label, False, True, 0)

        self.debug_text_view = Gtk.TextView()
        self.debug_text_buffer = Gtk.TextBuffer()
        self.debug_scrolled_window = Gtk.ScrolledWindow()
        self.debug_scrolled_window.add(self.debug_text_view)
        self.debug_text_view.set_editable(False)
        self.debug_text_view.set_buffer(self.debug_text_buffer)
        self.debug_text_view.set_wrap_mode(Gtk.WrapMode.WORD)
        vbox = Gtk.VBox()
        vbox.pack_start(self.alt_drawingarea_vbox, True, True, 0)
        vbox.pack_start(self.drawingarea, True, True, 0)
        vbox.show_all()
        self.stack.add_titled(vbox, "Video", "Video")
        self.stack.add_titled(self.debug_scrolled_window, "Debug", "Debug")

        self.bottom_hbox = Gtk.HBox()
        self.status_bar = Gtk.Statusbar()
        
        # Controls
        self.init_controls()

        self.bottom_hbox.pack_start(self.prev_btn, False, True, 0)
        self.bottom_hbox.pack_start(self.pause_btn, False, True, 0)
        self.bottom_hbox.pack_start(self.next_btn, False, True, 0)

        self.bottom_hbox.pack_start(self.status_bar, False, True, 0)
        self.main_vbox.pack_start(self.bottom_hbox, False, True, 0)
        self.push_status("Started")
        self.window.show_all()
        self.stack.show_all()
        self.alt_drawingarea_vbox.hide()
        try:
            self.xid = self.drawingarea.get_property('window').get_xid()
        except AttributeError, e:
            print "AttributeError:", e

    def init_top_hbox(self):
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
        self.top_hbox.pack_start(self.file_label, True, True, 0)
        self.top_hbox.pack_start(self.time_label, True, True, 0)


    def init_controls(self):
        self.prev_btn = Gtk.Button()
        prev_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PREVIOUS, Gtk.IconSize.BUTTON)
        self.prev_btn.set_image(prev_img)

        self.pause_btn = Gtk.Button()
        self.pause_image = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON)
        self.pause_btn.set_image(self.pause_image)

        self.next_btn = Gtk.Button()
        next_img = Gtk.Image.new_from_stock(
            Gtk.STOCK_MEDIA_NEXT, Gtk.IconSize.BUTTON)
        self.next_btn.set_image(next_img)

        self.pause_btn.connect("clicked", self.pause)

    def push_status(self, msg):
        print "PUSH:", msg
        self.alt_drawingarea_vbox_label.set_text(msg)
        context_id = self.status_bar.get_context_id(msg)
        self.status_bar.push(context_id, msg)
        msg = "%s %s " % (datetime.now(), msg)
        self.debug_messages.insert(0, msg)
        if len(self.debug_messages) > 35:
            self.debug_messages = self.debug_messages[0:35]
        self.debug_text_buffer.set_text("\n".join(self.debug_messages))

    def on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        print "keyname:", keyname
        self.push_status("Player.on_key_press:"+keyname)
        if keyname in ('space', 'Return'):
            self.pause()
            return True

        if keyname in ('Up', 'KP_Up'):
            self.position = "+5"
            return True

        if keyname in ('Down', 'KP_Down'):
            self.position = "-5"
            return True

        if keyname in ('Page_Up','KP_Page_Up'):
            self.position = "+30"
            return True

        if keyname in ('Page_Down','KP_Page_Down', 'KP_Next'):
            self.position = "-15"
            return True

        if keyname in ("1", "2", "3", "4", "5", "6", "7", "8", "9", "0"):
            self.position = keyname+":00"
            return True

        if keyname in ("q", "Escape"):
            self.quit()
            return True

        return False

    def show_controls(self, *args, **kwargs):
        return

    def pause(self, *args, **kwargs):
        self.state = 'TOGGLE'

    def on_scroll(self, widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.position = "+5"
        if event.direction == Gdk.ScrollDirection.DOWN:
            self.position = "-5"

    @property
    def position(self):
        try:
            res, position = self.pipeline.query_position(time_format)
        except:
            print "ERROR GETTING POSITION"
            return self.last_good_position

        if res and position:
            self.last_good_position = position
        else:
            print "FAIL GETTING RES", res, position
        return self.last_good_position

    def parseInt(self, string):
        value = 0
        try:
            value = int(string)
        except:
            pass
        return value

    def parse_minutes_seconds(self, position):
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
        percent = float(position[:-1]) * 0.01
        if not percent < 0 or percent > 1:
            self.seek_lock = False
            raise PlayerError('invalid percent %r' % position)
        return self.duration * percent

    def parse_pos_negative_position(self, position):
        seconds = int(position[1:])
        if position.startswith("-"):
            seconds = -seconds
        if seconds:
            seek_to = self.position + (seconds * Gst.SECOND)
            self.seek_lock = False
            return seek_to

        return int(position)

    def parse_position_string(self, position):
        if ':' in position:
            position = self.parse_minutes_seconds(position)
        elif position.startswith("+") or position.startswith("-"):
            position = self.parse_pos_negative_position(position)
        elif position.endswith("%"):
            position = self.parse_percent(position)
        else:
            position = int(position)
        return position

    @position.setter
    def position(self, position):
        if self.seek_lock:
            return
        self.seek_lock = False
        if isinstance(position, (str, unicode)):
            position = self.parse_position_string(position)

        if position < 0:
            position = 0

        self_duration = self.duration
        if position > self_duration:
            position = self_duration

        self.playbin.seek_simple(
            Gst.Format.TIME,
            Gst.SeekFlags.FLUSH,
            position
        )
        self.push_status("SEEK:%s" % (self.format_ns(position)))
        self.last_good_position = position
        self.seek_lock = False

    @property
    def duration(self):
        try:
            res, duration = self.pipeline.query_duration(time_format)
        except:
            return self.last_good_duration

        if res and duration:
            self.last_good_duration = duration

        return self.last_good_duration

    def init_player(self, uri=None):

        # Create GStreamer pipeline
        self.pipeline = Gst.Pipeline()

        # Create bus to get events from GStreamer pipeline
        self.bus = self.pipeline.get_bus()
        self.bus.add_signal_watch()
        self.bus.connect('message::eos', self.on_eos)
        self.bus.connect('message::error', self.on_error)

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

    def quit(self, *args, **kwargs):
        self.pipeline.set_state(STOPPED)
        Gtk.main_quit()

    @property
    def state(self):
        self.pipeline_ready()
        states = self.playbin.get_state(0)
        return states[1]

    @property
    def uri(self):
        return self.uri_path

    @uri.setter
    def uri(self, value):
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
            self.playbin.set_property('uri', self.uri)
            self.push_status("uri:%s" % urllib.unquote(self.uri))
            self.emit('uri-changed', self.uri)


    @state.setter
    def state(self, value=None):
        self.pipeline_ready()
        if value not in (PLAYING, PAUSED, STOPPED):
            self.state_string = value
            return

        old_state = self.state
        self.pipeline.set_state(value)
        self_state = self.state
        if old_state != self_state or value != self_state:
            self.last_state = value
            if value in(PAUSED, STOPPED, READY):
                self.pause_btn.get_image().set_from_stock(
                    Gtk.STOCK_MEDIA_PLAY, Gtk.IconSize.BUTTON)
            if value == PLAYING:
                self.pause_btn.get_image().set_from_stock(
                    Gtk.STOCK_MEDIA_PAUSE, Gtk.IconSize.BUTTON)
            self.push_status("state-changed:%s" % self.state_to_string(value))
            self.file_label.set_text(os.path.basename(self.filename))
            self.emit('state-changed', value)

    def pipeline_ready(self):
        if not self.pipeline:
            raise PlayerError('Player.player is %r\nInfo:%s' % (
                self.pipeline, sys.exc_info()[0]))

    @property
    def state_string(self):
        return self.state_to_string(self.state)

    def state_to_string(self, state):
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
        if not value:
            raise ValueError('Invalid state_string %r' % value)

        value_upper = str(value).upper()
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
        if msg.get_structure().get_name() == 'prepare-window-handle':
            print "-"*100
            print('prepare-window-handle')
            msg.src.set_window_handle(self.xid)

    def on_eos(self, bus, msg):
        print('Player.on_eos(): seeking to start of video')

    def on_error(self, bus, msg):
        error = msg.parse_error()
        print 'Player.on_error():', error[0]
        

class Playlist:
    def __init__(self, files=[], player=None, index=0):
        self.index = index
        self.files = files
        if player is None:
            self.player = Player()
        else:
            self.player = player

        try:
            self.player.uri = self.files[self.index]
        except IndexError:
            pass
        self.player.state = 'PLAYING'
        self.player.bus.connect('message::eos', self.on_eos)
        self.player.bus.connect('message::error', self.on_error)
        self.player.window.connect("key-press-event", self.on_key_press)
        self.player.prev_btn.connect("clicked", self.prev)
        self.player.next_btn.connect("clicked", self.next)

    def on_key_press(self, widget, event):
        keyname = Gdk.keyval_name(event.keyval)
        print "Playlist.on_key_press keyname:", keyname
        
        if keyname in ('Right', 'KP_Right'):
            self.next()
            return True

        if keyname in ('Left', 'KP_Left'):
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
        print "Playlist.on_eos"
        self.inc_index()
        self.player.push_status("End of stream")

    def on_error(self, bus, msg):
        print "*"*100
        print "Playlist.on_error"
        error = msg.parse_error()[0]
        print "ERROR:", error.message
        print "CODE:", error.code
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
                print "CODE:", error.code, '=', code

        print self.player.filename
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

        import pdb; pdb.set_trace()
        if 'Could not determine type of stream.' in msg.parse_error():
            inc_index();

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
        self.player.uri = self.files[self.index]
        print "SANITY CHECK", self.player.uri
        self.player.state = PLAYING

class TrayIcon():
    def __init__(self, player=None, playlist=None):
        self.player = player
        self.playlist = playlist
        if player is None:
            self.player = self.playlist.player
        self.init_icon()
        self.init_menu()
        self.on_state_change(self.player, self.player.state)

    def init_icon(self):
        self.ind = Gtk.StatusIcon()
        self.ind.set_from_stock(Gtk.STOCK_MEDIA_PLAY)
        self.ind.set_name("player.py")
        self.ind.set_title("player.py")
        self.ind.connect("button-press-event", self.on_button_press)
        self.player.connect("state-changed", self.on_state_change)
        

    @property
    def pause_img(self):
        return Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PAUSE, 
                                        Gtk.IconSize.BUTTON)

    @property
    def play_img(self):
        return Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PLAY, 
                                        Gtk.IconSize.BUTTON)

    def on_state_change(self, player, state):
        print "on_state_change:", player, state
        if state != PLAYING or state in (READY,):
            self.play_pause_item.set_label('Play')
            self.play_pause_item.set_image(self.play_img)
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PLAY)
        else:
            self.play_pause_item.set_label('Pause')
            self.play_pause_item.set_image(self.pause_img)
            self.ind.set_from_stock(Gtk.STOCK_MEDIA_PAUSE)

    def on_button_press(self, icon, event, **kwargs):
        print "on_button_press:", icon, event
        if event.button == 1:
            self.menu.popup(None, None, None, None, event.button, event.time)

    def init_menu(self):
        self.menu = Gtk.Menu()
        self.play_pause_item = Gtk.ImageMenuItem("Pause")
        self.play_pause_item.set_image(self.pause_img)
        self.play_pause_item.connect("activate", self.on_menuitem_clicked)
        self.play_pause_item.show()
        self.menu.append(self.play_pause_item)
        next_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_NEXT, 
                                            Gtk.IconSize.BUTTON)
        next_item = Gtk.ImageMenuItem("Next")
        next_item.set_image(next_img)
        next_item.connect("activate", self.on_menuitem_clicked)
        next_item.show()
        self.menu.append(next_item)

        prev_img = Gtk.Image.new_from_stock(Gtk.STOCK_MEDIA_PREVIOUS, 
                                            Gtk.IconSize.BUTTON)
        prev_item = Gtk.ImageMenuItem("Prev")
        prev_item.set_image(prev_img)
        prev_item.connect("activate", self.on_menuitem_clicked)
        prev_item.show()
        self.menu.append(prev_item)

        quit_item = Gtk.ImageMenuItem("Quit")
        quit_item.connect("activate", self.on_menuitem_clicked)
        img = Gtk.Image.new_from_stock(Gtk.STOCK_QUIT, 
                                       Gtk.IconSize.BUTTON)
        quit_item.set_image(img)
        quit_item.show()
        self.menu.append(quit_item)

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

