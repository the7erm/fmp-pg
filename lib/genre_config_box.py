#!/usr/bin/env python
# lib/genre_config_box.py -- enable/disable genres
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
from genres_v1 import genres_v1
import pygtk, gtk, gobject

class  Genre_Config_Box(gtk.VBox):
	def __init__(self):
		gtk.VBox.__init__(self)
		self.liststore = gtk.ListStore(int,str,bool,bool) # gid, genre, enabled
		self.treeview = gtk.TreeView(self.liststore)
		scrollWindow = gtk.ScrolledWindow()
		scrollWindow.set_property("hscrollbar-policy",gtk.POLICY_AUTOMATIC)
		scrollWindow.set_property("vscrollbar-policy",gtk.POLICY_AUTOMATIC)
		self.pack_start(scrollWindow)
		scrollWindow.add(self.treeview)
		self.genres = []

		
		self.genres = get_results_assoc("SELECT gid, genre, enabled, seq_genre FROM genres g ORDER BY genre")

			
		cell = gtk.CellRendererText()
		col = gtk.TreeViewColumn('Genre')
		cell.set_property('editable',False)
		col.pack_start(cell)
		col.add_attribute(cell, 'text', 1)
		col.set_sort_column_id(1)
		self.treeview.append_column(col)
		
		cell = gtk.CellRendererToggle()
		col = gtk.TreeViewColumn('Enabled')
		cell.set_property('activatable',True)
		col.pack_start(cell, False)
		col.add_attribute(cell, 'active', 2)
		cell.connect("toggled",self.on_toggle,'enabled')
		col.set_sort_column_id(2)
		self.treeview.append_column(col)
		
		cell = gtk.CellRendererToggle()
		col = gtk.TreeViewColumn('Sequential')
		cell.set_property('activatable',True)
		col.pack_start(cell, False)
		col.add_attribute(cell, 'active', 3)
		cell.connect("toggled",self.on_toggle,'seq_genre')
		col.set_sort_column_id(3)
		self.treeview.append_column(col)
		self.status_bar = gtk.Statusbar()
		self.pack_start(self.status_bar, False, True)
		gobject.idle_add(self.load_genres)
		
	def on_toggle(self, cell, row, db_column):
		# print db_column
		colNum = 2
		if db_column == 'enabled':
			colNum = 2
		elif  db_column == 'seq_genre':
			colNum = 3
		
		if self.liststore[row][colNum]:
			self.liststore[row][colNum] = False
		else:
			self.liststore[row][colNum] = True
			
		gid = self.liststore[row][0]
		active = self.liststore[row][colNum]
		
		query("UPDATE genres SET "+db_column+" = %s WHERE gid = %s",(active, gid))
		query("DELETE FROM preload p WHERE fid NOT IN (SELECT p.fid FROM preload p, file_genres fg, genres g WHERE p.fid = fg.fid AND g.gid = fg.gid AND g.enabled = true)")

		genre = self.liststore[row][1]
		
		if db_column == "enabled":
			if active:
				self.status_bar.push(0, "Enabled songs with the genre %s" % genre)
			else:
				self.status_bar.push(0, "Disabled songs with the genre %s" % genre)
		else:
			if active:
				self.status_bar.push(0, "All songs in the genre %s will now be played sequentially." % genre)
			else:
				self.status_bar.push(0, "All songs in the genre %s will now be played randomly." % genre)
	
	def load_genres(self):
		
		insertedNew = False
		null_genres = get_results_assoc("SELECT genre, g.gid FROM genres g LEFT JOIN file_genres f ON f.gid = g.gid WHERE f.gid IS NULL")
		for g in null_genres:
			if not g['genre'] in genres_v1:
				query("DELETE FROM genres WHERE gid = %s", (g['gid'],))

		for g in genres_v1:
			found = False
			for g2 in self.genres:
				if g.lower() == g2['genre'].lower():
					found = True
					break
			if not found:
				print "Didn't find genre:%s" % g
				present = get_assoc("SELECT gid, genre, enabled, seq_genre FROM genres g WHERE genre = %s", (g,))
				if not present:
					query("INSERT INTO genres (genre, enabled, seq_genre) VALUES(%s, %s, %s)", (g, True, False))
					insertedNew = True
				
		if insertedNew:
			self.genres = get_results_assoc("SELECT gid, genre, enabled, seq_genre FROM genres g ORDER BY genre")
			
		for g in self.genres:
			self.liststore.append([g['gid'], g['genre'], bool(g['enabled']), bool(g['seq_genre'])])
			
if __name__ == '__main__':
	genre_config_box = Genre_Config_Box()
	w = gtk.Window()
	w.set_title("FMP - Genres Management")
	w.set_position(gtk.WIN_POS_CENTER)
	w.set_default_size(480,540)
	w.add(genre_config_box)
	w.show_all()
	gtk.gdk.threads_init()
	w.connect("destroy", gtk.main_quit)
	gtk.main()

