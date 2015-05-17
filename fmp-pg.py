#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# fmp-pg.py -- main file.
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


import gobject, gtk, gc
import glib 
# gobject.threads_init()

from lib.__init__ import *
from lib.listeners import listeners
from lib.fmp_plugin import FmpPluginWrapper
import os
import sys
import re
import satellite_player as player
from satellite_player import STOPPED, PAUSED, PLAYING
import lib.notify as notify
import lib.tray as tray
import math
import dbus
import dbus.service
# import alsaaudio
import datetime
import time
# import setproctitle

import urllib
import lib.fobj as fobj
import lib.picker as picker
import lib.local_file_fobj as local_file_fobj
from lib.netcast_fobj import is_netcast

from dbus.mainloop.glib import DBusGMainLoop
from subprocess import Popen, PIPE

from ConfigParser import NoSectionError
from lib.excemptions import CreationFailed, NotImpimented
from pprint import pformat, pprint

from interaction_tracker import InteractionTracker

# setproctitle.setproctitle(os.path.basename(sys.argv[0])+" ".join(sys.argv[1:]))

MIN_PRELOAD_SIZE_PER_USER = 15
MIN_PRELOAD_SIZE = 40

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

    @dbus.service.method('org.mpris.MediaPlayer2', in_signature = 's', 
                         out_signature = 's')
    def cue(self, filename):
        print "CUE:",filename
        # plr.seek(value)
        f = fobj.get_fobj(filename=filename)
        if f.is_audio or f.is_video or f.exists or f.is_stream:
            print "CUEING:",f.filename
            history.append({"filename":f.filename, 
                            "reason": "Cued from command line"})
            pp.pprint(history)
            return "CUED:%s" % filename
        return "FAILED TO CUE:%s" % filename

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
print os.environ

try:
    bus = dbus.SessionBus()
    server = bus.get_object('org.mpris.MediaPlayer2', '/fmp')
    exit = True
    args = sys.argv[1:]
    for i, arg in enumerate(args):
        print "ARG:",arg
        if arg in ('-h','-help','--help'):
            print usage
            sys.exit()

        if arg in ("--rate","-r","-rate"):
            rating = args[i+1]
            uid = "0"
            for i2, arg2 in enumerate(args):
                if arg2 in ('-u','--uid'):
                    uid = args[i2+1]
                    break
            urllib.urlopen("http://localhost:5050/?cmd=rate&uid=%s&value=%s" % (uid, rating), proxies={})
            continue

        if arg in ("-n","--next","-next"):
            # print server.next("", dbus_interface = 'org.mpris.MediaPlayer2')
            print "NEXT"
            urllib.urlopen("http://localhost:5050/player/next", proxies={})
            time.sleep(1)
            continue

        if arg in ("-b","--prev","-prev", "--back","-back"):
            # print server.prev("", dbus_interface = 'org.mpris.MediaPlayer2')
            urllib.urlopen("http://localhost:5050/player/prev", proxies={})
            continue

        if arg in ("-p","--pause","-pause", "--play","-play"):
            print "PAUSE"
            # print server.pause("", dbus_interface = 'org.mpris.MediaPlayer2')
            urllib.urlopen("http://localhost:5050/player/pause", proxies={})
            continue

        if arg in ("-k","--kill","-kill"):
            print server.kill("", dbus_interface = 'org.mpris.MediaPlayer2')
            exit=False
            continue

        if arg in ("-e","--exit","-exit"):
            print server.quit("", dbus_interface = 'org.mpris.MediaPlayer2')
            continue

        if arg in ("-s","--seek","-seek"):
            print server.seek(args[i+1], 
                              dbus_interface = 'org.mpris.MediaPlayer2')
            continue

        if os.path.exists(arg):
            f = fobj.get_fobj(filename=arg)
            if f.is_audio or f.is_video or f.exists or f.is_stream:
                print "CUE:",f.filename
                server.cue(f.filename)

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
    updated = playing.mark_as_played(percent_played)
    res = []
    if updated:
        for r in updated:
            res.append(dict(r))

    update_data = {
        "mark-as-played": percent_played,
        "res": res
    }

    plugins.write(update_data)

    flask_server.server.emit_mark_as_played(update_data)


