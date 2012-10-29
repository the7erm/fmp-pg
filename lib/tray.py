#!/usr/bin/env python
# lib/tray.py -- tray icons
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
import gtk, sys, os
from player import PLAYING
from subprocess import Popen, PIPE

def on_rating_scroll(icon, event):
    print "on_rating_scroll:",event
    print "event.direction:",event.direction
    r = get_assoc("SELECT rating FROM user_song_info WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true AND selected = true)", (playing["fid"],))
    rating = r['rating']
    if event.direction == gtk.gdk.SCROLL_UP:
        print "UP"
        rating = rating + 1

    if event.direction == gtk.gdk.SCROLL_DOWN:
        print "DOWN"
        rating = rating - 1

    if rating >= 0 and rating <= 5:
        query("UPDATE user_song_info SET rating = %s, true_score = (((%s * 2 * 10) + (score * 10) + percent_played) / 3)  WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true AND selected = true)", (rating, rating, playing['fid'],))
    
    set_rating()

def set_rating():
    # print "playing:",playing
    r = get_assoc("SELECT rating FROM user_song_info WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true AND selected = true)", (playing["fid"],))
    rating_icon.set_from_file(image_path+"rate.%s.svg" % r['rating'])
    rating_icon.set_tooltip(playing['basename'])
    icon.set_tooltip(playing['basename'])


def set_play_pause_item(state):
    if state != "PLAYING" and state != PLAYING:
        play_pause_item.set_label("Play")
        play_pause_item.set_image(play_img)
    else:
        play_pause_item.set_label("Pause")
        play_pause_item.set_image(pause_img)


def on_button_press(icon, event, **kwargs):
    print "on_button_press:",icon, event
    if event.button == 1:
        menu.popup(None, None, None, event.button, event.get_time())

def on_rating_button_press(icon, event, **kwargs):
    if event.button == 1:
        rating_menu.popup(None, None, None, event.button, event.get_time())

def on_rate(menu_item, rating):
    print "on_rate:",menu_item, rating
    print "playing:",playing
    rating = int(rating)
    if rating <= 5 and rating >= 0:
        query("UPDATE user_song_info SET rating = %s, true_score = (((%s * 2 * 10) + (score * 10) + percent_played) / 3) WHERE fid = %s AND uid IN (SELECT uid FROM users WHERE listening = true AND selected = true)", (rating, rating, playing['fid']))
        set_rating()

def on_activate_listeners(*args):
    # WHY?! because I'm sick of running down thread locks.
    if os.path.exists(sys.path[0]+"/lib/listeners_list.py"):
        Popen([sys.path[0]+"/lib/listeners_list.py"])
        return
    if os.path.exists("./lib/listeners_list.py"):
        Popen(['./lib/listeners_list.py'])
        return

    if os.path.exists("./listeners_list.py"):
        Popen(['./listeners_list.py'])
        return

    if os.path.exists("../lib/listeners_list.py"):
        Popen(['../lib/listeners_list.py'])
        return

def on_activate_file_info(*args):
    fid = str(playing['fid'])
    if os.path.exists(sys.path[0]+"/lib/file_info.py"):
        Popen([sys.path[0]+"/lib/file_info.py", fid])
        return
    if os.path.exists(sys.path[0]+"/../lib/file_info.py"):
        Popen([sys.path[0]+"/../lib/file_info.py", fid])
        return


def on_activate_genres(*args):
    # WHY?! because I'm sick of running down thread locks.
    if os.path.exists(sys.path[0]+"/lib/genre_config_box.py"):
        Popen([sys.path[0]+"/lib/genre_config_box.py"])
        return
    if os.path.exists(sys.path[0]+"/../lib/genre_config_box.py"):
        Popen([sys.path[0]+"/../lib/genre_config_box.py"])
        return

def on_activate_preload(*args):
    # WHY?! because I'm sick of running down thread locks.
    if os.path.exists(sys.path[0]+"/lib/preload.py"):
        Popen([sys.path[0]+"/lib/preload.py"])
        return
    if os.path.exists(sys.path[0]+"/../lib/preload.py"):
        Popen([sys.path[0]+"/../lib/preload.py"])
        return


if os.path.exists(sys.path[0]+"/images/angry-square.jpg"):
    image_path = sys.path[0]+"/images/"

if os.path.exists(sys.path[0]+"/../images/angry-square.jpg"):
    image_path = sys.path[0]+"/../images/"

rating_icon = gtk.StatusIcon()
rating_icon.set_name("fmp-2-player")
rating_icon.set_title("fmp-2-player")
rating_icon.connect("button-press-event", on_rating_button_press)
rating_icon.connect("scroll-event", on_rating_scroll)

rating_images = []

rating_menu_items = []
rating_menu = gtk.Menu()

for i, r in enumerate(range(5,-1,-1)):
    rating_menu_items.append(gtk.ImageMenuItem("Rate %s" % r))
    rating_menu.append(rating_menu_items[i])
    rating_images.append(gtk.image_new_from_file(image_path+"rate.%s.svg" % r))
    rating_images[i].set_pixel_size(gtk.ICON_SIZE_MENU)
    rating_menu_items[i].set_image(rating_images[i])
    rating_menu_items[i].connect("activate",on_rate,r)

rating_menu.show_all()
rating_icon.set_from_file(image_path+"rate.6.svg")

menu = gtk.Menu()

pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
play_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)

play_pause_item = gtk.ImageMenuItem("Pause")
play_pause_item.set_image(pause_img)
play_pause_item.show()
menu.append(play_pause_item)

next = gtk.ImageMenuItem("Next")
img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_BUTTON)
next.set_image(img)
menu.append(next)

prev = gtk.ImageMenuItem("Prev")
img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_BUTTON)
prev.set_image(img)
menu.append(prev)

song_info = gtk.ImageMenuItem("File Info")
img = gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON)
song_info.set_image(img)
menu.append(song_info)

listeners = gtk.ImageMenuItem("Listeners")
img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
listeners.set_image(img)
menu.append(listeners)

genres = gtk.ImageMenuItem("Genres")
img = gtk.image_new_from_stock(gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_BUTTON)
genres.set_image(img)
menu.append(genres)

preload = gtk.ImageMenuItem("Preload")
img = gtk.image_new_from_stock(gtk.STOCK_PROPERTIES, gtk.ICON_SIZE_BUTTON)
preload.set_image(img)
menu.append(preload)



quit = gtk.ImageMenuItem("Quit")
img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)
quit.set_image(img)
menu.append(quit)

menu.show_all()

song_info.connect("activate", on_activate_file_info)
listeners.connect("activate", on_activate_listeners)
genres.connect("activate", on_activate_genres)
preload.connect("activate",on_activate_preload)



icon = gtk.StatusIcon()
icon.set_name("fmp-3-player")
icon.set_title("fmp-3-player")
icon.connect("button-press-event", on_button_press)

print "sys.path[0]:",sys.path[0]


icon.set_from_file(image_path+"angry-square.jpg")


if __name__ == "__main__":
    def toggle_pause(item):
        if play_pause_item.get_label() == "Play":
            set_play_pause_item("PAUSED")
        else:
            set_play_pause_item("PLAYING")

    play_pause_item.connect("activate",toggle_pause)
    gtk.main()

