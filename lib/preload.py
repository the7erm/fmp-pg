#!/usr/bin/env python
# lib/preload.py -- Display files in preload
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

from __init__ import *
from star_cell import CellRendererStar
import gtk, gobject, os
from subprocess import Popen

class Preload(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.change_locked = False
        self.tv = None
        self.create_treeview()
        gobject.timeout_add(10000, self.refresh_data)

    def create_treeview(self):
        if self.tv:
            self.tv.destroy()
        self.tv = gtk.TreeView()
        self.tv.connect("row-activated",self.on_row_activate)
        self.tv.show()
        self.setup_cols()
        self.add(self.tv)
        self.tv.set_model(self.liststore)

        self.liststore.connect("row-changed", self.on_row_change)
        
        selection = self.tv.get_selection()
        selection.set_mode(gtk.SELECTION_MULTIPLE)
        self.tv.set_rubber_banding(True)
        self.tv.connect("key_press_event", self.on_key_press_event)

    def on_row_activate(self,treeview, path, view_column):
        fid = str(self.liststore[path][0])
        print "fid:",fid
        if os.path.exists(sys.path[0]+"/file_info.py"):
            Popen([sys.path[0]+"/file_info.py", fid])
            return
        if os.path.exists(sys.path[0]+"/lib/file_info.py"):
            Popen([sys.path[0]+"/lib/file_info.py", fid])
            return
        if os.path.exists(sys.path[0]+"/../lib/file_info.py"):
            Popen([sys.path[0]+"/../lib/file_info.py", fid])
            return

    def setup_cols(self):
        
        self.cols = [
            int, # fid
            str, # basename
            str, # cued for
            str, # reason
        ]
        self.user_map_cols = {}
        self.user_cols = {}
        
        self.listeners = get_results_assoc("SELECT * FROM users WHERE listening = true ORDER BY admin DESC, uname ASC")
        """
             Column     |           Type           |                           Modifiers           
            ----------------+--------------------------+-----------------------------------------------
             usid           | integer                  | not null default nextval('user_song_info_usid_
             uid            | integer                  | not null
             fid            | integer                  | not null
             rating         | integer                  | default 6
             score          | integer                  | default 5
             percent_played | double precision         | default 50.00
             ultp           | timestamp with time zone | 
             true_score     | double precision         | default 50.00

        """
        col_number = len(self.cols)
        cols = [
            [int, 'uid'],
            [int, 'rating'], 
            [int, 'score'],
            [float, 'percent_played'],
            [float, 'true_score']
        ]

        for u in self.listeners:
            print u
            for typ, c in cols:
                print typ, c
                self.cols.append(typ)
                if not self.user_cols.has_key(u['uid']):
                    self.user_cols[u['uid']] = {}
                self.user_map_cols[col_number] = {'uid':u['uid'], 'col':c}
                self.user_cols[u['uid']][c] = col_number
                col_number = col_number + 1

        self.liststore = gtk.ListStore(*self.cols)
        

        self.refresh_data()

        self.append_simple_col("Filename",1)
        self.append_simple_col("Cued For",2)
        self.append_simple_col("Reason",3)
        for u in self.listeners:
            cell = CellRendererStar(15, self.user_cols[u['uid']]['rating'])
            cell.set_property('xalign',0.0)
            col = gtk.TreeViewColumn('%s\'s Rating' % (u['uname'],), cell, rating=self.user_cols[u['uid']]['rating'])
            col.set_sort_column_id(self.user_cols[u['uid']]['rating'])
            col.set_resizable(True)
            self.tv.append_column(col)
            self.tv.connect("motion-notify-event", cell.on_motion_notify)
            self.tv.connect("button-press-event", cell.on_button_press)

        for u in self.listeners:
            self.append_simple_col('%s\'s Skip Score' % (u['uname'],),self.user_cols[u['uid']]['score'])

        for u in self.listeners:
            self.append_simple_col('%s\'s Percent Played' % (u['uname'],),self.user_cols[u['uid']]['percent_played'])

        for u in self.listeners:
            self.append_simple_col('%s\'s True Score' % (u['uname'],),self.user_cols[u['uid']]['true_score'])

    def append_simple_col(self, text, col_id):
        col = gtk.TreeViewColumn(text, gtk.CellRendererText(), text=col_id)
        col.set_sort_column_id(col_id)
        col.set_resizable(True)
        self.tv.append_column(col)


    def on_row_change(self, liststore, path, itr):
        # print "change_locked:",self.change_locked
        if self.change_locked:
            return
        self.change_locked = True
        fid = liststore[path][0]
        print "fid:",fid
        for uid in self.user_cols:
            print "uid:",uid
            rating = self.liststore[path][self.user_cols[uid]['rating']]
            print "rating:", rating
            res = get_assoc("UPDATE user_song_info SET rating = %s, true_score = (((%s * 2 * 10) + (score * 10) + percent_played) / 3) WHERE uid = %s AND fid = %s RETURNING *",(rating, rating, uid, fid))
            liststore[path][self.user_cols[uid]['true_score']] = res['true_score']
        self.change_locked = False

    def on_key_press_event(self,w,event):
        print "on_key_press_event"
        name = gtk.gdk.keyval_name(event.keyval)
        if name == "Delete":
            self.remove_selected()
            return True # stop beep

    def remove_selected(self):
        selection = self.tv.get_selection()
        model, selected = selection.get_selected_rows()
        selected.sort(reverse=True)
        rows = []
        for path in selected:
            print "SELECTED:",path
            selection.unselect_path(path)
            itr = self.liststore.get_iter(path)
            fid = self.liststore[path][0]
            query("DELETE FROM preload WHERE fid = %s",(fid,))
            self.liststore.remove(itr)



    def refresh_data(self):
        print "refresh_data"
        cols = ['uid', 'rating', 'score', 'percent_played', 'true_score']
        self.change_locked = True
        listeners = get_results_assoc("SELECT * FROM users WHERE listening = true ORDER BY admin DESC, uname ASC")
        if len(self.listeners) != len(listeners):
            self.listeners = listeners
            self.create_treeview()
            return True
        else:
            for l in listeners:
                found = False
                for l2 in self.listeners:
                    if l['uid'] == l2['uid']:
                        found = True
                        break
                if not found:
                    self.listeners = listeners
                    self.create_treeview()
                    return True

        files = get_results_assoc("SELECT p.fid, basename, p.uid, u.uname, reason FROM preload p, files f, users u WHERE f.fid = p.fid AND u.uid = p.uid ORDER BY basename")
        
        for f in files:
            row = self.create_row(f, cols)
            if not row:
                continue

            # print "row:",row
            # print "cols:",self.cols
            try:
                self.liststore.append(row)
            except ValueError:
                self.insert_ratings()
                row = self.create_row(f, cols)
                if not row:
                    continue
                self.liststore.append(row)

        self.change_locked = False

        for r in self.liststore:
            found = False
            for f in files:
                if r[0] == f['fid']:
                    found = True
            if not found:
                self.liststore.remove(r.iter)
        return True

    def create_row(self, f, cols):
        found = False
        user_file_info = get_results_assoc("SELECT * FROM users u, user_song_info us WHERE us.uid = u.uid AND u.listening = true AND us.fid = %s ORDER BY admin DESC, uname", (f['fid'],))
        for r in self.liststore:
            if r[0] == f['fid']:
                found = True
                self.update_row(r, cols, user_file_info)
                break
        if found:
            return None

        row = [
            f['fid'],
            f['basename'],
            f['uname'],
            f['reason']
        ]
        
        for u in user_file_info:
            for c in cols:
                row.append(u[c])

        return row

    def update_row(self, r, cols, user_file_info):
        for u in user_file_info:
            for c in cols:
                c_num = self.user_cols[u['uid']][c]
                if r[c_num] != u[c]:
                    r[c_num] = u[c]

    def insert_ratings(self):
        for u in self.listeners:
            default_rating = 6
            default_score = 5
            default_percent_played = 50.0
            default_true_score = ((default_rating * 2 * 10.0) + (default_score * 10.0) + (default_percent_played) / 3)

            m = pg_cur.mogrify("SELECT fid FROM user_song_info WHERE uid = %s", (u['uid'],))
            q = "INSERT INTO user_song_info (fid, uid, rating, score, percent_played, true_score) SELECT f.fid, '%s', '%s', '%s', '%s', '%s' FROM files f WHERE f.fid NOT IN (%s)" % (u['uid'], default_rating, default_score, default_percent_played, default_true_score, m)
            query(q)

if __name__ == "__main__":
    
    preload = Preload()
    w = gtk.Window()
    w.set_title("FMP - Preload")
    w.set_default_size(800,600)
    w.set_position(gtk.WIN_POS_CENTER)
    w.add(preload)
    w.show_all()
    w.connect("destroy", gtk.main_quit)
    # w.maximize()
    gtk.main()