def on_time_status(player, pos_int, dur_int, left_int, decimal, pos_str, 
                   dur_str, left_str, percent):
    gtk.gdk.threads_leave()
    global last_percent_played_decimal
    percent_played  = decimal * 100

    if percent_played == last_percent_played_decimal:
        # It's paused no need to update the database
        return

    if plr.playingState != PLAYING:
        print "on_time_status: not playing"
        sys.stdout.flush()
        return

    print "on_time_status: playing"
    sys.stdout.flush()

    last_percent_played_decimal = percent_played
    plugins.write({
        'time-status': {
            'pos_int': pos_int,
            'dur_int': dur_int,
            'left_int': left_int,
            'decimal': decimal,
            'pos_str': pos_str,
            'dur_str': dur_str,
            'left_str': left_str,
            'percent': percent
        }
    })
    mark_as_played(percent_played)


def create_dont_pick():
    populate_preload()


def populate_preload(min_amount=0):
    gtk.gdk.threads_leave()
    print "gc:",gc.collect()
    # picker.create_preload()
    picker.create_dont_pick()
    # picker.populate_dont_pick()
    picker.populate_preload(min_amount=min_amount, 
                            min_preload_size=MIN_PRELOAD_SIZE)
    return True


def on_toggle_playing(item):
    gtk.gdk.threads_leave()
    plr.pause()
    tray.set_play_pause_item(plr.playingState)

def on_next_clicked(*args, **kwargs):
    gtk.gdk.threads_leave()
    global playing, idx
    playing.deinc_score()
    start_playing("inc")
    playing.check_recently_played()
    interaction_tracker.mark_interaction()

def on_prev_clicked(item):
    gtk.gdk.threads_leave()
    start_playing("deinc")
    interaction_tracker.mark_interaction()

def get_cue_netcasts():
    cue_netcasts = cfg.get('Netcasts', 'cue', False, bool)
    print "CUE_NETCASTS:",cue_netcasts
    return cue_netcasts


def get_bedtime_mode():
    bedtime_mode = cfg.get('Misc', 'bedtime_mode', False, bool)
    print "BEDTIME_MODE:", bedtime_mode
    return bedtime_mode

