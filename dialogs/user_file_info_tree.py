#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
# Copyright 2013 Eugene R. Miller
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/>.
#

from star_cell import CellRendererStar
from __init__ import *
import gtk, random, gobject
from file_objects.rating_utils import rate_for_uid


class User_File_Info_Tree(gtk.TreeView):
    def __init__(self, fid=None):
        gtk.TreeView.__init__(self)
        self.change_locked = False
        self.fid = None
        # uid, uname, rating, score, true_score, percent_played, ultp
        self.store = gtk.ListStore(
            int, # uid
            str, # uname
            int, # rating
            int, # score
            float, # true_score
            float, # percent_played
            str, # ultp
        )
        
        self.set_model(self.store)
        self.set_headers_visible(True)
        self.append_simple_col("Username", 1)
        
        cell = CellRendererStar(15,2)
        cell.set_property('xalign',0.0)
        col = gtk.TreeViewColumn('Rating', cell, rating=2)
        col.set_sort_column_id(2)
        self.append_column(col)
        self.connect("motion-notify-event", cell.on_motion_notify)
        self.connect("button-press-event", cell.on_button_press)

        self.append_simple_col("Skip Score", 3)
        self.append_simple_col("True Score", 4)
        self.append_simple_col("% Played", 5)
        self.append_simple_col("Last Time Played", 6)

        # self.connect("key-release-event", self.on_key_release)

        # self.set_property('reorderable',True)
        # self.set_property('rubber-banding', True)
        # select = self.get_selection()
        # select.set_mode(gtk.SELECTION_MULTIPLE)

        self.query = pg_cur.mogrify("""SELECT * 
                                       FROM users u, user_song_info ui 
                                       WHERE u.uid = ui.uid AND ui.fid = %s AND 
                                             listening = true 
                                       ORDER BY listening DESC, 
                                                admin DESC, 
                                                uname""", 
                                   (fid,))

        self.populate_liststore()
        if self.file_info:
            self.fid = fid

        gobject.timeout_add(4000, self.populate_liststore)
        self.store.connect("row-changed", self.on_row_change)

    def populate_liststore(self):
        self.change_locked = True
        print "User_File_Info_Tree:self.query:",self.query
        self.file_info = get_results_assoc(self.query)
        if len(self.file_info) < len(self.store):
            for i, r in enumerate(self.store):
                found = False
                for u in self.file_info:
                    if u['uid']  == r[0]:
                        found = True
                    break
                if not found:
                    # print "REMOVE:",r
                    del self.store[i]
                    break
        
        for u in self.file_info:
            found = False
            for r in self.store:
                if u['uid'] == r[0]:
                    found = True
                    if r[2] != u['rating']:
                        r[2] = u['rating']

                    if r[3] != u['score']:
                        r[3] = u['score']

                    if r[4] != u['true_score']:
                        r[4] = u['true_score']

                    if r[5] != u['percent_played']:
                        r[5] = u['percent_played']

                    if u['ultp'] is not None:
                        try:
                            if r[6] != u['ultp'].strftime("%c"):
                                r[6] = u['ultp'].strftime("%c")
                        except AttributeError, err:
                            r[6] = "Never"
                            u['ultp'] = "Never"
                            print "AttributeError:",err
                    else:
                        r[6] = "Never"
                        u['ultp'] = "Never"

                    break
            if not found:
                if u['ultp'] is None:
                    self.store.append([
                        u['uid'],
                        u['uname'],
                        u['rating'],
                        u['score'],
                        u['true_score'],
                        u['percent_played'],
                        "Never",
                    ])
                    continue
                try:
                    self.store.append([
                        u['uid'],
                        u['uname'],
                        u['rating'],
                        u['score'],
                        u['true_score'],
                        u['percent_played'],
                        u['ultp'].strftime("%c"),
                    ])
                except AttributeError, err:
                    
                    print "AttributeError:",err
                    continue
        
        self.change_locked = False
        return True

    def append_simple_col(self, text, col_id):
        col = gtk.TreeViewColumn(text, gtk.CellRendererText(), text=col_id)
        col.set_sort_column_id(col_id)
        self.append_column(col)

    def on_row_change(self,liststore, path, itr):
        if self.change_locked:
            return
        self.change_locked = True
        uid = int(liststore[path][0])
        uname = liststore[path][1]
        rating = int(liststore[path][2])
        res = rate_for_uid(self.fid, uid, rating)
        liststore[path][4] = res[0]['true_score']
        print "on_row_change: fid:%s uid:%s, uname:%s rating:%s" % (self.fid, uid, uname, rating)
        self.change_locked = False


def on_change(*args):
    #print "CHANGED!", args
    return

if __name__ == "__main__":
    w = gtk.Window()
    w.set_position(gtk.WIN_POS_CENTER)
    w.connect('delete-event', gtk_main_quit)
    finfo = get_assoc("""SELECT fid 
                         FROM user_song_info
                         WHERE ultp IS NOT NULL
                         ORDER BY ultp DESC
                         LIMIT 1""")
    if not finfo:
        finfo = get_assoc("""SELECT fid 
                             FROM user_song_info
                             ORDER BY ultp DESC
                             LIMIT 1""")
    t = User_File_Info_Tree(fid=finfo['fid'])
    m = t.get_model()
    m.connect("row-changed", on_change)
    # t.insert('foo')
    w.add(t)

    w.show_all()
    gtk.main()
