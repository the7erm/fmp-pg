#!/usr/bin/env python
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

from lib.__init__ import *
import lib.fobj as fobj
import os
import sys
import lib.netcast_fobj as netcast_fobj
import pprint
import gtk
import gobject
import time
import lib.clear_cache as clear_cache
from lib.episode_downloader import downloader
gobject.threads_init()

pp = pprint.PrettyPrinter(depth=6, indent=4)

def on_button_press(icon, event, **kwargs):
    print "on_button_press:",icon, event
    if event.button == 1:
        menu.popup(None, None, None, event.button, event.get_time())


def on_update(*args, **kwargs):
    netcast_fobj.update_now()
    update()
    icon.set_from_file(ICON_NOTHING)

def update(*args, **kwargs):
    netcasts = netcast_fobj.get_expired_subscribed_netcasts()
    if not netcasts:
        f = netcast_fobj.get_one_unlistened_episode()
        if f:
            nobj = netcast_fobj.Netcast_File(**f)
            if nobj:
                nobj.netcast.download_unlistened_netcasts()
        clear_cache.clear_cache()
        return True

    icon.set_from_file(ICON_UPDATING)
    for n in netcasts:
        gtk.threads_leave()
        icon.set_tooltip("Updating %s" % (n.name))
        while gtk.events_pending():
            gtk.main_iteration(False)
        gtk.threads_enter()
        n.update()
        n.download_unlistened_netcasts()
    icon.set_tooltip("Done updating")
    icon.set_from_file(ICON_NOTHING)
    clear_cache.clear_cache()
    while gtk.events_pending():
            gtk.main_iteration(False)
    return True

def on_download_status(downloader, status):
    gtk.threads_leave()
    icon.set_tooltip(status)
    icon.set_from_file(ICON_DOWNLOADING)
    while gtk.events_pending():
        gtk.main_iteration(False)
    gtk.threads_enter()


image_path = sys.path[0]+"/images/rss/"
if os.path.exists(sys.path[0]+"/../images/rss/"):
    image_path = os.path.realpath(sys.path[0]+"/../images/rss/")+"/"

ICON_NOTHING = image_path + "red.png"
ICON_DOWNLOADING = image_path + "green.png"
ICON_UPDATING = image_path + "01_01.png"

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
quit_item.connect("activate", lambda _: gtk.main_quit())
menu.append(quit_item)

menu.show_all()
downloader.connect("download-status", on_download_status)

if __name__ == "__main__":
    import lib.pid_handler as pid_handler
    if pid_handler.is_running():
        print "Netcast tray is already running."
        sys.exit()
    pid_handler.write_pid()
    update()
    gobject.timeout_add(60000, update)
    gtk.main()
