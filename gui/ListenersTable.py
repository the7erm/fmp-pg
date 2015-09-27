

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

from TableSkel import TableSkel
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

def on_toggle(cell_renderer, path, db_col, skel):
    print "on_toggle:"
    print "cell_renderer:", cell_renderer
    print "db_col:", db_col
    print "path:", path
    print "db_col:", db_col
    val = skel.liststore[path][skel.map[db_col]]
    if not val:
        val = True
    else:
        val = False
    skel.liststore[path][skel.map[db_col]] = val
    print "new val:", skel.liststore[path][skel.map[db_col]]
    print "skel.map:", skel.map
    uid = skel.liststore[path][skel.map['uid']]
    print "uid:", uid
    # <CellRendererToggle object at 0x7fab69fec5a0 (GtkCellRendererToggle at 0x28c6d50)>, '0', 2, 'admin'
    sql = """UPDATE users 
             SET {db_col} = %(val)s
             WHERE uid = %(uid)s
             RETURNING *""".format(db_col=db_col)

    spec = {
        'val': bool(val),
        'uid': uid
    }
    print sql % spec
    print get_results_assoc_dict(sql, spec)
   

def gtk_main_quit(*args, **kwargs):
        Gtk.main_quit()

global change_lock
change_lock = False

skel = TableSkel("""SELECT uname, admin, listening, uid
                    FROM users
                    ORDER BY admin, listening, uname""")

skel.add_col(str, "uname", "uname", True)

idx = len(skel.cols)
skel.add_col(bool, "admin", "admin", True, 
             renderer=Gtk.CellRendererToggle,
             attribs={
                'active': 1
             })
cell = skel.cols[idx]['cell']
cell.connect("toggled", on_toggle, 'admin', skel)

idx = len(skel.cols)
skel.add_col(int, "listening", "listening", True, 
             renderer=Gtk.CellRendererToggle,
             attribs={
                'active': 2
             })

cell = skel.cols[idx]['cell']
cell.connect("toggled", on_toggle, 'listening', skel)
skel.add_col(int, "uid", "uid", True)

treeview = Gtk.TreeView()
treeview.show()

treeview.set_model(skel.get_liststore())
# treeview.connect("row-activated", on_row_activate)
skel.liststore.set_sort_column_id(skel.map['listening'], Gtk.SortType.DESCENDING)
skel.add_cols_to_treeview(treeview)
skel.populate_liststore()
GObject.timeout_add(5000, skel.refresh_data, ("uid"))

if __name__ == '__main__':
    window = Gtk.Window();
    scrolled_window = Gtk.ScrolledWindow()
    scrolled_window.show()
    scrolled_window.add(treeview)
    window.add(scrolled_window)
    window.set_title("FMP - Listeners")
    window.set_default_size(800,600)
    window.set_position(Gtk.WindowPosition.CENTER)
    window.connect("destroy", gtk_main_quit)
    window.show()
    Gtk.main()
