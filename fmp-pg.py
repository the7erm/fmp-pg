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
import os, sys, re
import player
import notify
import tray
import picker
import math
import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from subprocess import Popen, PIPE

class DbusWatcher(dbus.service.Object):
    def __init__(self):
        busName = dbus.service.BusName('org.mpris.MediaPlayer2', bus = dbus.SessionBus())
        dbus.service.Object.__init__(self, busName, '/fmp')

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def next(self):
        on_next_clicked(None)
        return "next"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def prev(self):
        on_prev_clicked(None)
        return "prev"
    
    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def pause(self):
        on_toggle_playing(None)
        return "pause"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def play(self):
        on_toggle_playing(None)
        return "play"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = 's', out_signature = 's')
    def seek(self,value):
        plr.seek(value)
        return "seek:%s" % value

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def kill(self):
        gobject.timeout_add(100, gtk.main_quit)
        return "kill"

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = '', out_signature = 's')
    def quit(self):
        gobject.timeout_add(100, gtk.main_quit)
        return "quit"
    

usage = """
Usage:
fmp.py <arguments> [file] [file] ...
For your convenience all text commands can have 2 dashes ie --next -n -next all do the same thing
-n, -next             Play next track
-b, -back, -prev      Play next track
-p, -play, -pause     Play/pause current track
-s, -seek <arg>       Seek to a specific second of current track
-k, -kill             Kill the currently running player, and replace it.
-e, -exit             Kill the currently running player, then exit.
<filename>            Append file to playlist (.pls, .m3u not currently supported)
"""

DBusGMainLoop(set_as_default = True)

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
            print server.quit(argv[i+1], dbus_interface = 'org.mpris.MediaPlayer2')
           

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

def mark_as_played(percent_played=0):
    global listeners, last_percent_played, last_percent_played_decimal

    query("UPDATE user_song_info SET ultp = NOW(), percent_played = %s WHERE fid = %s AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)",(percent_played, playing['fid'],))

    calculate_true_score()
    
    if not listeners:
        listeners = get_results_assoc("SELECT uid, uname FROM users WHERE listening = true")
    
    if listeners and last_percent_played != math.ceil(percent_played):
        updated = get_results_assoc("UPDATE user_history uh SET true_score = ufi.true_score, score = ufi.score, rating = ufi.rating, percent_played = ufi.percent_played, time_played = NOW(), date_played = current_date FROM user_song_info ufi WHERE ufi.uid IN (SELECT uid FROM users WHERE listening = true) AND uh.uid = ufi.uid AND ufi.fid = uh.id AND uh.id_type = 'f' AND uh.date_played = DATE(ufi.ultp) AND uh.id = %s RETURNING uh.*", (playing['fid'],))
        # print "UPDATED:"
        # pp.pprint(updated)
        
        for l in listeners:
            found = False
            for u in updated:
                if u['uid'] == l['uid']:
                    found = True
            if not found:
                try:
                    user_history = get_assoc("INSERT INTO user_history (uid, id, id_type, percent_played, time_played, date_played) VALUES(%s, %s, %s, %s, NOW(), current_date) RETURNING *",(l['uid'], playing['fid'], 'f', percent_played))
                    updated_user = get_assoc("UPDATE user_history uh SET true_score = ufi.true_score, score = ufi.score, rating = ufi.rating, percent_played = ufi.percent_played, time_played = NOW(), date_played = current_date FROM user_song_info ufi WHERE ufi.uid = %s AND uh.uid = ufi.uid AND ufi.fid = uh.id AND uh.id_type = 'f' AND uh.date_played = DATE(ufi.ultp) AND uh.id = %s RETURNING uh.*", (l['uid'], playing['fid']))
                    if updated_user:
                        updated.append(updated_user)

                except psycopg2.IntegrityError, err:
                    query("COMMIT;")
                    print "psycopg2.IntegrityError:",err

        artists = get_results_assoc("UPDATE artists a SET altp = NOW() FROM file_artists fa WHERE fa.aid = a.aid AND fa.fid = %s RETURNING *;",(playing['fid'],))
        # print "ARTISTS:"
        # pp.pprint(artists) 
        if artists:
            updated_artists = get_results_assoc("UPDATE user_artist_history uah SET time_played = NOW(), date_played = NOW() FROM user_song_info usi, file_artists fa WHERE usi.uid IN (SELECT uid FROM users WHERE listening = true) AND fa.fid = usi.fid AND uah.uid = usi.uid AND uah.aid = fa.aid AND usi.fid = %s AND uah.date_played = current_date RETURNING uah.*",(playing['fid'],))

            update_association = {}

            for ua in updated_artists:
                key = "%s-%s" % (ua['aid'], ua['uid'])
                update_association[key] = ua

            pp.pprint(update_association)
            for l in listeners:
                found = False 
                for a in artists:
                    key = "%s-%s" % (a['aid'], l['uid'])
                    if not update_association.has_key(key):
                        try:
                            user_artist_history = get_assoc("INSERT INTO user_artist_history (uid, aid, time_played, date_played) VALUES(%s, %s, NOW(), current_date) RETURNING *", (l['uid'], a['aid']))
                            update_association[key] = user_artist_history
                        except psycopg2.IntegrityError, err:
                            query("COMMIT;")
    
        last_percent_played = math.ceil(percent_played)


