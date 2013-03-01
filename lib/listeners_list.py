#!/usr/bin/env python
# lib/users_list.py -- list of users.
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
import sys, os, time
import gobject, pygtk, gtk

def wait():
    if gtk.events_pending():
        while gtk.events_pending():
            print "pending:"
            gtk.main_iteration(False)

class Listeners_Listview(gtk.VBox):
    __gsignals__ = {
        'users-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'close': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    }
    def __init__(self):
        gtk.VBox.__init__(self)
        self.pack_start(gtk.Label("Make sure you add yourself as user, and mark yourself as listening."), False, False)
        self.liststore = gtk.ListStore(int, str, bool, bool) # uid, uname, listening, admin
        
        self.map = {
            'uid':0,
            'uname':1,
            'admin':2,
            'listening':3
        }
        self.populate_liststore()
        
        hbox = gtk.HBox()
        self.usernameEntry = gtk.Entry()
        self.usernameEntry.connect("activate", self.on_user_add)
        hbox.pack_start(self.usernameEntry,False,False)
        
        userAddButton = gtk.Button('Add User')
        userAddButton.connect("clicked", self.on_user_add)
        hbox.pack_start(userAddButton,False,False)
        
        self.pack_start(hbox,False,False)
        self.treeview = gtk.TreeView(self.liststore)
        scrolledWindow = gtk.ScrolledWindow()
        scrolledWindow.add(self.treeview)
        scrolledWindow.set_property("hscrollbar-policy",gtk.POLICY_AUTOMATIC)
        scrolledWindow.set_property("vscrollbar-policy",gtk.POLICY_AUTOMATIC)
        self.pack_start(scrolledWindow)
        
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn('Username')
        col.set_property('resizable', True)
        col.pack_start(cell, True)
        col.set_attributes(cell, text=1)
        col.set_property('clickable',True)
        col.set_sort_column_id(1)
        self.treeview.append_column(col)
        
        cell = gtk.CellRendererToggle()
        cell.connect('toggled',self.on_toggle,'admin')
        col = gtk.TreeViewColumn('Admin')
        col.pack_start(cell, False)
        col.set_attributes(cell, active=2)
        col.set_property('clickable',True)
        col.set_sort_column_id(2)

        self.treeview.append_column(col)
        
        cell = gtk.CellRendererToggle()
        cell.connect('toggled',self.on_toggle,'listening')
        col = gtk.TreeViewColumn('Listening')
        col.pack_start(cell, False)
        col.set_attributes(cell, active=3)
        col.set_sort_column_id(3)
        col.set_property('clickable',True)
        self.treeview.append_column(col)
        # listeners.connect("listeners-changed", self.on_listeners_changed)

        self.close_button = gtk.Button("Close")
        self.close_button.set_image(gtk.image_new_from_stock(gtk.STOCK_CLOSE, gtk.ICON_SIZE_BUTTON))
        self.close_button.connect("clicked", self.on_close)

        self.bottom_buttons = gtk.HBox()
        self.bottom_buttons.pack_start(gtk.Label(" "), True, False)
        self.bottom_buttons.pack_start(self.close_button, False, False)
        self.status_bar = gtk.Statusbar()
        self.pack_start(self.bottom_buttons, False, False)
        self.pack_start(self.status_bar, False, True)

    def on_close(self, *args):
        self.emit('close')


    def populate_liststore(self):
        self.liststore.clear()
        users = []
        
        users = get_results_assoc("""SELECT uid, uname, admin, listening 
                                     FROM users 
                                     ORDER BY admin DESC, listening DESC, uname""")
        
        for u in users:
            data = [
                u['uid'], 
                u['uname'],
                bool(u['admin']),
                bool(u['listening'])
            ]
            # print data
            self.liststore.append(data)

    def on_listeners_changed(self,*args):
        for i, u in enumerate(self.liststore):
            gtk_wait()
            found = False
            for uid in listeners.uids:
                if u[self.map['uid']] == uid:
                    self.liststore[i][self.map['listening']] = 1
                    found = True
                    break
            if not found:
                self.liststore[i][self.map['listening']] = 0
                    
        
    def on_user_add(self,*args,**kwargs):
        uname = self.usernameEntry.get_text()
        print "uname:",uname
        if uname.strip() == '':
            return
        present = get_assoc("SELECT uid FROM users WHERE uname = %s",(uname,))
        if present:
            print "%s exists" % (uname,)
            self.populate_liststore()
            return
        new_user = get_assoc("""INSERT INTO users (uname, listening) 
                                VALUES(%s, true) RETURNING *""",(uname,))
        
        data = [
            new_user['uid'], 
            new_user['uname'],
            bool(new_user['admin']),
            bool(new_user['listening'])
        ]
        print data
        self.liststore.append(data)
        self.usernameEntry.set_text("")
        
    def on_toggle(self,cell, row, key):
        selection = self.treeview.get_selection()
        selection.select_path(row)
        wait()
        print "key:",key
        uid = self.liststore[row][0]
        uname = self.liststore[row][1]
        print "UID:",uid
        if cell.get_active():
            state = False
            stateInt = 0
        else:
            state = True
            stateInt = 1

        if key == 'admin':
            col = 2
        elif key == 'listening':
            col = 3

        self.liststore[row][col] = state

        # (<gtk.CellRendererToggle object at 0xa3eae64 (GtkCellRendererToggle at 0xa431928)>, '0')
        print 'on_toggle:',state,row,key

        stateBool = bool(stateInt)
        # cell.set_active(state)
        
        query("UPDATE users SET "+key+" = %s WHERE uid = %s",(stateBool,uid))
        if key == 'admin':
            if stateInt == 1:
                self.status_bar.push(0, "%s is now an admin" % (uname,))
            else:
                self.status_bar.push(0, "%s is no longer an admin" % (uname,))
        elif key == 'listening':
            if stateInt == 1:
                self.status_bar.push(0, "%s is now listening" % (uname,))
                zero = get_results_assoc("SELECT p.fid FROM preload p, user_song_info u WHERE u.fid = p.fid AND u.rating = 0 AND u.uid = %s",(uid,))
                for f in zero:
                    query("DELETE FROM preload WHERE fid = %s",(f['fid'],))
            else:
                # print "DELETE FROM preload WHERE uid = %s" % (uid,)
                query("DELETE FROM preload WHERE uid = %s",(uid,))
                self.status_bar.push(0, "%s is no longer listening" % (uname,))
                
        

        # listeners.reloadListeners()
        # gobject.idle_add(listeners.emit, 'listeners-changed')
        gobject.idle_add(self.emit, 'users-changed')
        
        # gobject.timeout_add(10000, listeners.emit, ('listeners-changed',))


    
        
        
if __name__ == '__main__':
    w = gtk.Window()
    w.set_title("FMP - Lister Management")
    w.set_default_size(480,540)
    w.set_position(gtk.WIN_POS_CENTER)
    l = Listeners_Listview()
    w.add(l)
    w.show_all()
    w.connect("destroy", gtk.main_quit)
    l.connect("close", gtk.main_quit)
    gtk.main()


