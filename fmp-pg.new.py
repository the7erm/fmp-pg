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

import os
import sys

os.chdir(sys.path[0])

from setproctitle import setproctitle
setproctitle(os.path.basename(sys.argv[0]))

import threading
Thread = threading.Thread
from player1 import *
from fobjs.misc import *
import fobjs.preload_class
Preload = fobjs.preload_class.Preload
from picker import picker
picker.wait = wait
fobjs.preload_class.wait = wait
from gui.RatingTrayIcon import RatingTrayIcon
import gui.ListenersTable as ListenersTable

from pprint import pprint
from time import sleep, time
from config import cfg
from copy import deepcopy
import cherry_py_server.server as server

server.wait = wait


import fobjs
refresh_and_download_all_netcasts = fobjs.netcast_episode_class.refresh_and_download_all_netcasts
refresh_and_download_expired_netcasts = fobjs.netcast_episode_class.refresh_and_download_expired_netcasts

fobjs.netcast_episode_class.wait = wait

def quit():
    server.cherrypy_thread.stop()
    Gtk.main_quit()

from log_class import Log, logging
logger = logging.getLogger(__name__)

class UserFileInfoTreeview():
    def __init__(self, playlist=None):
        self.fullscreen = False
        self.is_video = False
        self.playlist = playlist
        self.init_store()
        self.init_treeview()
        self.init_treeview_cols()
        self.init_cells()
        self.pack_treeview_cols()

    def on_fullscreen(self, *args, **kwargs):
        print "on_fullscreen:", args, kwargs
        """self.player.connect("fullscreen", 
                            self.user_file_info_treeview.on_fullscreen)
        self.player.connect("hide-controls", 
                            self.user_file_info_treeview.on_hide_controls)
        self.player.connect("show-controls", 
                            self.user_file_info_treeview.on_show_controls)"""
        self.show_hide_controls()

    def show_hide_controls(self, *args, **kwargs):
        playlist_rows = []
        playlist = self.playlist
        for file_info in playlist.files[playlist.index].listeners.user_file_info:
            if not file_info.fid:
                continue
            obj = {}
            for key in self.store_col_indexes.keys():
                obj[key] = getattr(file_info, key, -100000)
            playlist_rows.append(obj)
        if len(playlist_rows) == 0 or (self.fullscreen and self.is_video and 
           not self.playlist.player.showing_controls):
            self.treeview.hide()
        else:
            self.treeview.show()

    def on_hide_controls(self, *args, **kwargs):
        print "on_hide_controls:", args, kwargs
        self.show_hide_controls()

    def on_show_controls(self, *args, **kwargs):
        print "on_show_controls:", args, kwargs
        self.show_hide_controls()

    def init_store(self):
        # uid, uname, fid, rating, score, true_score
        self.ufi_store_structure = [
            {'fid': int},
            {'uid': int},
            {'uname': str},
            {'rating': int},
            {'score': int},
            {'true_score': float}
        ]

        self.store_types = []
        self.store_col_indexes = {}
        for i, item in enumerate(self.ufi_store_structure):
            for col, _type in item.items():
                self.store_col_indexes[col] = i
                self.store_types.append(_type)

        self.ufi_store = Gtk.TreeStore(*self.store_types)

    def init_treeview(self):
        self.treeview = Gtk.TreeView(self.ufi_store)

    def init_treeview_cols(self):
        self.treeview_columns = [
            {'uname': Gtk.TreeViewColumn("User")},
            {'rating': Gtk.TreeViewColumn("Rating")},
            {'score': Gtk.TreeViewColumn('Score')},
            {'true_score': Gtk.TreeViewColumn('True Score')}
        ]

        self.treeview_column_labels = {
            'uname': Gtk.Label(),
            'rating': Gtk.Label(),
            'score': Gtk.Label(),
            'true_score': Gtk.Label()
        }
        self.treeview_column_labels['uname'].set_markup(TOP_SPAN % "User")
        self.treeview_column_labels['rating'].set_markup(TOP_SPAN % "Rating")
        self.treeview_column_labels['score'].set_markup(TOP_SPAN % "Score")
        self.treeview_column_labels['true_score'].set_markup(
            TOP_SPAN % "True Score")
        for item in self.treeview_columns:
            for k, col in item.items():
                label = self.treeview_column_labels[k]
                label.set_ellipsize(Pango.EllipsizeMode.END)
                label.show()
                col.set_widget(label)
                col.set_property('resizable', True)
                col.set_property('expand', True)
                # col.set_property('sizing', Gtk.TreeViewColumnSizing.AUTOSIZE )

    def col_idx(self, key):
        return self.store_col_indexes[key]

    def cell_text(self, editable=False):
        cell = Gtk.CellRendererText()
        cell.set_property("editable", editable)
        font = Pango.FontDescription('FreeSans bold 15')
        cell.set_property('font-desc', font)
        cell.set_property('ellipsize-set', True)
        cell.set_property('ellipsize', Pango.EllipsizeMode.MIDDLE)
        return cell

    def init_cells(self):
        self.init_rating_combo()
        self.cells = {
            'uname': self.cell_text(),
            'rating': self.rating_combo,
            'score': self.cell_text(),
            'true_score': self.cell_text(),
        }

    def init_rating_combo(self):
        self.liststore_ratings = Gtk.ListStore(str)
        for i in range(5, -1, -1):
            self.liststore_ratings.append([str(i)])
        self.rating_combo = Gtk.CellRendererCombo()
        self.rating_combo.set_property("editable", True)
        self.rating_combo.set_property("model", self.liststore_ratings)
        self.rating_combo.set_property("text-column", 0)
        self.rating_combo.set_property("has-entry", False)
        self.rating_combo.connect("edited", self.on_rating_combo_change)
        font = Pango.FontDescription('FreeSans bold 15')
        self.rating_combo.set_property('font-desc', font)

        store = Gtk.ListStore(str, GdkPixbuf.Pixbuf)
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size("images/rate.6.svg", 32, 32)
        store.append(["Test", pb])
        renderer = Gtk.CellRendererPixbuf()
        # self.rating_combo.pack_start(renderer, False)
        # self.rating_combo.add_attribute(renderer, "pixbuf", 1)

        return self.rating_combo

    def on_rating_combo_change(self, cell, path, text):
        # <CellRendererCombo object at 0x7f75e2926320 (GtkCellRendererCombo at 0x1180660)>, '0', '4'
        rating = int(text)
        logger.debug("+"*100)
        logger.debug("on_rating_combo_change: cell:%s path:%s rating:%s" % 
                     (cell, path, rating))

        rating_idx = self.col_idx('rating')
        self.ufi_store[path][rating_idx] = rating

        true_score_idx = self.col_idx('true_score')
        
        uid_idx = self.col_idx('uid')
        uid = self.ufi_store[path][uid_idx]
        
        index = self.playlist.index
        for file_info in self.playlist.files[index].listeners.user_file_info:
            if file_info.uid == uid:
                logger.debug("uid:%s rating:%s"  % (uid, rating))
                file_info.rating = rating
                self.ufi_store[path][true_score_idx] = file_info.true_score
        self.playlist.broadcast_change()

    def pack_treeview_cols(self):
        for col_data in self.treeview_columns:
            for key, col in col_data.items():
                cell = self.cells[key]
                idx = self.col_idx(key)
                logger.debug("key:%s" % key)
                logger.debug("col:%s" % col)
                logger.debug("cell:%s" % cell)
                logger.debug("idx:%s" % idx)
                col.pack_start(cell, True)
                col.add_attribute(cell, "text", idx)
                self.treeview.append_column(col)

    def update(self, playlist, broadcast_change=True):
        store_rows = []
        for store_row in self.ufi_store:
            obj = {}
            for key in self.store_col_indexes.keys():
                idx = self.col_idx(key)
                try:
                    obj[key] = store_row[idx]
                except Exception, e:
                    logger.error("Exception: %s" % e)
            store_rows.append(obj)

        playlist_rows = []
        for file_info in playlist.files[playlist.index].listeners.user_file_info:
            if not file_info.fid:
                continue
            obj = {}
            for key in self.store_col_indexes.keys():
                obj[key] = getattr(file_info, key, -100000)
            playlist_rows.append(obj)

        if len(playlist_rows) == 0 or (self.fullscreen and self.is_video and 
           not self.playlist.player.showing_controls):
            self.treeview.hide()
        else:
            self.treeview.show()

        if playlist_rows == store_rows:
            logger.debug("Nothing has changed not updating treeview.")
            return

        self.ufi_store.clear()
        try:
            for file_info in playlist.files[playlist.index].listeners.user_file_info:
                if not file_info.fid:
                    continue
                logger.debug("appending:%s" % (file_info.kwargs))
                row = []
                col_numbers = []
                
                treeiter = self.ufi_store.append(None, None)
                for col_number, item in enumerate(self.ufi_store_structure):
                    for k, v in item.items():
                        
                        if hasattr(file_info, k):
                            value = getattr(file_info,k )
                            logger.debug("GETATTR k:%s value:%s" % (k, value))
                            # row.append(value)
                            self.ufi_store.set_value(treeiter, col_number, value)
                            continue
                        if k in file_info.kwargs:
                            value = file_info.kwargs.get(k)
                            logger.debug("FALLBACK k:%s value:%s" % (k, value))
                            # row.append(value)
                            self.ufi_store.set_value(treeiter, col_number, value)
                            continue

                logger.debug("APPEND OK %s" % row)
                logger.debug("treeiter:%s" % treeiter)
        except Exception, e:
            logger.debug("Exception:%s" % e)
        if broadcast_change:
            server.broadcast({"player-playing": playlist.files[playlist.index].json()})