def get_bible_chapters(episode_title):
    print "*"*20, "get_bible_chapters", "*"*20
    print "episode_title:", episode_title
    multiple_books = False
    books = [
        "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy",
        "Joshua", "Judges", "Ruth", "1Samuel", "2Samuel", "1Kings",
        "2Kings", "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah",
        "Esther", "Job", "Psalms", "Psalm", "Proverbs", "Ecclesiastes",
        "Song of Solomon", "Isaiah", "Jeremiah", "Lamentations", "Ezekiel",
        "Daniel", "Hosea", "Joel", "Amos", "Obadiah", "Jonah",
        "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai", "Zechariah",
        "Malachi", "Matthew", "Mark", "Luke", "John", "Acts", "Romans",
        "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
        "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
        "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
        "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude",
        "Revelation"
    ]

    episode_title = episode_title.replace("—",'-')
    book_matches = []
    files = []
    chapters = []
    for book in books:
        if episode_title.lower().startswith(book.lower()):
            if book == 'Psalm' and 'Psalms' in episode_title:
                book_matches.append('Psalms')
                continue
            book_matches.append(book)


    # 2:1-5
    re_chapter_verse_to_verse = re.compile(r"(\d+)\:(\d+)\-(\d+)")
    # 2:16—3:11
    re_chapter_verse_to_chapter_verse = re.compile(r"(\d+)\:(\d+)\-(\d+)\:(\d+)")

    # 1:1, 2
    re_chapter_verse_to_chapter_chapter = re.compile(r"(\d+)\:(\d+),(\d+)")

    # 1:2
    re_chapter_verse = re.compile(r"(\d+)\:(\d+)")

    # 1:1-3, 7:13-16
    re_chapter_verse_to_verse_comma_chapter_verse_to_verse = re.compile(
        r"(\d+)\:(\d+)\-(\d+)\,(\d+)\:(\d+)\-(\d+)")

    re_chapter_verse_to_verse_comma_chapter_verse = re.compile(
        r"(\d+)\:(\d+)\-(\d+)\,(\d+)\:(\d+)")
    
    for match in book_matches:
        # Remove the book so we just have the verses
        if match == 'Philemon':
            chapters = ['1']
        verses = episode_title.lower().replace(match.lower(), "").strip()
        verses = verses.replace(" ", "")
        verses = verses.replace("intro-", "")
        verses = verses.replace("-intro", "")
        verses = verses.replace("intro", "")
        if ':' not in verses and '-' not in verses and ',' not in verses:
            # it's just 1 chapter
            if verses != '':
                chapters.append(verses)
            continue

        if ':' not in verses:
            if '-' in verses and ',' not in verses:
                # format is <chapter>-<chapter>
                start, end = verses.split("-")
                start = int(start)
                end = int(end)
                while start <= end:
                    chapters.append(str(start))
                    start += 1
                continue

            if ',' in verses:
                # format is <chapter>,<chapter>
                _chapters = verses.split(",")
                for chapter in _chapters:
                    chapters.append(chapter)
                continue

        chapter_match = re_chapter_verse_to_verse_comma_chapter_verse_to_verse\
                        .search(verses)
        if chapter_match:
            print "re_chapter_verse_to_verse_comma_chapter_verse_to_verse.groups():", chapter_match.groups()
            chapters.append(chapter_match.group(1))
            chapters.append(chapter_match.group(4))
            continue

        chapter_match = re_chapter_verse_to_verse_comma_chapter_verse\
                        .search(verses)
        if chapter_match:
            print "re_chapter_verse_to_verse_comma_chapter_verse.groups():", chapter_match.groups()
            chapters.append(chapter_match.group(1))
            chapters.append(chapter_match.group(4))
            continue

        chapter_match = re_chapter_verse_to_chapter_verse.search(verses)
        if chapter_match:
            print "re_chapter_verse_to_chapter_verse.groups():", chapter_match.groups()
            start = int(chapter_match.group(1))
            end = int(chapter_match.group(3))
            while start <= end:
                chapters.append(str(start))
                start += 1
            continue

        chapter_match = re_chapter_verse_to_chapter_chapter.search(verses)
        if chapter_match:
            print "re_chapter_verse_to_chapter_chapter.groups():", chapter_match.groups()
            chapters.append(chapter_match.group(1))
            chapters.append(chapter_match.group(3))
            continue

        chapter_match = re_chapter_verse_to_verse.search(verses)
        if chapter_match:
            print "re_chapter_verse_to_verse.groups():", chapter_match.groups()
            chapters.append(chapter_match.group(1))
            continue

        chapter_match = re_chapter_verse.search(verses)
        if chapter_match:
            print "re_chapter_verse.groups():", chapter_match.groups()
            chapters.append(chapter_match.group(1))
            continue



    print "chapters:", chapters
    if not chapters:
        print "-="*300
        return []

    recently_played = fobj.recently_played(limit=100)
    for book in book_matches:
        # Hosea
        sql = """SELECT fid, dirname, basename 
                 FROM file_locations 
                 WHERE dirname LIKE '%%/MP3 Bible/%%' AND 
                       basename LIKE %s"""
        _book = book
        if _book == "Psalms":
            _book = "Psalm"

        if _book.startswith("1"):
            _book = "I %s" % (_book[2:])

        if _book.startswith("2"):
            _book = "II %s" % (_book[2:])

        if _book.startswith("3"):
            _book = "III %s" % (_book[2:])

        for chapter in chapters:
            picker.wait()
            # print "chapter:", chapter
            try:
                chp = int(chapter)
            except ValueError:
                continue

            for i in range(3, 0, -1):
                fmt = "%%0%sd" % i
                like = "% {book} {chapter}.mp3".format(book=_book, 
                                                    chapter=fmt % chp)
                # print pg_cur.mogrify(sql, (like, ))
                _files = get_results_assoc(sql, (like, ))
                if _files:
                    for f in _files:
                        _f = dict(f)
                        _f['reason'] = "Thru the Bible - pre-roll"
                        played = False
                        for r in recently_played:
                            # print "R:", r
                            if r['id'] == _f['fid'] and r['id_type'] == 'f':
                                played = True
                                break
                        if not played:
                            files.append(_f)
                            # print "_f:", pp.pformat(_f)
                    break

    print "FILES:", pp.pformat(files)
    return files

