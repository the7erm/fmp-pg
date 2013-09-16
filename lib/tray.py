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
from ConfigParser import NoSectionError

def on_rating_scroll(icon, event):
    gtk.gdk.threads_leave()
    print "on_rating_scroll:",event
    print "event.direction:",event.direction
    r = playing.get_selected()
    rating = r['rating']
    if event.direction == gtk.gdk.SCROLL_UP:
        print "UP"
        rating = rating + 1

    if event.direction == gtk.gdk.SCROLL_DOWN:
        print "DOWN"
        rating = rating - 1

    if rating >= 0 and rating <= 5:
        playing.rate(rating=rating, selected=True)
    set_rating()

def set_rating():
    gtk.gdk.threads_enter()
    if playing.can_rate:
        if not rating_icon.get_visible():
            icon.set_visible(False)
            rating_icon.set_visible(True)
            icon.set_visible(True)
        # print "PLAYING:",playing
        r = playing.get_selected()
        if r:
            # print "R:",r
            rating_icon.set_from_file(image_path+"rate.%s.svg.png" % r['rating'])
        rating_icon.set_tooltip(playing.get_artist_title())
        icon.set_tooltip(playing.get_artist_title())
        song_info.show()
    else:
        icon.set_tooltip(playing.get_artist_title())
        rating_icon.set_visible(False)
        song_info.hide()
    gtk.gdk.threads_leave()

def set_play_pause_item(state):
    gtk.gdk.threads_enter()
    if state != "PLAYING" and state != PLAYING:
        play_pause_item.set_label("Play")
        play_pause_item.set_image(play_img)
        icon.set_from_stock(gtk.STOCK_MEDIA_PAUSE)
        # icon.set_from_file(image_path+"angry-paused-square.jpg")
    else:
        play_pause_item.set_label("Pause")
        play_pause_item.set_image(pause_img)
        icon.set_from_stock(gtk.STOCK_MEDIA_PLAY)
        # icon.set_from_file(image_path+"angry-playing-square.jpg")
    gtk.gdk.threads_leave()


def on_button_press(icon, event, **kwargs):
    print "on_button_press:",icon, event
    if event.button == 1:
        menu.popup(None, None, None, event.button, event.get_time())

def on_rating_button_press(icon, event, **kwargs):
    if event.button == 1:
        rating_menu.popup(None, None, None, event.button, event.get_time())

def on_rate(menu_item, rating):
    gtk.gdk.threads_leave()
    print "on_rate:",menu_item, rating
    print "playing:",playing
    rating = int(rating)
    if rating <= 5 and rating >= 0:
        playing.rate(selected=True, rating=rating)
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

def on_activate_history(*args):
    if os.path.exists(sys.path[0]+"/lib/history_dialog.py"):
        Popen([sys.path[0]+"/lib/history_dialog.py"])
        return
    if os.path.exists(sys.path[0]+"/../lib/history_dialog.py"):
        Popen([sys.path[0]+"/../lib/history_dialog.py"])
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

def on_toggle_cue_netcasts(item,*args):
    cue_netcasts = "%s" % item.get_active()
    cue_netcasts = cue_netcasts.lower()
    print "on_toggle_cue_netcasts:", 
    cfg.set('Netcasts', 'cue', cue_netcasts, bool)

def on_toggle_bedtime_mode(item, *args):
    bedtime = "%s" % item.get_active()
    bedtime = bedtime.lower()
    print "on_toggle_bedtime:", bedtime
    cfg.set('Misc', 'bedtime_mode', bedtime, bool)

def on_activate_favorites(item, *args):
    print "on_activate_favorites"
    q = """INSERT INTO preload (fid, uid, reason) 
                SELECT fid, usi.uid, 'My Favorites' 
                FROM user_song_info usi, users u
                WHERE usi.uid = u.uid AND u.listening = true AND 
                      true_score >= 85 AND ultp <= now() - INTERVAL '1 day'"""
    query(q)

def on_activate_webplayer(item, *args):
    print "on_activate_webplayer"
    if os.path.exists(sys.path[0]+"/lib/player_window.py"):
        Popen([sys.path[0]+"/lib/player_window.py"])
        return
    if os.path.exists(sys.path[0]+"/../lib/player_window.py"):
        Popen([sys.path[0]+"/../lib/player_window.py"])
        return

