#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# fmp-pg.py -- main file.
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

import threading
from player1 import *
from fobjs.misc import *
from picker import picker
picker.wait = wait

from pprint import pprint
from time import sleep
from config import cfg
from copy import deepcopy
import cherry_py_server.server as server
import sys
server.wait = wait

import fobjs
refresh_and_download_all_netcasts = fobjs.netcast_episode_class.refresh_and_download_all_netcasts
refresh_and_download_expired_netcasts = fobjs.netcast_episode_class.refresh_and_download_expired_netcasts

def quit():
    server.cherrypy_thread.stop()
    Gtk.main_quit()

from log_class import Log, logging
logger = logging.getLogger(__name__)

class FmpPlaylist(Playlist):
    __name__ = 'FmpPlaylist'
    logger = logger
    def set_player_uri(self):
        try:
            print "self.index:",self.index
            print "self.files[self.index]", self.files[self.index]
        except IndexError as e:
            self.player.push_status("IndexError:%s" % e)
            return
        if self.files[self.index] is None:
            print "INDEX IS NONE"
            pprint(self.files)
            Gtk.main_quit()
            sys.exit()
            return
        else:
            filename = self.files[self.index].filename
        print "filename:", filename
        self.player.uri = self.files[self.index].filename

    def init_connections(self):
        self.player.connect('time-status', self.mark_as_played)
        self.player.connect('state-changed', self.save_config)
        self.player.connect('time-status', self.broadcast_time)

    def save_config(self, player, state):
        state = player.state_to_string(state)
        cfg.set('player_state', 'state', state , str)
        server.broadcast({"state-changed": state})

    def mark_as_played(self, player, time_status):
        try:
            self.files[self.index].mark_as_played(**time_status)
        except AttributeError:
            sys.exit()
        
        
    def broadcast_time(self, player, time_status):
        if not hasattr(self, 'last_time_status'):
            self.last_time_status = {}
        if time_status == self.last_time_status:
            return
        self.last_time_status = deepcopy(time_status)
        time_status['now'] = "%s" % time_status['now']
        server.broadcast({"time-status": time_status})

    def next(self, *args, **kwargs):
        self.files[self.index].deinc_score()
        super(FmpPlaylist, self).next(*args, **kwargs)

    def inc_index(self, *args, **kwargs):
        last_index = len(self.files) - 1
        if self.index == last_index:
            print "LAST INDEX"
            if time_to_cue_netcast():
                fobj = get_unlistend_episode()
                if fobj:
                    self.files.append(fobj)
                else:
                    print "NO UNLISTENED EPISODES"

            fobjs = picker.get_files_from_preload()
            for fobj in fobjs:
                if not fobj:
                    continue
                print "APPEND:",fobj.filename
                self.files.append(fobj)
            for f in self.files:
                print "F:", f,
                if f and f.filename:
                    print f.filename
                else:
                    print "<--------- WTF MAN?"
        super(FmpPlaylist, self).inc_index(*args, **kwargs)

    def on_eos(self, bus, msg):
        self.player.push_status("End of stream")
        print "FmpPlaylist.on_eos"
        # Trigger mark_as_played
        time_status = self.player.get_time_status()
        time_status['percent_played'] = 100
        time_status['decimal_played'] = 1
        self.files[self.index].inc_score()
        try:
            self.files[self.index].mark_as_played(**time_status)
        except AttributeError:
            sys.exit()
        self.inc_index()


picker.initial_picker()
GObject.timeout_add(60000, picker.populate_preload)
GObject.timeout_add(60000, refresh_and_download_expired_netcasts)

recently_played = get_recently_played(convert_to_fobj=True)

recently_played.reverse()
for r in recently_played:
    print "R:",r.filename, 'percent_played', r.percent_played
index = len(recently_played) - 1
state = cfg.get('player_state', 'state', 'PLAYING', str)
playlist = FmpPlaylist(files=recently_played, index=index)
server.playlist = playlist
server.wait = wait
fobjs.netcast_episode_class.wait = wait

tray_icon = TrayIcon(playlist=playlist, state=state)
percent = "%s%%" % recently_played[index].percent_played
print "PERCENT:", percent
playlist.player.position = percent
playlist.player.state = state

cherry_py_thread = threading.Thread(target=server.cherry_py_worker)
cherry_py_thread.start()

Gtk.main()