def append_file():
    global history
    f = None
    if get_cue_netcasts():
        # TODO: Add config option for netcast spacing.
        recent = history[-10:]
        found_netcast = False
        for r in recent:
            r = dict(r)
            # print "r:", dict(r)
            if is_netcast(r):
                found_netcast = True
                break

        if not found_netcast:
            f = fobj.netcast_fobj.get_one_unlistened_episode()
            if f and 'thru the bible' in f['netcast_name'].lower():
                files = get_bible_chapters(f['episode_title'])
                for _f in files:
                    history.append(_f)
    if not f:
        f = picker.get_song_from_preload()

    if f:
        print "APPEND:",f
        history.append(f)
        if 'fid' in f:
            delete_fid_from_preload(f['fid'])
        if 'id' in f and 'id_type' in 'f':
            delete_fid_from_preload(f['id'])
        return f
    
    print "NO FILE:"
    return None


def delete_fid_from_preload(fid):
    if not fid:
        return
    sql = """DELETE FROM preload WHERE fid = %s"""
    print pg_cur.mogrify(sql, (fid,))
    query(sql, (fid,))

def set_idx(idx, retry=2):
    global playing, history

    if idx < 0:
        idx = 0
    print "set_idx: IDX:",idx
    try:
        f = dict(history[idx])
        print "set_idx F:", idx, f
        if 'fid' in f:
            delete_fid_from_preload(f['fid'])
        tray.playing = flask_server.server.playing = playing = \
            fobj.get_fobj(**f)
        print "/set_idx F:"
        tray.set_rating()
        populate_preload()
    except IndexError:
        history_len = len(history)
        while idx > history_len - 1:
            f = append_file()
            if not f:
                break
            history_len = len(history)

        if idx == history_len - 1 and retry > 0:
            retry = 1

        if retry > 0:
            print "RETRYING:",retry
            set_idx(idx, retry-1)
            return


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
        # picker.wait()
    except:
        pass
    finally:
        gtk.gdk.threads_leave()
    return True

def on_end_of_stream(*args):
    gtk.gdk.threads_leave()
    global playing
    playing.inc_score()
    start_playing("inc")
    plugins.write(
        {'end-of-stream': True}
    )

def start_playing(direction="inc", start=True):
    global playing
    if direction == "inc":
        inc_index()
    elif direction == "deinc":
        deinc_index()
    retry_cnt = 0
    while isinstance(playing, local_file_fobj.Local_File) and not \
          playing.exists and playing.is_readable and retry_cnt < 10:
        retry_cnt += 1
        fp = open(os.path.join(config_dir,"missing.log"), "a")
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
        fp.write("[%s] MISSING:%s\n" % (now, playing.filename))
        fp.close()
        print "MISSING:", playing.filename, "%s" % retry_cnt
        if direction == "deinc":
            deinc_index()
        else:
            inc_index()

    playing.rating_callback = flask_server.server.emit_status

    plr.filename = playing.filename
    if start:
        plr.start()
    else:
        plr.prepare()
    tray.set_play_pause_item(plr.playingState)
    notify.playing(playing)
    flask_server.server.player = plr
    flask_server.server.emit_status(playing)

def on_state_change(*args, **kwargs):
    gtk.gdk.threads_leave()
    tray.set_play_pause_item(plr.playingState)
    plugins.write({'on-state-change':"%s" % plr.playingState})

def quit(*args, **kwargs):
    try:
        netcast_tray.terminate()
    except:
        pass
    plr.stop()
    gtk.threads_leave()
    gtk_main_quit()

def on_scroll(widget, event):
    plr.on_scroll(widget, event)
    # <gtk.StatusIcon object at 0x211da50 (GtkStatusIcon at 0x1ab7280)>, <gtk.gdk.Event at 0x2d2d8c8: GDK_SCROLL x=11.00, y=11.00, direction=GDK_SCROLL_UP>
    direction = ""
    if event.direction == gtk.gdk.SCROLL_UP:
        direction = "UP"
    if event.direction == gtk.gdk.SCROLL_DOWN:
        direction = "DOWN"
    if event.direction == gtk.gdk.SCROLL_LEFT:
        direction = "LEFT"
    if event.direction == gtk.gdk.SCROLL_RIGHT:
        direction = "RIGHT"
    plugins.write({'on-scroll': direction })