if os.path.exists(sys.path[0]+"/images/angry-square.jpg"):
    image_path = sys.path[0]+"/images/"

if os.path.exists(sys.path[0]+"/../images/angry-square.jpg"):
    image_path = sys.path[0]+"/../images/"

print "image_path:",image_path

rating_icon = gtk.StatusIcon()
rating_icon.set_name("fmp-rater")
rating_icon.set_title("fmp-rater")
rating_icon.connect("button-press-event", on_rating_button_press)
rating_icon.connect("scroll-event", on_rating_scroll)

icon = gtk.StatusIcon()
icon.set_name("fmp-player")
icon.set_title("fmp-player")
icon.connect("button-press-event", on_button_press)
icon.set_from_stock(gtk.STOCK_MEDIA_PLAY)
# icon.set_from_file(image_path+"angry-playing-square.jpg")


print "sys.path[0]:",sys.path[0]

rating_images = []

rating_menu_items = []
rating_menu = gtk.Menu()

for i, r in enumerate(range(5,-1,-1)):
    rating_menu_items.append(gtk.ImageMenuItem("Rate %s" % r))
    rating_menu.append(rating_menu_items[i])
    image_filename = image_path+"rate.%s.svg.png" % r
    if not os.path.exists(image_filename):
        print "MISSING:",image_filename
    print "image_filename:", image_filename
    rating_images.append(gtk.image_new_from_file(image_filename))
    rating_images[i].set_pixel_size(gtk.ICON_SIZE_MENU)
    rating_menu_items[i].set_image(rating_images[i])
    rating_menu_items[i].connect("activate", on_rate, r)

rating_menu.show_all()
rating_icon.set_from_file(image_path+"rate.6.svg.png")

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

player_window_item = gtk.ImageMenuItem("Player")
img = gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON)
player_window_item.set_image(img)
menu.append(player_window_item)

song_info = gtk.ImageMenuItem("File Info")
img = gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON)
song_info.set_image(img)
menu.append(song_info)

history_info = gtk.ImageMenuItem("History")
img = gtk.image_new_from_stock(gtk.STOCK_INFO, gtk.ICON_SIZE_BUTTON)
history_info.set_image(img)
menu.append(history_info)

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

cue_netcasts_item = gtk.CheckMenuItem("Cue Netcasts")
menu.append(cue_netcasts_item)

bedtime_mode_item = gtk.CheckMenuItem("Bedtime Mode")
menu.append(bedtime_mode_item)

my_favorites_item = gtk.ImageMenuItem("My Favorites")
img = gtk.image_new_from_stock(gtk.STOCK_ADD, gtk.ICON_SIZE_BUTTON)
my_favorites_item.set_image(img)
menu.append(my_favorites_item)

quit = gtk.ImageMenuItem("Quit")
img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)
quit.set_image(img)
menu.append(quit)

menu.show_all()

player_window_item.connect("activate", on_activate_webplayer)
song_info.connect("activate", on_activate_file_info)
history_info.connect("activate", on_activate_history)
listeners.connect("activate", on_activate_listeners)
genres.connect("activate", on_activate_genres)
preload.connect("activate", on_activate_preload)
cue_netcasts_item.connect("toggled", on_toggle_cue_netcasts, ())
bedtime_mode_item.connect("toggled", on_toggle_bedtime_mode, ())
my_favorites_item.connect("activate", on_activate_favorites, ())

cue_netcasts = cfg.get('Netcasts', 'cue', False, bool)
cue_netcasts_item.set_active(cue_netcasts)

bedtime_mode = cfg.get("Misc", "bedtime_mode", False, bool)
bedtime_mode_item.set_active(bedtime_mode)

if __name__ == "__main__":
    def toggle_pause(item):
        if play_pause_item.get_label() == "Play":
            set_play_pause_item("PAUSED")
        else:
            set_play_pause_item("PLAYING")

    play_pause_item.connect("activate",toggle_pause)
    gtk.main()

