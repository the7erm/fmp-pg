

"""
fmp=# \d user_song_info;
                                       Table "public.user_song_info"
     Column     |           Type           |                           Modifiers                           
----------------+--------------------------+---------------------------------------------------------------
 usid           | integer                  | not null default nextval('user_song_info_usid_seq'::regclass)
 uid            | integer                  | not null
 fid            | integer                  | not null
 rating         | integer                  | default 6
 score          | integer                  | default 5
 percent_played | double precision         | default 50.00
 ultp           | timestamp with time zone | 
 true_score     | double precision         | default 50.00
"""


"""
fmp=# \d user_history
                                       Table "public.user_history"
     Column     |           Type           |                          Modifiers                          
----------------+--------------------------+-------------------------------------------------------------
 uhid           | integer                  | not null default nextval('user_history_uhid_seq'::regclass)
 uid            | integer                  | not null
 percent_played | integer                  | 
 time_played    | timestamp with time zone | 
 date_played    | date                     | 
 true_score     | double precision         | not null default 0
 score          | integer                  | not null default 0
 rating         | integer                  | not null default 0
 reason         | text                     | 
 fid            | integer                  | 
 eid            | integer                  | 
Indexes:
    "user_history_pkey" PRIMARY KEY, btree (uhid)
    "uid_eid_fid_date_played" UNIQUE CONSTRAINT, btree (uid, eid, fid, date_played)
    "time_played_idx" btree (time_played)
"""
# eid, uid, fid rating score, true_socre, usid 
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

import gi
import os
import sys
from gi.repository import GObject, Gtk, Gdk
GObject.threads_init()

from fobjs.misc import _listeners
from datetime import date, datetime, timedelta
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)
from subprocess import Popen
from pprint import pprint
# from star_cell import CellRendererStar

listeners = _listeners(None)

class TableSkel:
    def __init__(self, query=""):
        self.editing = False
        self.cols = []
        self.map = {}
        self.query = query
        self.subqueries = []
        self.liststore = None
        self.listeners_len = len(listeners)

    def add_subquery(self, prefix, query, args=[], when=None, 
                     many=False, key_funct=None):
        self.subqueries.append({
            "prefix": prefix,
            "query": query,
            "when": when,
            "many": many,
            "key_funct":key_funct
        })

    def add_col(self, typ, table_col, title="", text_cell=False, 
                sort_by_col=None, renderer=Gtk.CellRendererText,
                renderer_args=[], renderer_kwargs={},
                attribs=None):
        if attribs is None:
            attribs = {}
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

        if not attribs.get('text') and not attribs.get("text-column"):
            attribs["text"] = obj['idx']

        if title and text_cell:
            obj['tv_col'].set_sort_column_id(obj['idx'])
            self.add_cell(
                obj['idx'], renderer(*renderer_args, **renderer_kwargs), 
                attribs)

        if sort_by_col is not None:
            obj['tv_col'].set_sort_column_id(sort_by_col)

        return obj

    def tv_col(self, title):
        tvc = Gtk.TreeViewColumn()
        tvc.set_visible(True)
        tvc.set_sort_indicator(True)
        tvc.set_sizing(Gtk.TreeViewColumnSizing.AUTOSIZE)
        tvc.set_title(title)
        return tvc

    def perform_query(self):
        return self.fix_rows_date_types(get_results_assoc_dict(self.query))

    def fix_rows_date_types(self, res):
        new_res = []
        for r in res:
            row = self.fix_cols_date_types(r)
            new_res.append(row)
        return new_res

    def fix_cols_date_types(self, r):
        row = {}
        for k, v in r.iteritems():
            if isinstance(v, datetime):
                v = v.strftime("%c")

            if isinstance(v, date):
                v = v.strftime("%Y-%m-%d")

            if isinstance(v, timedelta):
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
        for c in self.cols:
            try:
                key = c['table_col']
            except KeyError:
                continue
            try:
                cast = c['typ'](r[key])
            except TypeError, e:
                e = "%s" % e
                if 'int()' in e and 'NoneType' in e:
                    cast = 0
                if 'float()' in e and 'NoneType' in e:
                    cast = 0
            except KeyError:
                continue
            row.append(cast)
        return row

    def perform_subquery(self, row, subquery):
        when = subquery.get('when')
        if when and not when(row):
            return

        many = subquery.get("many")
        key_funct = subquery.get('key_funct')
        sql = subquery.get("query")
        sql_args = dict(row)
        prefix = subquery.get('prefix')
        if many:
            res = self.fix_rows_date_types(
                get_results_assoc_dict(sql, sql_args))
            for i, res_row in enumerate(res):
                idx = "%s" % i
                if key_funct:
                    idx = key_funct(res_row)
                for k, v in res_row.iteritems():
                    key = "%s.%s.%s" % (prefix, idx, k)
                    # print "key:",key
                    row[key] = v
        else:
            res = self.fix_cols_date_types(get_assoc_dict(sql, sql_args))
            for k, v in res.iteritems():
                if key_funct:
                    k = key_funct(res)
                key = "%s.%s" % (prefix, k)
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
        # cell.connect('editing-started', self.on_editing_started)
        # cell.connect('editing-canceled', self.on_editing_done)
        # cell.connect('edited', self.on_editing_done)
        self.cols[idx]['cell'] = cell
        self.cols[idx]['tv_col'].pack_start(self.cols[idx]['cell'], True)
        self.cols[idx]['tv_col'].set_attributes(self.cols[idx]['cell'], **attribs)

    def on_editing_started(self, *args, **kwargs):
        self.editing = True

    def on_editing_done(self, *args, **kwargs):
        self.editing = False

    def get_liststore(self):
        if not self.liststore:
            self.liststore = Gtk.ListStore(*self.get_liststore_cols())
        return self.liststore

    def populate_liststore(self):
        rows = self.get_rows()

    def wait(self):
        Gdk.threads_leave()
        Gdk.threads_enter()
        while Gtk.events_pending():
            Gtk.main_iteration()
        Gdk.threads_leave()

    def refresh_data(self, based_on=""):
        Gdk.threads_leave()
        if self.editing:
            print "EDITING"
            return True
        if not based_on or not self.liststore or self.editing:
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
                        Gdk.threads_enter()
                        liststore_row[i2] = fresh_row[i2]
                        Gdk.threads_leave()
                        change_lock = False
                break
                
            if not found:
                change_lock = True
                Gdk.threads_enter()
                self.liststore.append(fresh_row)
                Gdk.threads_leave()
                change_lock = False

        return True

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
    
