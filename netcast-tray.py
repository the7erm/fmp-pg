#!/usr/bin/env python2
# lib/netcast-tray.py -- Download/manage netcasts
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

from init.__init__ import *
from util.wait_util import wait, enter, leave
import file_objects.fobj as fobj
import os
import sys
import file_objects.netcast as netcast_fobj
import pprint
import gtk
import gobject
import time
import util.clear_cache as clear_cache
from util.episode_downloader import downloader

pp = pprint.PrettyPrinter(depth=6, indent=4)

def on_button_press(icon, event, **kwargs):
    print "on_button_press:",icon, event
    if event.button == 1:
        menu.popup(None, None, None, event.button, event.get_time())
        wait()

def on_update(*args, **kwargs):
    leave("on_update")
    netcast_fobj.update_now()
    update()

def set_tooltip(msg):
    enter("set_tooltip:%s" % msg)
    icon.set_tooltip(msg)
    leave("set_tooltip:%s" % msg)
    wait()

def set_icon(img, msg=None):
    enter("set_icon:%s %s" % (img, msg))
    if msg is not None:
        icon.set_tooltip(msg)
    icon.set_from_file(img)
    leave("set_icon:%s %s" % (img, msg))
    wait()

def update(*args, **kwargs):
    leave("def update")
    if downloader.downloading:
        print "Not updating downloader is getting a file."
        return True

    netcasts = netcast_fobj.get_expired_subscribed_netcasts()
    wait()
    if not netcasts:
        f = netcast_fobj.get_one_unlistened_episode()
        wait()
        if f:
            nobj = netcast_fobj.Netcast_File(**f)
            if nobj:
                wait()
                nobj.netcast.download_unlistened_netcasts()
        clear_cache.clear_cache()
        set_icon(ICON_NOTHING, "Done updating")
        return True

    
    if not downloader.downloading:
        set_icon(ICON_UPDATING, "Updating")

    for n in netcasts:
        set_tooltip("Updating %s" % (n.name,))
        n.update()
        n.download_unlistened_netcasts()
    clear_cache.clear_cache()
    set_icon(ICON_NOTHING, "Done updating")
    return True

def on_download_status(downloader, status):
    set_icon(ICON_DOWNLOADING, status)

def on_download_done(downloader, status):
    set_icon(ICON_NOTHING, status)


image_path = os.path.join(sys.path[0], "images", "rss")
alt_image_path = os.path.realpath(os.path.join(sys.path[0], "..", "images", "rss"))
if os.path.exists(alt_image_path):
    image_path = alt_image_path

ICON_NOTHING = os.path.join(image_path, "red.png")
ICON_DOWNLOADING = os.path.join(image_path, "green.png")
ICON_UPDATING = os.path.join(image_path, "01_01.png")

icon = gtk.StatusIcon()
icon.set_has_tooltip(True)
icon.set_from_file(ICON_NOTHING)
icon.set_visible(False)
icon.set_visible(True)
icon.connect("button-press-event", on_button_press)

menu = gtk.Menu()

update_img = gtk.image_new_from_stock(gtk.STOCK_CONNECT, gtk.ICON_SIZE_BUTTON)

update_item = gtk.ImageMenuItem("Update Netcasts")
update_item.set_image(update_img)
update_item.show()
update_item.connect("activate", on_update)
menu.append(update_item)

quit_img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)

quit_item = gtk.ImageMenuItem("Quit Netcast Tray")
quit_item.set_image(quit_img)
quit_item.show()
quit_item.connect("activate", gtk_main_quit)
menu.append(quit_item)

menu.show_all()
downloader.connect("download-status", on_download_status)
downloader.connect("download-done", on_download_done)

if __name__ == "__main__":
    import util.pid_handler as pid_handler
    if pid_handler.is_running():
        print "Netcast tray is already running."
        sys.exit()
    pid_handler.write_pid()
    wait()
    update()
    gobject.timeout_add(60000, update)
    gtk.main()
