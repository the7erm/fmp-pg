#!/usr/bin/env python
# lib/tray.py -- tray icons
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

import gtk
import sys
import os
from gst import STATE_NULL, STATE_PAUSED, STATE_PLAYING
from picker import wait

gtk.gdk.threads_init()



class TrayIcon:
    def __init__(self):
        self.init_icon()
        self.init_menu()

    def init_icon(self):
        self.icon = gtk.StatusIcon()

    def init_menu(self):
        self.menu = gtk.Menu()

    def on_button_press(self, icon, event, **kwargs):
        print "on_button_press"
        if event.button == 1:
            wait()
            self.menu.popup(None, None, None, event.button, event.get_time())
            wait()

    def set_tooltip(self, text=""):
        self.icon.set_tooltip(text)


class ControllerIcon(TrayIcon):

    def init_icon(self):
        TrayIcon.init_icon(self)
        self.icon.set_name("fmp-player-controller")
        self.icon.set_title("fmp-player-controller")
        self.icon.connect("button-press-event", self.on_button_press)
        self.icon.set_from_stock(gtk.STOCK_MEDIA_PAUSE)

    def init_menu(self):
        TrayIcon.init_menu(self)
        self.pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
        self.play_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)

        self.play_pause_item = gtk.ImageMenuItem("Pause")
        self.play_pause_item.set_image(self.pause_img)
        self.play_pause_item.show()
        self.menu.append(self.play_pause_item)

        self.next = gtk.ImageMenuItem("Next")
        img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_BUTTON)
        self.next.set_image(img)
        self.menu.append(self.next)

        self.prev = gtk.ImageMenuItem("Prev")
        img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_BUTTON)
        self.prev.set_image(img)
        self.menu.append(self.prev)

        self.quit_item = gtk.ImageMenuItem("Quit")
        img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)
        self.quit_item.set_image(img)
        self.menu.append(self.quit_item)

        self.menu.show_all()

    def set_state(self, state):
        if state == STATE_PLAYING:
            self.icon.set_from_stock(gtk.STOCK_MEDIA_PLAY)
            self.play_pause_item.set_label("Pause")
            self.play_pause_item.set_image(self.pause_img)
        else:
            self.icon.set_from_stock(gtk.STOCK_MEDIA_PAUSE)
            self.play_pause_item.set_label("Play")
            self.play_pause_item.set_image(self.play_img)
        self.state = state

class RatingIcon(TrayIcon):
    def __init__(self, playing=None):
        self.rating = 6
        paths = [
            os.path.join(sys.path[0], "images"),
            os.path.join(sys.path[0], "..","images")
        ]
        self.image_path = paths[0]
        for path in paths:
            if os.path.exists(path):
                self.image_path = path
                break

        print "image_path:",self.image_path
        TrayIcon.__init__(self)
        if playing:
            self.playing = playing

    def init_icon(self):
        TrayIcon.init_icon(self)
        self.icon.set_name("fmp-player-rating")
        self.icon.set_title("fmp-player-rating")
        self.icon.connect("button-press-event", self.on_button_press)
        self.icon.connect("scroll-event", self.on_rating_scroll)
        self.icon.set_from_file(os.path.join(self.image_path, "rate.6.svg.png"))

    def init_menu(self):
        TrayIcon.init_menu(self)
        self.rating_items = []
        for i, r in enumerate(range(5,-1,-1)):
            item = gtk.ImageMenuItem("Rate %s" % r)
            self.menu.append(item)
            image_filename = os.path.join(self.image_path, "rate.%s.svg.png" % r)
            if not os.path.exists(image_filename):
                print "MISSING:",image_filename
            print "image_filename:", image_filename
            img = gtk.image_new_from_file(image_filename)
            img.set_pixel_size(gtk.ICON_SIZE_MENU)
            item.set_image(img)
            # self.rating_items.append(item)
            item.connect("activate", self.on_rate, r)

        self.menu.show_all()

    def on_rate(self, item, rating):
        print "on_rate:", item, rating
        if self.playing is not None:
            self.playing.rate(rating=rating, selected=True)
        self.set_rating(rating)

    def on_rating_scroll(self, icon, event, *args, **kwargs):
        rating = self.rating
        if self.playing is not None:
            rating = self.playing.rating

        if event.direction == gtk.gdk.SCROLL_UP:
            rating += 1

        if event.direction == gtk.gdk.SCROLL_DOWN:
            rating -= 1

        print "rating:", rating
        self.set_rating(rating)
        
    def set_rating(self, rating):
        rating = int(rating)
        if rating < 0 or rating > 6:
            return
        self.rating = rating
        if self.playing is not None:
            wait()
            self.playing.rate(rating=rating, selected=True)
        self.icon.set_from_file(os.path.join(self.image_path, "rate.%s.svg.png" % rating))
        wait()

if __name__ == "__main__":
    tray = Tray()
    gtk.main()
