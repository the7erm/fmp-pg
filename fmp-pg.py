#!/usr/bin/env python
# fmp-pg.py -- main file.
#    Copyright (C) 2012 Eugene Miller <theerm@gmail.com>
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

import gobject, gtk, gc
gobject.threads_init()

from __init__ import *
import os
import sys
import re
import player
import notify
import tray
import picker
import math
import dbus
import dbus.service
import fobj
from netcast_fobj import is_netcast

from dbus.mainloop.glib import DBusGMainLoop
from subprocess import Popen, PIPE
import flask_server
from ConfigParser import NoSectionError

class DbusWatcher(dbus.service.Object):
    def __init__(self):
        busName = dbus.service.BusName('org.mpris.MediaPlayer2', 
                                       bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, busName, '/fmp')

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def next(self):
        on_next_clicked(None)
        return "next"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def prev(self):
        on_prev_clicked(None)
        return "prev"
    
    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def pause(self):
        on_toggle_playing(None)
        return "pause"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def play(self):
        on_toggle_playing(None)
        return "play"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = 's', 
                         out_signature = 's')
    def seek(self, value):
        plr.seek(value)
        return "seek:%s" % value

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def kill(self):
        gobject.timeout_add(100, quit)
        return "kill"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', 
                         out_signature = 's')
    def quit(self):
        gobject.timeout_add(100, quit)
        return "quit"
    

usage = """
Usage:
fmp.py <arguments> [file] [file] ...
For your convenience all text commands can have 2 dashes ie --next -n -next all 
do the same thing.

-n, -next             Play next track
-b, -back, -prev      Play previous track
-p, -play, -pause     Play/pause current track
-s, -seek <arg>       Seek to a specific second of current track
-k, -kill             Kill the currently running player, and replace it.
-e, -exit             Kill the currently running player, then exit.
<filename>            Append file to playlist (.pls, .m3u not currently 
                      supported)
"""

DBusGMainLoop(set_as_default=True)

try:
    bus = dbus.SessionBus()
    server = bus.get_object('org.mpris.MediaPlayer2', '/fmp')
    exit = True

    for i, arg in enumerate(sys.argv):
        print "ARG:",arg
        if arg in ('-h','-help','--help'):
            print usage
            sys.exit()

        if arg in ("-n","--next","-next"):
            print server.next("", dbus_interface = 'org.mpris.MediaPlayer2')

        if arg in ("-b","--prev","-prev", "--back","-back"):
            print server.prev("", dbus_interface = 'org.mpris.MediaPlayer2')

        if arg in ("-p","--pause","-pause", "--play","-play"):
            print server.pause("", dbus_interface = 'org.mpris.MediaPlayer2')

        if arg in ("-k","--kill","-kill"):
            print server.kill("", dbus_interface = 'org.mpris.MediaPlayer2')
            exit=False

        if arg in ("-e","--exit","-exit"):
            print server.quit("", dbus_interface = 'org.mpris.MediaPlayer2')

        if arg in ("-s","--seek","-seek"):
            print server.seek(argv[i+1], 
                              dbus_interface = 'org.mpris.MediaPlayer2')

    if exit:
        print "Dbus Instance of fmp player detected exiting..."
        sys.exit()
except dbus.exceptions.DBusException, err:
    print "dbus.exceptions.DBusException:",err
    print "Initializing player"


def is_running(pid_file, kill=False):
    """
        Check if a file is running, return True if it's running.
        if kill is set to True it will kill the process.
    """
    if not os.path.isfile(pid_file):
        return False

    fp = open(pid_file,'r')
    pid = fp.read()
    fp.close()
    proc_path = '/proc/%s/exe' % pid
    if not os.path.exists(proc_path):
        return False
    cmd_path = "/proc/%s/cmdline" % pid
    fp = open(cmd_path,'r')
    cmd_line = fp.read()
    fp.close()

    # print "cmd_line:",cmd_line
    # print "sys.argv:",sys.argv

    is_fmp = re.search("(fmp\-pg\.py)", cmd_line)
    if is_fmp:
        if '-kill' in sys.argv:
            os.system("kill %s" % pid)
            print "killing %s" % pid
            return False
        return True
    return False


def write_pid(pid_file):
    """
        Write the current pid to a file.
    """
    fp = open(pid_file,'w')
    fp.write(str(os.getpid()))
    fp.close()


pid_file = config_dir+"/running_pid"

if is_running(pid_file):
    print "already running"
    sys.exit()

write_pid(pid_file)

watcher = DbusWatcher()

def update_history(percent_played=0):
    playing.update_history(percent_played)


def mark_as_played(percent_played=0):
    playing.mark_as_played(percent_played)