def on_time_status(player, pos_int, dur_int, left_int, decimal, pos_str, dur_str, left_str, percent):
    global listeners, last_percent_played, last_percent_played_decimal
    percent_played  = decimal * 100
    if percent_played == last_percent_played_decimal:
        # It's paused no need to update the database
        return
    last_percent_played_decimal = percent_played
    mark_as_played(percent_played)

def create_dont_pick():
    populate_preload()

def populate_preload(min_amount=0):
    global listeners
    listeners = get_results_assoc("SELECT uid, uname FROM users WHERE listening = true")
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



def on_next_clicked(item):
    query("UPDATE user_song_info SET ultp = NOW(), score = score - 1 WHERE fid = %s AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)", (playing['fid'], ))
    query("UPDATE user_song_info SET score = 1  WHERE fid = %s AND score <= 0 AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)", (playing['fid'], ))
    calculate_true_score()

    inc_index()
    plr.filename = os.path.join(playing['dir'], playing['basename'])
    plr.start()
    notify.playing(playing)

def on_prev_clicked(item):
    deinc_index()
    plr.filename = os.path.join(playing['dir'], playing['basename'])
    plr.start()
    notify.playing(playing)

def deinc_index():
    global idx, playing
    idx = idx - 1
    if idx < 0:
        idx = 0

    try:
        tray.playing = playing = history[idx]
    except IndexError:
        f = picker.get_song_from_preload()
        history.append(f)
        tray.playing = playing = history[idx]

    tray.set_rating()

def inc_index():
    global idx, playing
    idx = idx + 1
    print "IDX:",idx
    try:
        tray.playing = playing = history[idx]
    except IndexError:
        f = picker.get_song_from_preload()
        history.append(f)
        tray.playing = playing = history[idx]

    tray.set_rating()
    populate_preload()

def set_rating():
    try:
        tray.set_rating()
        picker.wait()
    except:
        pass
    return True

def calculate_true_score():
    query("UPDATE user_song_info SET true_score = (((rating * 2 * 10.0) + (score * 10) + percent_played) / 3) WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true)",(playing['fid'],))
    # print "calculate_true_score:",res

def on_end_of_stream(*args):
    global playing
    query("UPDATE user_song_info SET ultp = NOW(), score = score + 1 WHERE fid = %s AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)", (playing['fid'],))
    query("UPDATE user_song_info SET score = 10 WHERE fid = %s AND score > 10 AND uid IN (SELECT DISTINCT uid FROM users WHERE listening = true)", (playing['fid'],))
    mark_as_played(100.00)

    inc_index()
    plr.filename = os.path.join(playing['dir'], playing['basename'])
    plr.start()
    notify.playing(playing)

global history, playing, idx, listeners, last_percent_played, last_percent_played_decimal
last_percent_played = 0
last_percent_played_decimal = 0
listeners = get_results_assoc("SELECT uid FROM users WHERE listening = true")

history = get_results_assoc("SELECT DISTINCT f.fid, dir, basename, ultp, percent_played FROM files f, user_song_info u WHERE u.uid IN (SELECT uid FROM users WHERE listening = true) AND f.fid = u.fid AND ultp IS NOT NULL ORDER BY ultp DESC LIMIT 10")
history.reverse()

if not history:
    history = []


idx = len(history) - 1
tray.playing = playing = history[idx]
tray.set_rating()

plr = player.Player(filename=os.path.join(playing['dir'], playing['basename']))
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
tray.quit.connect("activate", gtk.main_quit)
tray.icon.connect('scroll-event',plr.on_scroll)
# query("TRUNCATE preload")
gobject.idle_add(create_dont_pick)
gobject.timeout_add(60000, populate_preload, 5)
gobject.timeout_add(5000, set_rating)
gtk.main()

