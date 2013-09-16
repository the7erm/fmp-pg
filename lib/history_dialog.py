#!/usr/bin/env python
# lib/history_dialog.py -- Display files in history
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

from __init__ import *
from star_cell import CellRendererStar
import gtk
import gobject
gobject.threads_init()
import os
import datetime
import math
from subprocess import Popen
from preload import convert_delta_to_str
from listeners import listeners
import pprint
pp = pprint.PrettyPrinter(depth=6)

class TableSkel:
    def __init__(self,query=""):
        self.cols = []
        self.map = {}
        self.query = query
        self.subqueries = []
        self.liststore = None
        self.listeners_len = len(listeners.listeners)

    def add_subquery(self, prefix, query, args=[], when=None, many=False, key_funct=None):
        self.subqueries.append({
            "prefix": prefix,
            "query": query,
            "args": args,
            "when": when,
            "many": many,
            "key_funct":key_funct
        })

    def add_col(self, typ, table_col, title="", text_cell=False, sort_by_col=None):
        idx = len(self.cols)
        self.map[table_col] = idx

        obj = {
            "idx": idx,
            "typ": typ,
            "table_col": table_col,
        }

        if title:
            obj["title"] = title
            obj["tv_col"] = self.tv_col(title)

        self.cols.append(obj)

        if title and text_cell:
            obj['tv_col'].set_sort_column_id(obj['idx'])
            self.add_cell(obj['idx'], gtk.CellRendererText(), {"text": obj['idx']})

        if sort_by_col is not None:
            obj['tv_col'].set_sort_column_id(sort_by_col)

        return obj

    def tv_col(self, title):
        tvc = gtk.TreeViewColumn()
        tvc.set_visible(True)
        tvc.set_sort_indicator(True)
        tvc.set_sizing(gtk.TREE_VIEW_COLUMN_AUTOSIZE)
        tvc.set_title(title)
        return tvc

    def perform_query(self):
        return self.fix_rows(get_results_assoc(self.query))

    def fix_rows(self, res):
        new_res = []
        for r in res:
            row = self.fix_cols(r)
            new_res.append(row)
        return new_res

    def fix_cols(self, r):
        row = {}
        for k, v in r.iteritems():
            if isinstance(v, datetime.datetime):
                v = v.strftime("%c")

            if isinstance(v, datetime.date):
                v = v.strftime("%Y-%m-%d")

            if isinstance(v, datetime.timedelta):
                v = convert_delta_to_str(c)

            row[k] = v
        return row

    def get_rows(self, force_fetch=False):
        res = self.perform_query()
        rows = []
        for r in res:
            self.wait()
            if self.liststore and not force_fetch:
                global change_lock
                change_lock = True
                self.liststore.append(self.create_row(r))
                change_lock = False
            else:
                rows.append(self.create_row(r))
        return rows

    def create_row(self, r):
        row = []
        for s in self.subqueries:
            self.perform_subquery(r, s)
        # pp.pprint(r)
        for c in self.cols:

            row.append(r[c['table_col']])
        return row

    def perform_subquery(self, row, subquery):

        if subquery.has_key("when") and subquery["when"] and not subquery["when"](row):
            return
        args = []
        for a in subquery['args']:
            args.append(row[a])

        if subquery.has_key("many") and subquery["many"]:
            res = self.fix_rows(get_results_assoc(subquery["query"], args))
            for i, res_row in enumerate(res):
                idx = "%s" % i
                if subquery.has_key("key_funct") and subquery["key_funct"]:
                    idx = subquery["key_funct"](res_row)
                for k, v in res_row.iteritems():
                    key = "%s.%s.%s" % (subquery["prefix"], idx, k)
                    # print "key:",key
                    row[key] = v
        else:
            res = self.fix_cols(get_assoc(subquery["query"], args))
            for k, v in res.iteritems():
                if subquery.has_key("key_funct") and subquery["key_funct"]:
                    k = subquery["key_funct"](res)
                key = "%s.%s" % (subquery["prefix"], k)
                row[key] = v

    def get_liststore_cols(self):
        cols = []
        for c in self.cols:
            cols.append(c['typ'])
        return cols

    def add_cols_to_treeview(self, treeview):
        for c in self.cols:
            if c.has_key("tv_col"):
                treeview.append_column(c["tv_col"])
                c["tv_col"].set_resizable(True)

    def add_cell(self, idx, cell, attribs={}):
        self.cols[idx]['cell'] = cell
        self.cols[idx]['tv_col'].pack_start(self.cols[idx]['cell'])
        self.cols[idx]['tv_col'].set_attributes(self.cols[idx]['cell'], **attribs)

    def get_liststore(self):
        if not self.liststore:
            self.liststore = gtk.ListStore(*self.get_liststore_cols())
        return self.liststore

    def populate_liststore(self):
        rows = self.get_rows()

    def wait(self):
        if gtk.events_pending():
            while gtk.events_pending():
                gtk.main_iteration(False)

    def refresh_data(self, based_on=""):
        if not based_on or not self.liststore:
            return True
        global change_lock
        fresh_rows = self.get_rows(True)
        for fresh_row in fresh_rows:
            col_number = self.map[based_on]
            found = False
            for ils, liststore_row in enumerate(self.liststore):
                if liststore_row[col_number] != fresh_row[col_number]:
                    continue
                found = True
                for i2, fr in enumerate(fresh_row):
                    if "%s" % liststore_row[i2] != "%s" % fresh_row[i2]:
                        change_lock = True
                        print liststore_row[i2],"!=",fresh_row[i2]
                        liststore_row[i2] = fresh_row[i2]
                        change_lock = False
                break
                
            if not found:
                change_lock = True
                self.liststore.append(fresh_row)
                change_lock = False

        return True


