#!/usr/bin/env python2
# lib/preload.py -- Display files in preload
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

from __init__ import *
from picker import wait
from star_cell import CellRendererStar
import gtk
import gobject
import os
import datetime
import math
import pytz
from subprocess import Popen
from rating_utils import rate_for_uid
from picker import insert_missing_songs

gobject.threads_init()
gtk.gdk.threads_init()

class Preload(gtk.ScrolledWindow):
    def __init__(self):
        gtk.ScrolledWindow.__init__(self)
        self.reload_lock = False
        self.change_locked = False
        self.tv = None
        self.create_treeview()
        self.stop = False
        gobject.timeout_add(1000, self.refresh_data)


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
        
        self.listeners = get_results_assoc("""SELECT * 
                                              FROM users 
                                              WHERE listening = true 
                                              ORDER BY admin DESC, uname ASC""")
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
            [float, 'true_score'],
            [str, 'ultp'],
            [int, 'ultp_int'],
            [str, 'age'],
            [int, 'age_int']
        ]

        for u in self.listeners:
            print u
            for typ, c in cols:
                print typ, c
                self.cols.append(typ)
                if u['uid'] not in self.user_cols:
                    self.user_cols[u['uid']] = {}
                self.user_map_cols[col_number] = {'uid':u['uid'], 'col':c}
                self.user_cols[u['uid']][c] = col_number
                col_number = col_number + 1


        print "self.cols:",self.cols
        self.liststore = gtk.ListStore(*self.cols)
        

        # self.refresh_data()

        self.append_simple_col("Filename", 1)
        self.append_simple_col("Cued For", 2)
        self.append_simple_col("Reason", 3)
        for u in self.listeners:
            cell = CellRendererStar(15, self.user_cols[u['uid']]['rating'])
            cell.set_property('xalign',0.0)
            col = gtk.TreeViewColumn('%s\'s Rating' % (u['uname'],), cell, 
                                     rating=self.user_cols[u['uid']]['rating'])
            col.set_sort_column_id(self.user_cols[u['uid']]['rating'])
            col.set_resizable(True)
            self.tv.append_column(col)
            self.tv.connect("motion-notify-event", cell.on_motion_notify)
            self.tv.connect("button-press-event", cell.on_button_press)

        for u in self.listeners:
            self.append_simple_col('%s\'s Skip Score' % (u['uname'],),
                                   self.user_cols[u['uid']]['score'])

        for u in self.listeners:
            self.append_simple_col('%s\'s Percent Played' % (u['uname'],),
                                   self.user_cols[u['uid']]['percent_played'])

        for u in self.listeners:
            self.append_simple_col('%s\'s True Score' % (u['uname'],),
                                   self.user_cols[u['uid']]['true_score'])

        for u in self.listeners:
            self.append_simple_col('%s\'s Last time played' % (u['uname'],), 
                                   self.user_cols[u['uid']]['ultp'],
                                   self.user_cols[u['uid']]['ultp_int'])

        for u in self.listeners:
            self.append_simple_col('%s\'s Age' % (u['uname'],), 
                                   self.user_cols[u['uid']]['age'],
                                   self.user_cols[u['uid']]['age_int'])


    def append_simple_col(self, text, col_id, sort_col=None):
        col = gtk.TreeViewColumn(text, gtk.CellRendererText(), text=col_id)
        if sort_col is None:
            sort_col = col_id
        col.set_sort_column_id(sort_col)
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
            res = rate_for_uid(fid, uid, rating)
            liststore[path][self.user_cols[uid]['true_score']] = res['true_score']
        self.change_locked = False

    def on_key_press_event(self,w,event):
        print "on_key_press_event"
        name = gtk.gdk.keyval_name(event.keyval)
        print "keyname:",name
        if name == "Delete" or name == 'KP_Delete':
            self.remove_selected()
            return True # stop beep

    def remove_selected(self):
        selection = self.tv.get_selection()
        model, selected = selection.get_selected_rows()
        selected.sort(reverse=True)
        rows = []
        cnt = 0
        for path in selected:
            cnt += 1
            print "SELECTED:",path
            selection.unselect_path(path)
            itr = self.liststore.get_iter(path)
            fid = self.liststore[path][0]
            query("DELETE FROM preload WHERE fid = %s",(fid,))
            self.liststore.remove(itr)
            if cnt % 10 == 0:
                wait()

    def quit_on_stop(self):
        if self.stop:
            print "STOP"
            gtk.main_quit()

    def refresh_data(self):
        self.quit_on_stop()
        if self.reload_lock:
            print "reload_lock"

            return True
        self.reload_lock = True
        wait()
        print "preload.refresh_data"
        cols = ['uid', 'rating', 'score', 'percent_played', 'true_score', 'ultp', 
                'ultp_int', 'age', 'age_int']
        self.change_locked = True
        listeners = get_results_assoc("""SELECT *
                                         FROM users 
                                         WHERE listening = true 
                                         ORDER BY admin DESC, uname ASC""")
        if len(self.listeners) != len(listeners):
            self.listeners = listeners
            self.create_treeview()
            self.reload_lock = False 
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
        wait()
        print "fetching files"
        files = get_results_assoc("""SELECT p.fid, fl.dirname, fl.basename, 
                                            p.uid, u.uname, reason 
                                     FROM preload p, files f, users u,
                                          file_locations fl
                                     WHERE f.fid = p.fid AND u.uid = p.uid AND 
                                           fl.fid = p.fid
                                     ORDER BY fl.basename""")
        print "done fetching files"
        wait()
        for i, f in enumerate(files):
            if i % 15 == 0:
                wait()
                self.quit_on_stop()
            
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

        print "done looping through files"
        self.change_locked = False

        for r in self.liststore:
            found = False
            for f in files:
                if r[0] == f['fid']:
                    wait()
                    self.quit_on_stop()
                    found = True
                    break
            if not found:
                self.liststore.remove(r.iter)
                wait()
        self.reload_lock = False 
        return True

    def create_row(self, f, cols):
        found = False
        q = pg_cur.mogrify("""SELECT *, age(now(), ultp) AS \"age\" 
                              FROM users u, user_song_info us 
                              WHERE us.uid = u.uid AND u.listening = true AND 
                                    us.fid = %s 
                              ORDER BY admin DESC, uname""", (f['fid'],))
        # print q
        db_user_file_info = get_results_assoc(q)
        user_file_info = []

        for r in db_user_file_info:
            r = dict(r)
            for k in r.keys():
                c = r[k]
                if k in ('ultp', 'age'):
                    r[k+"_int"] = 0
                
                if not isinstance(c, datetime.datetime) and\
                   not isinstance(c, datetime.timedelta):
                    r[k] = c
                    continue
                
                if isinstance(c, datetime.datetime):
                    r[k] = c.strftime("%c")
                    r[k+"_int"] = int((c - datetime.datetime(1970,1,1,tzinfo=pytz.UTC)).total_seconds())

                if isinstance(c, datetime.timedelta):
                    r[k] = convert_delta_to_str(c)
                    r[k+"_int"] = int(c.total_seconds())

            user_file_info.append(r)

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
                    print "update_row:",r[c_num], "!=", u[c]
                    r[c_num] = u[c]
                    wait()

    def insert_ratings(self):
        for u in self.listeners:
            insert_missing_songs(u['uid'])

    def quit(self, *args, **kwargs):
        self.stop = True
        self.connect('event-after', gtk.main_quit)
        sys.exit()


