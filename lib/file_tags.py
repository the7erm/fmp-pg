#!/usr/bin/env python2
# lib/file_info.py -- Display dialog about file
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
import gtk, re, os
from subprocess import Popen
try:
    import mutagen
    import mutagen.id3
except ImportError, err:
	print "mutagen isn't installed"
	print "run sudo apt-get install python-mutagen"
	exit(1)

class Tag_Table(gtk.Table):
    def __init__(self, tag_object=None, order=['artist','title','genre','album', 'date', 'tracknumber', 'TPE1','TPE2',"TIT2","TCON", "TALB", "TDRC", "TRCK"]):
        gtk.Table.__init__(self)
        self.tag_object = tag_object
        self.pre_order = order
        self.setup_table()
        self.show()

    def setup_table(self):
        if not self.tag_object:
            return
        r = 0
        for t in self.pre_order:
            if not self.tag_object.has_key(t):
                continue
            self.add_row(r, t, self.tag_object[t])
            r = r + 1

        for t in sorted(self.tag_object.keys()):
            if t in self.pre_order:
                continue
            self.add_row(r, t, self.tag_object[t])
            r = r + 1

        button_hbox = gtk.HButtonBox()

        buttons = [
            'kid3',
            'picard'
        ]

        for b in buttons:
            button = gtk.Button()
            button.set_label("Open in %s" % b)
            img = gtk.Image()
            img.set_from_stock(gtk.STOCK_OPEN, gtk.ICON_SIZE_MENU)
            button.set_image(img)
            button_hbox.pack_start(button)
            button.connect("clicked",self.on_click,b)
        button_hbox.show_all()
        
        self.attach(button_hbox,0,2,r,r+1,gtk.SHRINK, gtk.SHRINK,0,0)
        # self.add_row(r, t, self.tag_object[t])


    def on_click(self, btn, text):
        print "on_click:",btn, text
        print "self.tag_object.filename:", self.tag_object.filename
        Popen([text, self.tag_object.filename])
        

    def add_row(self, r, tag, frame):
        if type(frame) == mutagen.id3.APIC:
            print "APIC"
            print "MIME:",frame.mime
            lower_mime = frame.mime.lower()
            if lower_mime in("image/jpg","image/jpeg"):
                fp = open("tmp.jpg","wb")
                fp.write(frame.data)
                fp.close()
                image = gtk.image_new_from_file("tmp.jpg")
                label = gtk.Label("APIC:")
                label.show()
                label.set_property("xalign",1.0)
                self.attach(label,0,1,r,r+1,gtk.FILL,gtk.SHRINK,0,0)
                self.attach(image,1,2,r,r+1,gtk.FILL,gtk.FILL,0,0)
                r = r + 1
                return

            if lower_mime in("image/png"):
                fp = open("tmp.png","wb")
                fp.write(frame.data)
                fp.close()
                image = gtk.image_new_from_file("tmp.png")
                label = gtk.Label("APIC:")
                label.show()
                label.set_property("xalign",1.0)
                self.attach(label,0,1,r,r+1,gtk.FILL,gtk.SHRINK,0,0)
                self.attach(image,1,2,r,r+1,gtk.FILL,gtk.FILL,0,0)
                r = r + 1
                return

            if lower_mime in("image/gif"):
                fp = open("tmp.gif","wb")
                fp.write(frame.data)
                fp.close()
                image = gtk.image_new_from_file("tmp.gif")
                label = gtk.Label("APIC:")
                label.show()
                label.set_property("xalign",1.0)
                self.attach(label,0,1,r,r+1,gtk.FILL,gtk.SHRINK,0,0)
                self.attach(image,1,2,r,r+1,gtk.FILL,gtk.FILL,0,0)
                r = r + 1
                return

        try:
            for i,v in enumerate(frame):
                # attach(child, left_attach, right_attach, top_attach, bottom_attach, xoptions=gtk.EXPAND|gtk.FILL, yoptions=gtk.EXPAND|gtk.FILL, xpadding=0, ypadding=0)
                label, entry = self.create_entry("%s[%s]:" % (tag, i), v)
                label.set_property("xalign",1.0)
                self.attach(label,0,1,r,r+1,gtk.FILL,gtk.SHRINK,0,0)
                self.attach(entry,1,2,r,r+1,gtk.FILL|gtk.EXPAND,gtk.FILL,0,0)
                r = r + 1
        except TypeError, err:
            print "TypeError:",err
            print frame
            pass

    def create_entry(self, text, value):
        label = gtk.Label(text)
        entry = gtk.Entry()
        entry.set_text("%s" % value)
        return label, entry

class File_Tags_Tab(gtk.VBox):
    def __init__(self, fid=None, filename=None, file_info=None):
        gtk.VBox.__init__(self)
        self.vbox = gtk.VBox()
        self.pack_start(self.vbox,True,True)
        l = gtk.Label()
        l.set_markup("<b>Tags (Easy)</b>")
        self.vbox.pack_start(l,False,True)
        # self.add_with_viewport(self.vbox)
        self.fid = None
        self.filename = None
        self.dirname = None
        self.basename = None

        if filename:
            self.filename = os.path.realpath(filename)
            self.dirname = os.path.dirname(self.filename)
            self.basename = os.path.basename(self.filename)

        if fid:
            fid = int(fid)
            self.fid = fid

        if not file_info:
            self.file_info = get_assoc("SELECT * FROM files WHERE (dir = %s AND basename = %s) OR fid = %s LIMIT 1",(self.dirname, self.basename, self.fid))
        else:
            self.file_info = file_info

        if self.file_info:
            self.filename = os.path.join(self.file_info['dir'], self.file_info['basename'])
            self.basename = self.file_info['basename']
            self.dirname = self.file_info['dir']
            self.fid = self.file_info['fid']


        self.tags_easy = mutagen.File(self.filename, easy=True)
        self.tags_hard = mutagen.File(self.filename)

        table1 = Tag_Table(self.tags_easy)
        l = gtk.Label()
        l.set_markup("<b>Tags (Hard)</b>")
        
        table2 = Tag_Table(self.tags_hard)
        self.pack_start(table1,True,True)
        self.pack_start(l,False,True)
        self.pack_start(table2,True,True)

   

if __name__ == "__main__":
    for arg in sys.argv[1:]:
        result = re.match("^[0-9]+$", arg)
        if result:
            # It's a number so treat it as an fid.
            fid = int(arg)
            tab = File_Tags_Tab(fid=fid)
            break;
            
        if os.path.isfile(arg):
            filename = os.path.realpath(arg)
            tab = File_Tags_Tab(filename=filename)
            break

        if arg == "--latest":
            file_info = get_assoc("SELECT * FROM user_song_info WHERE ultp IS NOT NULL ORDER BY ultp DESC LIMIT 1")
            if not file_info:
                print "couldn't find recent file."
                sys.exit()
            tab = File_Tags_Tab(file_info=file_info)
            break;

    if not tab:
        print "Usage: file_tags.py <fid> or <filename> or --latest"
        sys.exit()

    w = gtk.Window()
    w.set_title("FMP - File Tags - %s" % tab.file_info['basename'])
    w.set_default_size(600,400)
    w.set_position(gtk.WIN_POS_CENTER)
    
    w.add(tab)
    w.show_all()
    w.connect("destroy", gtk_main_quit)
    gtk.main()