if __name__ == '__main__':
    history_length = 50
    global change_lock
    change_lock = False

    def id_type_is_f(row):
        return row['id_type'] == 'f'

    def id_type_is_e(row):
        return row['id_type'] == 'e'

    def id_type_is_g(row):
        return row['id_type'] == 'g'

    def uid_key_funct(row):
        return "%s" % row["uid"]

    def on_row_activate(treeview, path, view_column):
        fid = str(skel.liststore[path][skel.map['id']])
        id_type = str(skel.liststore[path][skel.map['id_type']])
        if id_type != "f":
            return
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


    def on_row_change(liststore, path, itr ,**kwargs):
        global change_lock
        if change_lock:
            # print "change_lock"
            return
        change_lock = True
        print "on_row_change:",liststore,path,itr
        id_type = liststore[path][skel.map['id_type']]
        fid = liststore[path][skel.map['id']]
        print "id_type:",id_type
        if id_type != "f":
            change_lock = False
            return
        for u in listeners.listeners:
            key = "user.%s.rating" % u['uid']
            rating = liststore[path][skel.map[key]]
            print "rating:", rating
            
            res = get_assoc("""UPDATE user_song_info 
                               SET rating = %s, 
                                   true_score = (((%s * 2 * 10) + (score * 10) + 
                                                   percent_played) / 3) 
                               WHERE uid = %s AND fid = %s RETURNING *""",
                               (rating, rating, u['uid'], fid))
            key = "user.%s.true_score" % u['uid']
            change_lock = True
            liststore[path][skel.map[key]] = res['true_score']
            change_lock = False
        change_lock = False


    skel = TableSkel("""SELECT uh.*, uname,
                               EXTRACT(EPOCH FROM time_played) AS \"time_played_epoch\"
                        FROM user_history uh, users u
                        WHERE u.uid = uh.uid AND u.listening = true AND 
                              id_type IN ('e','f')
                        ORDER BY time_played DESC LIMIT %d""" % history_length)

    skel.add_subquery("file", """SELECT basename AS \"title\" 
                                 FROM files f 
                                 WHERE fid = %s LIMIT 1""", 
                                 ['id'], id_type_is_f, False)

    skel.add_subquery("file", """SELECT CONCAT(netcast_name,' - ',episode_title) AS \"title\" 
                                 FROM netcast_episodes ne, netcasts n 
                                 WHERE eid = %s AND n.nid = ne.nid LIMIT 1""", 
                                 ['id'], id_type_is_e, False)

    skel.add_subquery("user", """SELECT u.uid, uname, rating, score, true_score,
                                        ultp, percent_played
                                 FROM user_song_info usi, users u
                                 WHERE usi.uid = u.uid AND u.listening = true
                                       AND usi.fid = %s
                                 ORDER BY admin DESC, uname""",
                                 ['id'], id_type_is_f, True, uid_key_funct)

    skel.add_subquery("user", """SELECT u.uid, uname, 
                                        -1 AS \"rating\", 
                                        -1 AS \"score\", 
                                        -1 AS \"true_score\",
                                        ' ' AS \"ultp\",
                                        percent_played
                                 FROM users u, netcast_listend_episodes nle
                                 WHERE u.listening = true AND nle.uid = u.uid
                                       AND nle.eid = %s
                                 ORDER BY admin DESC, uname""",
                                 ['id'], id_type_is_e, True, uid_key_funct)

    skel.add_col(int, "uhid")
    skel.add_col(int, "id")
    skel.add_col(str, "id_type", "Type", True)
    skel.add_col(str, "file.title","Title", True)
    skel.add_col(str, "uname", "Played for", True)
    skel.add_col(int, "rating", "Rating", True)
    skel.add_col(str, "score", "Skip score", True)
    skel.add_col(float, "true_score", "True Score", True)
    obj = skel.add_col(str, "time_played_epoch")
    skel.add_col(str, "time_played", "Time Played", True, obj['idx'])

    treeview = gtk.TreeView()
    treeview.show()

    for l in listeners.listeners:
        obj = skel.add_col(int, "user.%s.rating" % (l['uid'],))
        title = "%s's Current Rating" % (l['uname'],)
        obj["title"] = title
        obj["tv_col"] = skel.tv_col(title)
        cell = CellRendererStar(15, obj['idx'])
        cell.set_property('xalign',0.0)
        treeview.connect("motion-notify-event", cell.on_motion_notify)
        treeview.connect("button-press-event", cell.on_button_press)
        skel.add_cell(obj['idx'], cell, attribs={"rating": obj['idx']})
        obj["tv_col"].set_sort_column_id(obj['idx'])
        obj["tv_col"].set_resizable(True)
        obj["tv_col"].set_visible(True)
        skel.add_col(str, "user.%s.score" % (l['uid'],), "%s's Current Skip Score" % (l['uname'],), True)
        skel.add_col(str, "user.%s.true_score" % (l['uid'],), "%s's Current True Score" % (l['uname'],), True)
        skel.add_col(str, "user.%s.percent_played" % (l['uid'],), "%s's Current Percent Played" % (l['uname'],), True)
        skel.add_col(str, "user.%s.ultp" % (l['uid'],), "%s's Current Last Time Played" % (l['uname'],), True)

    treeview.set_model(skel.get_liststore())
    treeview.connect("row-activated", on_row_activate)
    skel.liststore.set_sort_column_id(skel.map['time_played_epoch'], gtk.SORT_DESCENDING)
    skel.add_cols_to_treeview(treeview)
    

    window = gtk.Window();
    scrolled_window = gtk.ScrolledWindow()
    scrolled_window.show()
    scrolled_window.add(treeview)
    window.add(scrolled_window)
    window.set_title("FMP - History")
    window.set_default_size(800,600)
    window.set_position(gtk.WIN_POS_CENTER)
    window.connect("destroy", gtk_main_quit)
    window.show()
    skel.wait()
    skel.liststore.connect("row-changed", on_row_change)
    skel.populate_liststore()
    gobject.timeout_add(5000, skel.refresh_data, ("uhid"))
    gtk.main()
    