class FmpPlayer(Player):
    __name__ = 'FmpPlayer'
    def __init__(self, *args, **kwargs):
        super(FmpPlayer, self).__init__(*args, **kwargs)
        self.window.set_title("Family Media Player")

    def init_window_image(self):
        img_path = self.get_img_path()
        self.window.set_icon_from_file(os.path.join(img_path, "fmp-logo.svg"))

    def init_debug_window(self):
        self.init_listeners_window()
        super(FmpPlayer, self).init_debug_window()

    def init_listeners_window(self):
        self.listeners_scrolled_window = Gtk.ScrolledWindow()
        self.listeners_scrolled_window.add(ListenersTable.treeview)
        self.stack.add_titled(self.listeners_scrolled_window, 
                              "Listeners",
                              "Listeners")
        return

    def json(self):
        res = {
            'artist_title': self.artist_title,
            'artist': self.artist,
            'title': self.title,
            'uri': self.uri,
            'last_time_status': self.last_time_status
        }
        print "PLAYER:", res
        return res

class FmpPlaylist(Playlist):
    __name__ = 'FmpPlaylist'
    logger = logger

    def __init__(self, *args, **kwargs):
        kwargs['player'] = FmpPlayer()
        self.last_marked_as_played = 0
        self.last_position = -1
        self.user_file_info_treeview = UserFileInfoTreeview(self)
        super(FmpPlaylist, self).__init__(*args, **kwargs)
        self.user_file_info_tray = RatingTrayIcon(self)
        self.player.connect("fullscreen", 
                            self.user_file_info_treeview.show_hide_controls)
        self.player.connect("hide-controls", 
                            self.user_file_info_treeview.show_hide_controls)
        self.player.connect("show-controls", 
                            self.user_file_info_treeview.show_hide_controls)
        self.player.video_area_vbox.pack_start(
            self.user_file_info_treeview.treeview, False, False, 0)
        self.user_file_info_treeview.treeview.show()
        self.update_treeview()

        GObject.timeout_add_seconds(5, self.update_treeview)
        self.player.window.connect('key-press-event', self.on_key_press)

    def on_key_press(self, widget, event):
        res = super(FmpPlaylist, self).on_key_press(widget, event)
        keyname = Gdk.keyval_name(event.keyval)
        if keyname in ('f', 'F'):
            self.user_file_info_treeview.is_video = self.player.is_video
            self.user_file_info_treeview.fullscreen = self.player.fullscreen
            self.user_file_info_treeview.update(self)


    def broadcast_change(self,  *args, **kwargs):
        server.broadcast({"state-changed": self.player.state_string})
        server.broadcast({"player-playing": self.files[self.index].json()})
        self.user_file_info_treeview.update(self, broadcast_change=False)
        if hasattr(self, 'user_file_info_tray'):
            self.user_file_info_tray.on_artist_title_changed(broadcast_change=False)

    def update_treeview(self):
        print "="*100
        self.user_file_info_treeview.update(self)
        return True

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
        print "fid:", self.files[self.index].fid
        print "eid:", self.files[self.index].eid
        print "FILENAME:", filename
        if filename:
            self.player.uri = self.files[self.index].filename
            self.update_treeview()
        else:
            fid = self.files[self.index].fid
            if fid:
                print "HAS FID:", fid
                self.fid_sanity_check(fid)
            print "NO FILENAME"

    def fid_sanity_check(self, fid):
        sql = """SELECT * FROM file_locations WHERE fid = %(fid)s"""
        spec = {'fid': fid}
        file_locations = get_results_assoc_dict(sql, spec)
        if not file_locations:
            print "NO FILE LOCATIONS wiping."
            fid = deepcopy(fid)
            self.inc_index()
            delete_fid(fid)

    def init_connections(self):
        self.player.connect('time-status', self.mark_as_played)
        self.player.connect('state-changed', self.save_config)
        self.player.connect('time-status', self.broadcast_time)

    def save_config(self, player, state):
        Gdk.threads_leave()
        state = player.state_to_string(state)
        cfg.set('player_state', 'state', state , str)
        self.broadcast_change()

    def mark_as_played(self, player, time_status):
        Gdk.threads_leave()
        now = time()

        position = time_status['position']
        one_second = 1000000000.0
        drifted = (position - self.last_position) / one_second
        if drifted > 5 or drifted < -5:
            # The file was seeked.  Force a mark_as_played
            self.last_marked_as_played = 0

        # self.log_debug("drifted:%s seconds" % drifted)
        self.last_position = position
        if self.last_marked_as_played > now - 5:
            # self.log_debug("!.mark_as_played()")
            return
        self.log_debug(".mark_as_played()")
        self.last_marked_as_played = now
        try:
            self.files[self.index].mark_as_played(**time_status)
        except AttributeError:
            sys.exit()
        
    def force_broadcast_time(self):
        if not hasattr(self, 'last_time_status'):
            self.last_time_status = {}
        self.broadcast_time(self.player, self.last_time_status, True)
        
    def broadcast_time(self, player, time_status, force=False):
        Gdk.threads_leave()
        if not hasattr(self, 'last_time_status'):
            self.last_time_status = {}
        if time_status == self.last_time_status and not force:
            return
        self.last_time_status = deepcopy(time_status)
        time_status['now'] = "%s" % time_status['now']

        server.broadcast({"time-status": time_status})

    def next(self, *args, **kwargs):
        Gdk.threads_leave()
        self.log_debug(".next()")
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
        
        try:
            for file_info in self.files[self.index].listeners.user_file_info:
                self.log_info("uname:%s", file_info.uname)
                self.log_info("score:%s", file_info.score)
        except:
            pass
        preload.refresh()
        server.broadcast({"player-playing": self.files[self.index].json()})


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

    def json(self):
        files = []
        for file_obj in self.files:
            files.append(file_obj.json())
        
        # TODO add config variable
        unlistened_episodes = get_unlistend_episode(limit=10)
        netcasts = []
        for n in unlistened_episodes:
            netcasts.append(n.json())

        return {
            'index': self.index,
            'player': self.player.json(),
            'player_playing': self.files[self.index].json(),
            'files': files,
            'netcasts': netcasts,
            'users': get_users()
        }

