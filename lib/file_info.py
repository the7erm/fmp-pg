#!/usr/bin/env python2
# lib/file_info.py -- Display dialog about file
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
import gtk, sys, os, re, gobject
from crumbs import Crumbs
from user_file_info_tree import User_File_Info_Tree
from history import History_Tree
from file_tags import Tag_Table
import mutagen
import fobj
import subprocess

class LocationTreeview:

    # close the window and quit
    def delete_event(self, widget, event, data=None):
        gtk.main_quit()
        return False

    def __init__(self, locations):
        # create a TreeStore with one string column to use as the model
        self.liststore = gtk.ListStore(str, str, str, str, int, str, str)
        
        for l in locations:
            print "loc:", l.filename
            exists = "%s" % l.exists
            is_readable = "%s" % l.is_readable
            self.liststore.append([exists, is_readable, l.dirname, l.basename, l.size,
                                   "%s" % l.atime, "%s" % l.mtime])

        # create the TreeView using treestore
        self.treeview = gtk.TreeView(self.liststore)

        self.add_tv_column('exists', 0)
        self.add_tv_column('readable', 1)
        self.add_tv_column('dirname', 2)
        self.add_tv_column('basename', 3)
        self.add_tv_column('size', 4)
        self.add_tv_column('atime', 5)
        self.add_tv_column('mtime', 6)

        # make it searchable
        self.treeview.set_search_column(2)

        # Allow drag and drop reordering of rows
        self.treeview.set_reorderable(True)


    def add_tv_column(self, title, col_num, sort_col=None):
        # create the TreeViewColumn to display the data
        col = gtk.TreeViewColumn(title)

        # add tvcolumn to treeview
        self.treeview.append_column(col)

        # create a CellRendererText to render the data
        cell = gtk.CellRendererText()

        # add the cell to the tvcolumn and allow it to expand
        col.pack_start(cell, True)

        # set the cell "text" attribute to column 0 - retrieve text
        # from that column in treestore
        col.add_attribute(cell, 'text', col_num)

        if sort_col is None:
            sort_col = col_num

        # Allow sorting on the column
        col.set_sort_column_id(sort_col)