def convert_delta_to_str(delta):
    c = ""
    
    days = delta.days
    years = 0
    months = 0
    weeks = 0
    parts = []

    try:
        years = int(math.floor(days / 365))
        if years > 1:
            parts.append("%s years" % years)
        elif years == 1:
            parts.append("%s year" % years)
    except ZeroDivisionError, err:
        pass

    days = days - (years * 365)

    try:
        months = int(math.floor(days / 30))
        if months > 1:
            parts.append("%s months" % months)
        elif months == 1:
            parts.append("%s month" % months)
    except ZeroDivisionError, err:
        pass

    days = days - (months * 30)

    try:
        weeks = int(math.floor(days / 7))
        if weeks > 1:
            parts.append("%s weeks" % weeks)
        elif weeks == 1:
            parts.append("%s week" % weeks)
    except ZeroDivisionError, err:
        pass

    days = days - (weeks * 7)

    days = int(days)
    if days > 1:
        parts.append("%s days" % days)
    elif days == 1:
        parts.append("%s day" % days)

    if parts:
        parts = parts[0:3]
        return " ".join(parts)

    secs = delta.seconds
    hrs = int(math.floor(secs / 3600))
    secs = secs - (hrs * 3600)
    mins = int(math.floor(secs / 60))
    secs = secs - (mins * 60)

    if len(parts) < 2:
        parts.append("%s:%02d:%02d" % (hrs, mins, secs))

    parts = parts[0:3]

    return " ".join(parts)



if __name__ == "__main__":
    
    preload = Preload()
    w = gtk.Window()
    w.set_title("FMP - Preload")
    w.set_default_size(800,600)
    w.set_position(gtk.WIN_POS_CENTER)
    w.add(preload)
    w.show_all()
    w.connect("destroy", preload.quit)
    preload.refresh_data()
    # w.maximize()
    gtk.main()