def refresh_netcasts_once():
    refresh_netcasts()
    seconds_to_next_expire = get_seconds_to_next_expire_time()
    if not seconds_to_next_expire or seconds_to_next_expire < 60:
        # At the minimum we want to wait 60 seconds to the next time we call
        # this def
        seconds_to_next_expire = 60
    logger.debug("MINUTES TO NEXT EXPIRE:%s" % (seconds_to_next_expire / 60))
    seconds_to_next_expire = 60
    GObject.timeout_add_seconds(seconds_to_next_expire, refresh_netcasts_once)

def refresh_netcasts():
    logger.debug("STARTING REFRESH NETCASTS")
    t = Thread(target=refresh_and_download_all_netcasts)
    #t = Thread(target=myfunc2)
    t.start()
    return True
    
preload = Preload()
server.preload = preload
picker.initial_picker()
GObject.timeout_add_seconds(60, preload.refresh)
GObject.timeout_add_seconds(60, picker.populate_preload_for_all_users)
# refresh_netcasts_timeout = GObject.timeout_add_seconds(120, refresh_netcasts)
GObject.idle_add(preload.refresh_once)
GObject.idle_add(refresh_netcasts_once)

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

print "**** TEST ****"
res = get_unlistend_episode()
print "TEST:", res
Gtk.main()