import flask_server
flask_server.server.threads = threads
flask_server.server.get_results_assoc = get_results_assoc
flask_server.server.get_assoc = get_assoc
flask_server.server.query = query
flask_server.server.pg_cur = pg_cur

global history, playing, idx, last_percent_played, last_percent_played_decimal

last_percent_played = 0
last_percent_played_decimal = 0

history = fobj.recently_played()

history.reverse()

if not history:
    history = []

for u in listeners.listeners:
    picker.insert_missing_songs(u['uid'])

idx = len(history) - 1
if idx < 0:
    idx = 0
try:
    item = dict(history[idx])
except IndexError:
    populate_preload()
    append_file()
    try:
        item = dict(history[idx])
    except IndexError:
        item = get_assoc("SELECT * FROM files ORDER BY random() LIMIT 1")
        history.append(dict(item))

def sync_playing(file_data):
    if not file_data or file_data == {}:
        return
    global idx, playing
    print "-="*20, "sync_playing"
    print "sync_playing:", pformat(file_data)
    history.append(dict(file_data))
    idx = len(history) - 1
    set_idx(idx)
    start_playing('stay', False)
    print "-="*20, "/sync_playing"


item_fobj = None
while item_fobj is None:
    try:
        item_fobj = fobj.get_fobj(**item)
    except CreationFailed as err:
        print "CreationFailed:", err
        item = get_assoc("SELECT * FROM files ORDER BY random() LIMIT 1")
        history.append(dict(item))
        item_fobj = None
        time.sleep(1)

tray.playing = flask_server.server.playing = playing = item_fobj

tray.set_rating()
plr = player.Player(filename=playing.filename)

start_playing("stay")
playing.check_recently_played()
notify.playing(playing)
if plr.dur_int:
    try:
        plr.seek_ns(int(plr.dur_int  * playing["percent_played"] * 0.01))
        plr.pause()
    except AttributeError:
        pass

plugins = FmpPluginWrapper()

plr.next_button.connect('clicked', on_next_clicked)
plr.prev_button.connect('clicked', on_prev_clicked)
plr.connect("time-status", on_time_status)
plr.connect("end-of-stream", on_end_of_stream)
plr.connect("state-changed", on_state_change)
tray.play_pause_item.connect("activate", on_toggle_playing)
tray.next.connect("activate", on_next_clicked)
tray.prev.connect("activate", on_prev_clicked)
tray.quit.connect("activate", quit)
tray.icon.connect('scroll-event', on_scroll)
# query("TRUNCATE preload")
gobject.idle_add(create_dont_pick)
gobject.timeout_add(15000, populate_preload, MIN_PRELOAD_SIZE_PER_USER)
gobject.timeout_add(1000, set_rating)

interaction_tracker = InteractionTracker('server', plr)
flask_server.server.interaction_tracker = interaction_tracker
flask_server.server.playing = playing
flask_server.server.player = plr
flask_server.server.tray = tray
flask_server.server.sync_playing = sync_playing
flask_server.server.start_in_thread()

picker.wait()

try:
    netcast_tray = Popen([sys.path[0]+'/netcast-tray.py'])
    """
    netcast_tray = Popen([sys.path[0]+'/netcast-tray.py'])
    tst = fobj.netcast_fobj.get_one_unlistened_episode()
    if tst:
        print "TST:",dict(tst) 
    print "is_netcast:",is_netcast(tst)
    """
    sql = """SELECT episode_title 
             FROM netcast_episodes 
             WHERE nid = 10
             ORDER BY pub_date DESC
             LIMIT 10"""
    # episodes = get_results_assoc(sql)
    #for e in episodes:
    #    print "chapters:", get_bible_chapters(e['episode_title'])
    gtk.gdk.threads_leave()
    gtk.main()
except KeyboardInterrupt:
    Popen(['pykill','netcast-tray.py', 'fmp-pg.py'])
