#!/usr/bin/env python
# lib/notify.py -- send notification about file.
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
import sys, os
import pygtk
pygtk.require('2.0')
import gtk
import notify2
from subprocess import Popen
import mutagen

notify2.init("Playing", mainloop='glib')

def more_info(n, action, fid):
    n.close()
    print "action:",action
    print "fid:",fid
    if os.path.exists(sys.path[0]+"/lib/file_info.py"):
        Popen([sys.path[0]+"/lib/file_info.py", str(fid)])
    # del n


def playing(file_info):
    print "file_info:",file_info
    
    msg = ""
    stats = []
    tags = []
    if file_info.can_rate:
        stats = get_results_assoc("""SELECT uname, rating 
                                     FROM user_song_info ui, users u 
                                     WHERE u.listening = true AND 
                                           u.uid = ui.uid AND fid = %s 
                                     ORDER BY admin DESC, uname""", 
                                     (file_info['fid'],))

    for s in stats:
        if msg:
            msg = msg+"\n"
        rating = "*"*s['rating']
        msg = msg + s['uname'] + ":" + rating

    if file_info.exists:
        print "FILENAME:",file_info["filename"]
        tags = mutagen.File(file_info["filename"])
    pbuf = None
    if tags and tags.has_key('APIC'):
        lower_mime = tags['APIC'].mime.lower()
        if lower_mime in("image/jpg","image/jpeg"):
            fp = open("tmp.jpg","wb")
            fp.write(tags['APIC'].data)
            fp.close()
            pbuf = gtk.gdk.pixbuf_new_from_file("tmp.jpg")

        if lower_mime in("image/png"):
            fp = open("tmp.png","wb")
            fp.write(tags['APIC'].data)
            fp.close()
            pbuf = gtk.gdk.pixbuf_new_from_file("tmp.png")
            

        if lower_mime in("image/gif"):
            fp = open("tmp.gif","wb")
            fp.write(tags['APIC'].data)
            fp.close()
            pbuf = gtk.gdk.pixbuf_new_from_file("tmp.gif")

    #else:
    #    pbuf = gtk.gdk.pixbuf_new_from_file("tmp.jpg")

    # helper = Gtk.Button()
    # icon = helper.render_icon(Gtk.STOCK_DIALOG_QUESTION, Gtk.IconSize.DIALOG)
    

    n = notify2.Notification("Playing %s" % (file_info['basename']),msg)
    if file_info.can_rate:
        n.add_action("file_info", "More Info", more_info, file_info['fid'])
    n.set_timeout(3000)
    if pbuf:
        print "PBUFF DETECTED"
        print gtk.ICON_SIZE_DIALOG
        n.set_icon_from_pixbuf(pbuf.scale_simple(100, 100, gtk.gdk.INTERP_TILES))
        del pbuf
    n.show()
    # Raw image
    # n = notify2.Notification("Raw image test",
    #                          "Testing sending raw pixbufs")
    

if __name__ == "__main__":
    
    # print sys.argv[1]
    notify_test(10)
    gtk.main()