class File_Info_Tab(gtk.ScrolledWindow):
    def __init__(self, fid=None, filename=None):
        gtk.ScrolledWindow.__init__(self)
        self.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.filename = None
        self.dirname = None
        self.basename = None
        self.fid = None
        self.vbox = gtk.VBox()
        self.add_with_viewport(self.vbox)
        self.artists = []
        self.genres = []
   
        if filename:
            self.filename = os.path.realpath(filename)
            self.dirname = os.path.dirname(self.filename)
            self.basename = os.path.basename(self.filename)

        if fid:
            fid = int(fid)
            self.fid = fid

        self.fobj = fobj.get_fobj(fid=self.fid, 
                                  dirname=self.dirname, 
                                  basename=self.basename,
                                  filename=self.filename)

        self.file_info = self.fobj.db_info

        if self.file_info:
            print "FILE INFO:",self.file_info
            self.dirname = self.fobj.dirname
            self.basename = self.fobj.basename
            self.fid = self.file_info['fid']
            self.filename = self.fobj.filename

        for loc in self.fobj.locations:
            print "LOCATION:", loc.filename

        self.add_crap_to_the_tab()
        # self.vbox.pack_start(gtk.Label(""),True,True)

    def add_crap_to_the_tab(self):
        self.add_dir_and_basename()
        self.add_artist_tags()
        self.add_genre_tags()
        self.add_album_tags()
        self.notebook = gtk.Notebook()
        self.notebook.set_scrollable(True)
        self.notebook.set_current_page(0)
        self.vbox.pack_start(self.notebook,True,True)

        self.ratings_and_history_vbox = gtk.VBox()
        self.ratings_and_history_vbox.show()
        self.add_tab(self.ratings_and_history_vbox, "Ratings &amp; History")
        self.add_locations()
        
        self.add_ratings_and_scores()
        self.add_history()
        self.add_tags()
        

    def add_tab(self, widget, text):
        widget.show()

        l = gtk.Label()
        l.set_markup("<b>%s</b>" % text)
        l.show()

        sw = gtk.ScrolledWindow()
        sw.show()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add_with_viewport(widget)
        self.notebook.append_page(sw, l)

    def add_tags(self):
        # tags = File_Tags_Tab(file_info=self.file_info)
        # print "filename:",self.filename
        self.fobj.get_tags(easy=True, hard=True)
        self.tags_easy = {}
        self.tags_hard = {}
        if self.fobj.tags_easy:
            self.tags_easy = self.fobj.tags_easy
        if self.fobj.tags_hard:
            self.tags_hard = self.fobj.tags_hard

        if self.tags_easy:
            table1 = Tag_Table(self.tags_easy)
            self.add_tab(table1, "Simple Tags")
        if self.tags_hard:
            table2 = Tag_Table(self.tags_hard)
            self.add_tab(table2, "Complex Tags")


    def add_dir_and_basename(self):
        dir_hbox = gtk.HBox()
        dir_hbox.set_border_width(5)
        self.file_label = gtk.Label()
        self.file_label.show()
        self.file_label.set_markup("<b>%s/\n%s</b>" % (self.dirname, self.basename))
        self.file_label.set_property("xalign",0.0)
        self.file_label.set_property("yalign",0.0)
        dir_hbox.pack_start(self.file_label)
        dir_hbox.show()
        self.vbox.pack_start(dir_hbox, False, False)

    def add_locations(self):
        self.add_tab(LocationTreeview(self.fobj.locations).treeview, 'Locations')

    def add_artist_tags(self):
        artist_hbox = self.create_section("Artists: ")

        self.artist_crumbs = Crumbs()
        # crumbs.set_property("xalign",0.0)
        # crumbs.set_property("yalign",0.0)
        artist_hbox.pack_start(self.artist_crumbs, True, True)

        self.artists = self.fobj.artists
        for a in self.artists:
            crumb = self.create_crumb('aid', a['aid'], a['artist'])
            self.artist_crumbs.add_crumb(crumb)

        add_artist = gtk.Button()
        add_image = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        add_artist.set_image(add_image)
        add_artist.connect("pressed", self.on_add_artist)

        self.artist_crumbs.add_crumb(add_artist)
        self.vbox.pack_start(artist_hbox, False, False)


    def add_genre_tags(self):
        genre_hbox = self.create_section("Genres: ")
        self.gernes = self.fobj.genres

        self.genre_crumbs = Crumbs()
        # crumbs.set_property("xalign",0.0)
        # crumbs.set_property("yalign",0.0)
        genre_hbox.pack_start(self.genre_crumbs, True, True)

        for g in self.gernes:
            crumb = self.create_crumb('gid', g['gid'], g['genre'])
            self.genre_crumbs.add_crumb(crumb)

        add_genre = gtk.Button()
        add_image = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        add_genre.set_image(add_image)
        add_genre.connect("pressed", self.on_add_genre)

        self.genre_crumbs.add_crumb(add_genre)
        self.vbox.pack_start(genre_hbox, False, False)

    def add_album_tags(self):
        album_hbox = self.create_section("Albums: ")
        self.albums = self.fobj.albums

        self.album_crumbs = Crumbs()
        # crumbs.set_property("xalign",0.0)
        # crumbs.set_property("yalign",0.0)
        album_hbox.pack_start(self.album_crumbs, True, True)

        for al in self.albums:
            crumb = self.create_crumb('alid', al['alid'], al['album_name'])
            self.album_crumbs.add_crumb(crumb)

        add_album = gtk.Button()
        add_image = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_MENU)
        add_album.set_image(add_image)
        add_album.connect("pressed", self.on_add_album)

        self.album_crumbs.add_crumb(add_album)
        self.vbox.pack_start(album_hbox, False, False)

    def add_ratings_and_scores(self):
        rating_hbox = self.create_section("Ratings, and Scores:")
        self.ratings_and_history_vbox.pack_start(rating_hbox, False, False)
        uf = User_File_Info_Tree(fid=self.fid)
        uf.show()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(uf)
        sw.show()
        # uf.grab_focus()
        self.ratings_and_history_vbox.pack_start(sw, True, True)

    def add_history(self):
        history_hbox = self.create_section("History:")
        self.ratings_and_history_vbox.pack_start(history_hbox,False,False)
        t = History_Tree(fid=self.fid)
        t.show()
        sw = gtk.ScrolledWindow()
        sw.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        sw.add(t)
        sw.show()
        # history_hbox.pack_start(sw)
        
        self.ratings_and_history_vbox.pack_start(sw,True, True)

    
    def create_crumb(self, typ, _id, text):
        border = gtk.EventBox()
        border.show()
        border.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))
        border.set_border_width(1) # padding so there is space between our buttons.

        body = gtk.EventBox()
        body.show()
        body.set_border_width(1) # padding so black shows.

        # Style our buttons.
        body.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
        body.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("black"))

        hbox = gtk.HBox() # For putting out buttons into.
        hbox.show()

        ## Tag button
        btn = gtk.Button()
        btn.set_property("relief",gtk.RELIEF_NONE) # Remove default borders
        btn.set_label("%s" % (text,))
        btn.connect("activate", self.on_crumb_info, border, typ, _id, text )
        btn.connect("pressed", self.on_crumb_info, border, typ, _id, text )
        btn.show()
        hbox.pack_start(btn,True,True)

        ## Remove button
        close_image = gtk.image_new_from_stock(gtk.STOCK_REMOVE, gtk.ICON_SIZE_MENU)
        btn = gtk.Button()
        btn.set_property("relief", gtk.RELIEF_NONE) # Remove default borders
        btn.set_image(close_image)
        btn.set_image_position(gtk.POS_RIGHT)
        btn.connect("activate", self.on_crumb_remove, border, typ, _id, text)
        btn.connect("pressed", self.on_crumb_remove, border, typ, _id, text)
        btn.show()
        hbox.pack_end(btn,False,False)

        border.add(body)
        body.add(hbox)
        return border

    def create_section(self, text):
        hbox = gtk.HBox()
        hbox.set_border_width(5)
        label = gtk.Label()
        label.set_markup("<b>%s</b>" % text)
        label.set_property("xalign",0.0)
        # label.set_property("yalign",0.5)
        hbox.pack_start(label, False,False)
        return hbox

    def on_crumb_remove(self, btn, btn_grp, typ, _id, text):
        btn_grp.destroy()
        print "on_crumb_remove:", btn_grp, typ, _id, text
        if typ == 'aid':
            self.fobj.remove_artist(aid=_id)
        if typ == 'gid':
            self.fobj.remove_genre(gid=_id)
        if typ == 'alid':
            self.fobj.remove_album(alid=_id)


    def on_crumb_info(self, btn, btn_grp, typ, _id, text):
        print "on_crumb_info:", text
        subprocess.Popen(['xdg-open', 
                          "http://localhost:5050/search/?q=%s" % urllib.quote(text)])

    def on_add_artist(self, btn):
        resp, text = self.add_dialog("Add Artist:", self.populate_artist_store)
        print "text:",text
        print "resp:",resp
        if resp == gtk.RESPONSE_OK and text:
            print "Saving:",text
            # add_album(self, album_name, aid)
            artist = self.fobj.add_artist(text)
            if artist:
                self.artists.append(artist)
                crumb = self.create_crumb('aid', artist['aid'], artist['artist'])
                self.artist_crumbs.insert_crumb(crumb, -2)


    def on_add_genre(self, btn):
        resp, text = self.add_dialog("Add Genre:", self.populate_genre_store)
        print "text:",text
        print "resp:",resp
        if resp == gtk.RESPONSE_OK and text:
            print "Saving:",text
            genre = self.fobj.add_genre(text)
            if genre:
                self.genres.append(genre)
                crumb = self.create_crumb('gid', genre['gid'], genre['genre'])
                self.genre_crumbs.insert_crumb(crumb, -2)

    def add_dialog(self, label_text, populate_store_command):
        dialog = gtk.Dialog()
        entry = gtk.Entry()
        
        completion = gtk.EntryCompletion()
        entry.set_completion(completion)
        store = gtk.ListStore(str)
        completion.set_model(store)
        completion.set_text_column(0)
        entry.show()
        hbox = gtk.HBox()
        label = gtk.Label(label_text)
        label.show()
        hbox.pack_start(label, False, False)
        hbox.pack_start(entry, True, True)
        dialog.vbox.pack_start(hbox)
        dialog.show_all()
        dialog.add_action_widget(entry, gtk.RESPONSE_OK)
        dialog.add_button(gtk.STOCK_ADD, gtk.RESPONSE_OK)
        # d.connect("destroy", d.destroy)
        gobject.idle_add(populate_store_command, store)
        resp = dialog.run()
        dialog.hide()
        text = entry.get_text()
        text = text.strip()
        dialog.destroy()
        return resp, text

    def on_add_album(self, *args, **kwargs):
        print "on_add_album:", args, kwargs
        resp, text = self.add_dialog("Add Album:", self.populate_album_store)
        print "text:",text
        print "resp:",resp
        if resp == gtk.RESPONSE_OK and text:
            print "Saving:",text
            album = self.fobj.add_album(text)
            if album:
                self.albums.append(album)
                crumb = self.create_crumb('alid', album['alid'], album['album_name'])
                self.album_crumbs.insert_crumb(crumb, -2)

    def populate_artist_store(self,store):
        artists = get_results_assoc("""SELECT artist 
                                       FROM artists 
                                       ORDER BY artist""")
        for a in artists:
            store.append([a['artist']])

    def populate_genre_store(self,store):
        genres = get_results_assoc("""SELECT genre 
                                      FROM genres 
                                      ORDER BY genre""")
        for g in genres:
            store.append([g['genre']])

    def populate_album_store(self, store):
        albums = get_results_assoc("""SELECT album_name
                                      FROM albums
                                      ORDER BY album_name""")
        for al in albums:
            store.append([al['album_name']])


if __name__ == "__main__":

    tab = None

    for arg in sys.argv[1:]:
        result = re.match("^[0-9]+$", arg)
        if result:
            # It's a number so treat it as an fid.
            fid = int(arg)
            tab = File_Info_Tab(fid=fid)
            break;
            
        if os.path.isfile(arg):
            filename = os.path.realpath(arg)
            tab = File_Info_Tab(filename=filename)
            break

        if arg == "--latest":
            file_info = get_assoc("""SELECT * 
                                     FROM user_song_info 
                                     WHERE ultp IS NOT NULL 
                                     ORDER BY ultp DESC LIMIT 1""")
            if not file_info:
                print "couldn't find recent file."
                sys.exit()
            tab = File_Info_Tab(fid=file_info['fid'])
            break;

    if not tab:
        print "Usage: file_info.py <fid> or <filename> or --latest"
        sys.exit()

    w = gtk.Window()
    w.set_title("FMP - File Info - %s" % tab.fobj.basename)
    w.set_default_size(800,600)
    w.set_position(gtk.WIN_POS_CENTER)

    w.add(tab)
    w.show_all()
    w.connect("destroy", gtk_main_quit)
    # w.maximize()
    gtk.main()
