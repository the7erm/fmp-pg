import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gtk, GdkX11, Gdk, Pango,\
                          GLib, Gio, GdkPixbuf
import signal
signal.signal(signal.SIGINT, signal.SIG_DFL)

from pprint import pprint
import os
import sys

try:
    from log_class import Log, logging
except:
   
    sys.path.append("../")
    from log_class import Log, logging

logger = logging.getLogger(__name__)

paths = [
    os.path.join(sys.path[0], "images"),
    "images",
    "../images",
]

IMAGE_PATH = paths[0]

for path in paths:
    six_path = os.path.join(path, "rate.6.svg")
    if os.path.exists(six_path):
        IMAGE_PATH = path
        break


class RatingTrayIcon(Log):
    __name__ = 'RatingTrayIcon'
    logger = logger
    def __init__(self, playlist=None):
        self.playlist = playlist
        self.playlist.player.connect('artist-title-changed', 
            self.on_artist_title_changed)
        self.init_icon()
        self.init_menu()
        self.set_rating(6)
        self.on_artist_title_changed()

    def init_icon(self):
        self.ind = Gtk.StatusIcon()
        self.ind.connect("button-press-event", self.on_button_press)

    def set_rating(self, rating, update=False, broadcast_change=True):
        self.ind.set_from_file(os.path.join(IMAGE_PATH, "rate.%s.svg" % rating))

        if update:
            self.log_debug("UPDATING")
            index = self.playlist.index
            broadcast_change = True
            for file_info in self.playlist.files[index].listeners.user_file_info:
                pprint(file_info)
                if not file_info.fid:
                    self.ind.set_visible(False)
                    continue
                self.ind.set_visible(True)
                pprint(file_info)
                file_info.rating = rating
                break
        if broadcast_change:
            self.playlist.broadcast_change()

    def on_artist_title_changed(self, *args, **kwargs):
        print "*"*100
        self.log_debug(".on_artist_title_changed() %s %s" % (args, kwargs))
        playlist = self.playlist
        index = self.playlist.index
        for file_info in self.playlist.files[index].listeners.user_file_info:
            self.log_debug("<<<<<<<<<<<<<<<<<<<< THIS ")
            pprint(file_info)
            if not file_info.fid:
                self.ind.set_visible(False)
                continue
            self.ind.set_visible(True)
            self.set_rating(file_info.rating, **kwargs)
            break
        
    def on_button_press(self, icon, event, **kwargs):
        self.log_info(".on_button_press: %s, %s", icon, event)
        if event.button == 1:
            self.menu.popup(None, None, None, None, event.button, event.time)

    def init_menu_quit(self):
        return
        quit_item = Gtk.ImageMenuItem("Quit")
        quit_item.connect("activate", self.on_menuitem_clicked)
        img = Gtk.Image.new_from_stock(Gtk.STOCK_QUIT, 
                                       Gtk.IconSize.BUTTON)
        quit_item.set_image(img)
        quit_item.show()
        self.menu.append(quit_item)

    def init_menu_ratings(self):
        for i in range(5, -1, -1):
            item = Gtk.ImageMenuItem("%s" % i)
            item.connect("activate", self.on_menuitem_clicked)
            img = Gtk.Image.new_from_file(os.path.join(IMAGE_PATH, "rate.%s.svg" % i))
            item.set_image(img)
            item.show()
            self.menu.append(item)

    def init_menu(self):
        self.menu = Gtk.Menu()
        self.init_menu_ratings()
        self.init_menu_quit()

    def on_menuitem_clicked(self, item):
        label = item.get_label()
        if label == 'Quit':
            Gtk.main_quit()
        try:
            i = int(label)
            self.set_rating(i, True)
        except:
            pass
        print "CLICKED:%s " % (item.get_label())

if __name__ == "__main__":
    icon = RatingTrayIcon()
    Gtk.main()