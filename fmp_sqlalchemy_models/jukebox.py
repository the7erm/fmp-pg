#!/usr/bin/env python
# fmp_sqlalchemy_models/jukebox.py -- manages player & picker
#    Copyright (C) 2013 Eugene Miller <theerm@gmail.com>
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

from picker import Picker, wait
from player_refactored import Player
from tray import ControllerIcon, RatingIcon
import gtk
import gobject
from files_model_idea import FileLocation, FileInfo, Artist, DontPick, Genre,\
                             Preload, Title, Album, User, UserHistory, \
                             UserFileInfo, session

from gst import STATE_NULL, STATE_PAUSED, STATE_PLAYING

gtk.gdk.threads_init()
NANO_SECOND = 1000000000.0
HISTORY_LENGTH = 100

class JukeBox:
    def __init__(self):
        self.percent_played = -10
        self.pos_float = -10.0
        self.controller_icon = None
        self.rating_icon = None
        self.init_history()
        self.init_picker()
        self.init_player()
        self.init_tray()

    def init_tray(self):
        self.init_rating_icon()
        self.init_controller_icon()
        self.set_tray_data()

    def init_controller_icon(self):
        self.controller_icon = ControllerIcon()
        self.controller_icon.icon.connect("scroll-event", self.on_seek_scroll)
        self.controller_icon.play_pause_item.connect("activate", self.on_play_pause)
        self.controller_icon.next.connect("activate", self.on_next)
        self.controller_icon.prev.connect("activate", self.on_prev)
        self.player.connect('state-changed', self.on_state_change)
        self.on_state_change(self.player, self.player.playingState)

    def init_rating_icon(self):
        self.rating_icon = RatingIcon(self.playing)

    def on_play_pause(self, *args, **kwargs):
        self.pause()
        wait()

    def on_next(self, *args, **kwargs):
        print "on_next"
        self.next()

    def on_prev(self, *args, **kwargs):
        self.prev()

    def on_seek_scroll(self, icon, event, *args, **kwargs):
        if event.direction == gtk.gdk.SCROLL_UP:
            self.player.seek("+5")

        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.player.seek("-5")

    def on_state_change(self, player, state):
        print "state change:", state
        self.controller_icon.set_state(state)
        self.set_tray_data()

    def set_tray_data(self):
        self.rating_icon.playing = self.playing
        self.controller_icon.set_tooltip(self.artist_title)
        self.rating_icon.set_tooltip(self.artist_title)
        self.rating_icon.set_rating(self.playing.rating)
        wait()

    def init_picker(self):
        self.picker = Picker()
        # self.picker.do()
        # self.playing = self.picker.pop()
        gobject.timeout_add(15000, self.picker.do)

    def init_player(self):
        self.player = Player()
        self.start()
        percent_played = self.playing.listeners_ratings[0].percent_played
        duration = self.player.get_duration()
        pos_ns = int(duration * (percent_played * 0.01))
        self.player.seek_ns(pos_ns)
        self.player.connect('time-status', self.on_time_status)
        self.player.connect('end-of-stream', self.on_end_of_stream)

    def init_history(self):
        self.index = 0
        self.history = []
        history = session.query(UserFileInfo)\
                         .filter(User.listening==True)\
                         .order_by(UserFileInfo.ultp.desc())\
                         .limit(HISTORY_LENGTH)

        for h1 in history:
            if h1.fid not in self.history:
                self.history.append(h1.fid)

        self.history.reverse()
        if self.history:
            self.index = len(self.history) - 1

    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, 
                       pos_str, dur_str, left_str, percent):
        percent_played = decimal * 100
        # print "on_time_status:", percent_played
        if percent_played < self.percent_played + 1 and\
           percent_played > self.percent_played - 1:
            return
        pos_float = pos_int / NANO_SECOND
        # print "pos_float:",pos_float
        if pos_float < self.pos_float + 5 and \
           pos_float > self.pos_float - 5:
            return
        self.percent_played = percent_played
        self.pos_float = pos_float
        print "mark as played:", percent_played, "***", pos_float
        self.playing.mark_as_played(percent_played=percent_played)

    def on_end_of_stream(self, *args, **kwargs):
        print "END OF STREAM"
        self.playing.inc_skip_score()
        self.percent_played = -100
        self.pos_float = -100.0
        self.index += 1
        self.start()
        
    def start(self):
        try:
            fid = self.history[self.index]
            file_info = session.query(FileInfo)\
                               .filter(FileInfo.fid == fid)\
                               .limit(1)\
                               .one()
        except IndexError:
            file_info = self.picker.pop()
            self.history.append(file_info.fid)
            self.history = self.history[-HISTORY_LENGTH:]
            self.index = len(self.history) - 1

        self.player.filename = file_info.filename
        self.player.start()
        self.playing = file_info
        if self.controller_icon is not None and self.rating_icon is not None:
            self.set_tray_data()

    def pause(self, *args, **kwargs):
        self.player.pause()

    def next(self, *args, **kwargs):
        self.playing.deinc_skip_score()
        self.player.stop()
        self.index += 1
        self.start()

    def prev(self, *args, **kwargs):
        self.index -= 1
        self.player.stop()
        self.start()

    @property
    def artist_title(self):
        return self.playing.artist_title


if __name__ == '__main__':
    jukebox = JukeBox()
    gtk.main()