if __name__ == '__main__':
    def gtk_main_quit(*args, **kwargs):
        Gtk.main_quit()

    def on_rating_change(adj, cell, obj):
        print "on_rating_change:", adj, cell, obj
        rating = adj.get_value()

    def on_rating_edited(*args, **kwargs):
        print "on_rating_edited:", args, kwargs

    history_length = 50
    global change_lock
    change_lock = False

    def id_type_is_f(row):
        return row.get('fid', False)

    def id_type_is_e(row):
        return row.get('eid', False)

    def id_type_is_g(row):
        return False

    def uid_key_funct(row):
        return "%s" % row["uid"]

    def get_path_key(path, key):
        idx = skel.map.get(key)
        val = skel.liststore[path][idx]
        return val


    def on_row_activate(treeview, path, view_column):
        fid = str(skel.liststore[path][skel.map['fid']])
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


    def rate(fid, uid, rating, uhid):
        sql_args = {
            'fid': fid,
            'uid': uid,
            'rating': rating,
            'uhid': uhid
        }
        sql = """UPDATE user_history
                 SET rating = %(rating)s,
                     true_score = (
                        ((%(rating)s * 2 * 10) +
                         (score * 10)) / 2
                     )
                 WHERE uhid = %(uhid)s
                 RETURNING *"""

        get_assoc_dict(sql, sql_args)
        sql = """UPDATE user_song_info
                 SET rating = %(rating)s,
                     true_score = (
                        ((%(rating)s * 2 * 10) +
                         (score * 10)) / 2
                     )
                 WHERE uid = %(uid)s AND fid = %(fid)s
                 RETURNING *"""
        return get_assoc_dict(sql, sql_args)

    def on_row_change(liststore, path, itr ,**kwargs):
        return
        global change_lock
        if change_lock:
            # print "change_lock"
            return
        change_lock = True
        print "on_row_change:",liststore,path,itr
        fid = liststore[path][skel.map['fid']]
        if not fid:
            change_lock = False
            return
       
        for u in listeners:
            key = "user.%s.rating" % u['uid']
            rating = liststore[path][skel.map[key]]
            print "rating:", rating
            res = get_assoc_dict("""UPDATE user_song_info 
                               SET rating = %s, 
                                   true_score = (
                                        ((%s * 2 * 10) +
                                         (score * 10)) / 2
                                   ) 
                               WHERE uid = %s AND fid = %s RETURNING *""",
                               (rating, rating, u['uid'], fid))
            key = "user.%s.true_score" % u['uid']
            change_lock = True
            liststore[path][skel.map[key]] = str(res['true_score'])
            change_lock = False
        change_lock = False


    skel = TableSkel("""SELECT uh.*, uname, uh.uid AS user_history_uid,
                               EXTRACT(EPOCH FROM time_played) AS \"time_played_epoch\"
                        FROM user_history uh, users u
                        WHERE u.uid = uh.uid AND u.listening = true
                        ORDER BY time_played DESC 
                        LIMIT %d""" % history_length)
    # add_subquery(self, prefix, query, args=[], when=None, 
    #                many=False, key_funct=None)
    sql = """SELECT basename AS "title"
             FROM files f, file_locations l
             WHERE f.fid = %(fid)s AND l.fid = f.fid 
             LIMIT 1"""
    skel.add_subquery(prefix="file", query=sql)

    sql = """SELECT CONCAT(
                    netcast_name,' - ',episode_title
                ) AS \"title\" 
             FROM netcast_episodes ne, netcasts n 
             WHERE eid = %(eid)s AND n.nid = ne.nid 
             LIMIT 1"""
    skel.add_subquery(prefix="file", query=sql)

    sql = """SELECT u.uid, uname, rating, score,
                    true_score, ultp, percent_played
             FROM user_song_info usi, users u
             WHERE usi.uid = u.uid AND u.listening = true
                   AND usi.fid = %(fid)s
             ORDER BY admin DESC, uname"""

    skel.add_subquery(prefix="user", 
                      query=sql,
                      many=True,
                      key_funct=uid_key_funct)

    sql = """SELECT u.uid, uname, 
                    -1 AS \"rating\", 
                    -1 AS \"score\", 
                    -1 AS \"true_score\",
                    ' ' AS \"ultp\",
                    percent_played
             FROM users u, netcast_listend_episodes nle
             WHERE u.listening = true AND nle.uid = u.uid
                   AND nle.eid = %(eid)s
             ORDER BY admin DESC, uname"""

    skel.add_subquery(prefix="user", 
                      query=sql,
                      many=True,
                      key_funct=uid_key_funct)

    skel.add_col(int, "uhid")
    skel.add_col(int, "user_history_uid")
    skel.add_col(int, "fid")
    skel.add_col(int, "eid")
    skel.add_col(str, "file.title","Title", True)
    skel.add_col(str, "uname", "Played for", True)
    """
    renderer_combo = Gtk.CellRendererCombo()
        renderer_combo.set_property("editable", True)
        renderer_combo.set_property("model", liststore_manufacturers)
        renderer_combo.set_property("text-column", 0)
        renderer_combo.set_property("has-entry", False)
        renderer_combo.connect("edited", self.on_combo_changed)"""
    ratings_liststore = Gtk.ListStore(str)
    for rating in range(1,6):
        ratings_liststore.append([str(rating)])
    def on_combo_changed(widget, path, text, idx):
        print "text:", text

        skel.liststore[path][idx] = text
        col = skel.cols[idx]
        if col['table_col'] == 'rating':
            print "map:", skel.map
            uhid = get_path_key(path, 'uhid')
            uid = get_path_key(path, 'user_history_uid')
            fid = get_path_key(path, 'fid')
            res = rate(fid=fid, uid=uid, rating=text, uhid=uhid)
            pprint(res)
        print "col:", skel.cols[idx]

    idx = len(skel.cols)
    obj = skel.add_col(str, "rating", "Rating", True, 
                       renderer=Gtk.CellRendererCombo)
    cell = skel.cols[idx]['cell']
    cell.set_property('editable', True)
    cell.set_property('model', ratings_liststore)
    cell.set_property('has-entry', False)
    cell.set_property('text-column', 0)
    cell.connect("edited", on_combo_changed, idx)
    

    pprint(dir(skel.cols[idx]['cell']))

    skel.add_col(int, "score", "Skip score", True)
    skel.add_col(float, "true_score", "True Score", True)
    obj = skel.add_col(float, "time_played_epoch")
    skel.add_col(str, "time_played", "Time Played", True, obj['idx'])

    treeview = Gtk.TreeView()
    treeview.show()

    for l in listeners:
        idx = len(skel.cols)
        obj = skel.add_col(
                str, 
                "user.%s.rating" % (l['uid'],), 
                "%s's Rating" % (l['uname'],), 
                True, 
                renderer=Gtk.CellRendererSpin,
                renderer_args=[],
                renderer_kwargs={})
        skel.cols[idx]['cell'].editable = True;
        skel.add_col(str, "user.%s.score" % (l['uid'],), "%s's Current Skip Score" % (l['uname'],), True)
        skel.add_col(str, "user.%s.true_score" % (l['uid'],), "%s's Current True Score" % (l['uname'],), True)
        skel.add_col(str, "user.%s.percent_played" % (l['uid'],), "%s's Current Percent Played" % (l['uname'],), True)
        skel.add_col(str, "user.%s.ultp" % (l['uid'],), "%s's Current Last Time Played" % (l['uname'],), True)

    treeview.set_model(skel.get_liststore())
    # treeview.connect("row-activated", on_row_activate)
    skel.liststore.set_sort_column_id(skel.map['time_played_epoch'], Gtk.SortType.DESCENDING)
    skel.add_cols_to_treeview(treeview)

    window = Gtk.Window();
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.show()
    scrolled_window.add(treeview)
    window.add(scrolled_window)
    window.set_title("FMP - History")
    window.set_default_size(800,600)
    window.set_position(Gtk.WindowPosition.CENTER)
    window.connect("destroy", gtk_main_quit)
    window.show()
    skel.liststore.connect("row-changed", on_row_change)
    skel.populate_liststore()
    GObject.timeout_add(5000, skel.refresh_data, ("uhid"))
    Gtk.main()
