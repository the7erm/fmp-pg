#!/usr/bin/env python
# lib/history_dialog.py -- Display files in preload
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
import gtk, gobject, os, datetime, math
from subprocess import Popen

class HistoryDialog(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.init_containers()
        
        self.history_length = 100
        self.change_locked = False
        self.tv = None
        self.create_treeview()
        gobject.timeout_add(10000, self.refresh_data)

    def init_containers(self):
        self.vbox = gtk.VBox()
        self.vbox.show()
        self.add(self.vbox)

        self.scrolled_window = gtk.ScrolledWindow()
        self.scrolled_window.show()
        self.vbox.pack_start(self.scrolled_window)
        
        self.hbox = gtk.HBox()
        self.vbox.pack_end(self.hbox,False,False)

        self.more_button = gtk.Button()
        self.more_button.show()
        img = gtk.Image()
        img.show()
        img.set_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
        self.more_button.set_image(img)
        self.more_button.set_label("More")
        self.more_button.connect("clicked",self.on_more)
        
        self.hbox.show()
        self.hbox.pack_end(self.more_button,False, True)


    def on_more(self, *args,**kwargs):
        self.history_length = self.history_length + 100
        self.refresh_data()


    def create_treeview(self):
        if self.tv:
            self.tv.destroy()
        self.tv = gtk.TreeView()

        self.tv.connect("row-activated",self.on_row_activate)
        self.tv.show()
        self.setup_cols()
        self.scrolled_window.add(self.tv)
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

    def get_listeners(self):
        return get_results_assoc("""SELECT * 
                                    FROM users 
                                    WHERE listening = true 
                                    ORDER BY admin DESC, uname ASC""")


    def setup_cols(self):
        
        self.cols = [
            int, # id
            str, # id_type
            str, # basename
        ]
        self.user_map_cols = {}
        self.user_cols = {}
        
        self.listeners = self.get_listeners();
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
            [str, 'age'],
            [float, 'ultp_epoch'],
            [float, 'age_epoch']
        ]

        for u in self.listeners:
            print u
            for typ, c in cols:
                print typ, c
                self.cols.append(typ)
                if not self.user_cols.has_key(u['uid']):
                    self.user_cols[u['uid']] = {}
                self.user_map_cols[col_number] = {'uid':u['uid'], 'col':c, 
                                                  'typ':typ}
                self.user_cols[u['uid']][c] = col_number
                col_number = col_number + 1

        self.liststore = gtk.ListStore(*self.cols)

        self.refresh_data()

        self.append_simple_col("Filename",1)
        
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
                                   self.user_cols[u['uid']]['ultp_epoch'])

        for u in self.listeners:
            c = self.append_simple_col('%s\'s Age' % (u['uname'],), 
                                   self.user_cols[u['uid']]['age'],
                                   self.user_cols[u['uid']]['age_epoch'])
            c.set_sort_order(gtk.SORT_DESCENDING)
            c.set_sort_indicator(True)


    def append_simple_col(self, text, col_id, sort_col=None):
        col = gtk.TreeViewColumn(text, gtk.CellRendererText(), text=col_id)
        if sort_col is not None:
            col.set_sort_column_id(sort_col)
        else:
            col.set_sort_column_id(col_id)

        col.set_resizable(True)
        self.tv.append_column(col)
        return col


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
            res = get_assoc("""UPDATE user_song_info 
                               SET rating = %s, 
                                   true_score = (((%s * 2 * 10) + (score * 10) + 
                                                   percent_played) / 3) 
                               WHERE uid = %s AND fid = %s RETURNING *""",
                               (rating, rating, uid, fid))
            liststore[path][self.user_cols[uid]['true_score']] = res['true_score']
        self.change_locked = False

    def on_key_press_event(self,w,event):
        print "on_key_press_event"
        name = gtk.gdk.keyval_name(event.keyval)
        print "keyname:",name
        """
        if name == "Delete" or name == 'KP_Delete':
            self.remove_selected()
            return True # stop beep
        """


    def refresh_data(self):
        print "history_dialog.refresh_data"
        cols = ['uid', 'rating', 'score', 'percent_played', 'true_score', 
                'ultp', 'age', 'ultp_epoch', 'age_epoch']
        self.change_locked = True
        listeners = self.get_listeners()
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
        # SELECT uh.*, u.uname FROM user_history uh, users u WHERE u.uid = uh.uid AND u.listening = true ORDER BY time_played DESC LIMIT 10
        files = get_results_assoc("""SELECT f.fid, id, id_type, u.uname, f.basename
                                     FROM user_history uh 
                                          LEFT JOIN files f ON f.fid = uh.id AND
                                                    uh.id_type = 'f',
                                          users u
                                     WHERE u.uid = uh.uid AND u.listening = true
                                           AND id_type = 'f'
                                     ORDER BY time_played DESC LIMIT %d""" %
                                     self.history_length)
                                     # for the time being it's just pulling files
                                     # TODO add netcasts, and generic files.
        
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
        if f['id_type'] == 'f':
            q = pg_cur.mogrify("""SELECT *, age(now(), ultp) AS \"age\",
                                         EXTRACT(EPOCH FROM ultp) AS \"ultp_epoch\",
                                         EXTRACT(EPOCH FROM age(now(), ultp)) AS \"age_epoch\"
                                  FROM users u, user_song_info us 
                                  WHERE us.uid = u.uid AND u.listening = true AND 
                                        us.fid = %s 
                                  ORDER BY admin DESC, uname""", (f['id'],))
        elif f['id_type'] == 'e':
            q = pg_cur.mogrify("""SELECT *, age(now(), ultp) AS \"age\",
                                         EXTRACT(EPOCH FROM ultp) AS \"ultp_epoch\",
                                         EXTRACT(EPOCH FROM age(now(), ultp)) AS \"age_epoch\"
                                  FROM users u, user_song_info us 
                                  WHERE us.uid = u.uid AND u.listening = true AND 
                                        us.fid = %s 
                                  ORDER BY admin DESC, uname""", (f['id'],))

        # print q
        db_user_file_info = get_results_assoc(q)
        user_file_info = []

        for r in db_user_file_info:
            r = dict(r)
            for k, c in r.iteritems():
                if isinstance(c, datetime.datetime):
                    c = c.strftime("%c")

                if isinstance(c, datetime.timedelta):
                    c = convert_delta_to_str(c)

                if k in ('ultp_epoch','age_epoch'):
                    if c is None:
                        c = 0
                    c = float(c)
                r[k] = c

            user_file_info.append(r)

        for r in self.liststore:
            if r[0] == f['id']:
                found = True
                self.update_row(r, cols, user_file_info)
                break
        if found:
            return None

        row = [
            f['id'],
            f['basename'],
            f['uname'],
        ]
        print "cols:",cols
        for u in user_file_info:
            for c in cols:
                row.append(u[c])

        return row

    def update_row(self, r, cols, user_file_info):
        if gtk.events_pending():
            while gtk.events_pending():
                # print "pending:"
                gtk.main_iteration(False)
        for u in user_file_info:
            for c in cols:
                c_num = self.user_cols[u['uid']][c]
                if r[c_num] != u[c]:
                    print "update_row:",r[c_num], "!=", u[c]
                    r[c_num] = u[c]
                    

    def insert_ratings(self):
        for u in self.listeners:
            default_rating = 6
            default_score = 5
            default_percent_played = 50.0
            default_true_score = ((default_rating * 2 * 10.0) + (default_score * 10.0) + (default_percent_played) / 3)

            m = pg_cur.mogrify("SELECT fid FROM user_song_info WHERE uid = %s", (u['uid'],))
            q = """INSERT INTO user_song_info (fid, uid, rating, score, 
                                               percent_played, true_score) 
                   SELECT f.fid, '%s', '%s', '%s', '%s', '%s' 
                   FROM files f 
                   WHERE f.fid NOT IN (%s)""" % (u['uid'], default_rating, 
                                                 default_score, 
                                                 default_percent_played, 
                                                 default_true_score, m)
            query(q)


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
    history = HistoryDialog()
    w = gtk.Window()
    history.set_title("FMP - History")
    history.set_default_size(800,600)
    history.set_position(gtk.WIN_POS_CENTER)
    history.connect("destroy", gtk.main_quit)
    history.show()
    # w.maximize()
    gtk.main()