def on_time_status(player, pos_int, dur_int, left_int, decimal, pos_str, 
                   dur_str, left_str, percent):

    global last_percent_played_decimal
    percent_played  = decimal * 100
    if percent_played == last_percent_played_decimal:
        # It's paused no need to update the database
        return
    last_percent_played_decimal = percent_played
    mark_as_played(percent_played)


def create_dont_pick():
    populate_preload()


def populate_preload(min_amount=0):
    print "gc:",gc.collect()
    # picker.create_preload()
    picker.create_dont_pick()
    # picker.populate_dont_pick()
    picker.populate_preload(min_amount=min_amount)

    return True


def on_toggle_playing(item):
    print "on_toggle_playing"
    plr.pause()
    tray.set_play_pause_item(plr.playingState)


def on_next_clicked(*args, **kwargs):
    playing.deinc_score()
    inc_index()
    plr.filename = playing.filename
    plr.start()
    tray.set_play_pause_item(plr.playingState)
    notify.playing(playing)


def on_prev_clicked(item):
    deinc_index()
    plr.filename = playing.filename
    plr.start()
    tray.set_play_pause_item(plr.playingState)
    notify.playing(playing)
    

def get_cue_netcasts():
    cfg = ConfigParser.ConfigParser()
    cfg.read(config_file)
    try:
        cue_netcasts = cfg.getboolean('Netcasts','cue')
        print "cue_netcasts:",cue_netcasts
    except NoSectionError:
        cfg.add_section('Netcasts')
        cue_netcasts = 0
        with open(config_file, 'wb') as configfile:
            cfg.set('Netcasts', 'cue', "false")
            cfg.write(configfile)

    return cue_netcasts


def set_idx(idx):
    global playing

    if idx < 0:
        idx = 0
    
    try:
        tray.playing = playing = fobj.get_fobj(**dict(history[idx]))
    except IndexError:
        if get_cue_netcasts():
            # TODO: Add config option for netcast spacing.
            recent = history[-10:]
            found_netcast = False
            for r in recent:
                r = dict(r)
                print "r:",dict(r)
                if is_netcast(r):
                    found_netcast = True
                    break

            if found_netcast:
                f = picker.get_song_from_preload()
            else:
                f = fobj.netcast_fobj.get_one_unlistened_episode()
                if not f:
                    f = picker.get_song_from_preload()
        else:
            recent = history[-10:]
            f = picker.get_song_from_preload()
        history.append(f)
        tray.playing = playing = fobj.get_fobj(**dict(history[idx]))

    tray.set_rating()
    populate_preload()


def inc_index():
    global idx, playing
    idx = idx + 1
    print "IDX:",idx
    set_idx(idx)


def deinc_index():
    global idx
    idx = idx - 1
    set_idx(idx)

def set_rating():
    try:
        tray.set_rating()
        picker.wait()
    except:
        pass
    return True

def on_end_of_stream(*args):
    global playing
    playing.inc_score()
    inc_index()
    plr.filename = playing.filename
    plr.start()
    tray.set_play_pause_item(plr.playingState)
    notify.playing(playing)

def quit(*args, **kwargs):
    try:
        netcast_tray.terminate()
    except:
        pass
    gtk.main_quit()

global history, playing, idx, last_percent_played, last_percent_played_decimal

last_percent_played = 0
last_percent_played_decimal = 0

history = fobj.recently_played()

history.reverse()

if not history:
    history = []

idx = len(history) - 1
item = dict(history[idx])
tray.playing = playing = fobj.get_fobj(**item)
tray.set_rating()

plr = player.Player(filename=playing.filename)
plr.start()
notify.playing(playing)
if plr.dur_int:
    plr.seek_ns(int(plr.dur_int  * playing["percent_played"] * 0.01))

plr.next_button.connect('clicked', on_next_clicked)
plr.prev_button.connect('clicked', on_prev_clicked)
plr.connect("time-status",on_time_status)
plr.connect("end-of-stream",on_end_of_stream)
tray.play_pause_item.connect("activate", on_toggle_playing)
tray.next.connect("activate", on_next_clicked)
tray.prev.connect("activate", on_prev_clicked)
tray.quit.connect("activate", quit)
tray.icon.connect('scroll-event',plr.on_scroll)
# query("TRUNCATE preload")
gobject.idle_add(create_dont_pick)
gobject.timeout_add(15000, populate_preload, 2)
gobject.timeout_add(5000, set_rating)

# flask_server.playing = playing
# flask_server.player = player
# flask_server.start_in_thread()

try:
    netcast_tray = Popen([sys.path[0]+'/netcast-tray.py'])
    tst = fobj.netcast_fobj.get_one_unlistened_episode()
    print "TST:",dict(tst) 
    print "is_netcast:",is_netcast(tst)
    gtk.main()
except KeyboardInterrupt:
    Popen(['pykill','netcast-tray.py', 'fmp-pg.py'])

