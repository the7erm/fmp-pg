#!/usr/bin/env python

import webkit 
import gtk
import gobject
import thread

# win = gtk.Window(gtk.WINDOW_TOPLEVEL) 
# win.add(sw) 
# win.show_all() 

# view.open("http://w3.org/") 

class PlayerWindow(gtk.Window):
    def __init__(self):
        gtk.Window.__init__(self)
        self.set_default_size(600, 400)
        self.set_position(gtk.WIN_POS_CENTER)
        self.vbox_container = gtk.VBox()
        self.add(self.vbox_container)
        view = webkit.WebView()
        sw = gtk.ScrolledWindow() 
        sw.add(view)
        self.vbox_container.pack_start(sw)
        view.open("http://localhost:5050/") 
        self.show_all()

    def on_button_press_event(self, *args, **kwargs):
        # logger.info("on_button_press_event:%s, %s", args, kwargs)
        self.destroy()
        gtk.main_quit()

    def destroy_window(self, *args, **kwargs):
        # logger.info("destroy_window:%s %s", args, kwargs)
        self.destroy()
        gtk.main_quit()
        return False


    def ensure_above(self, *args, **kwargs):
        # logger.info("ensure_above:%s %s", args, kwargs)
        self.set_keep_above(True)
        return False


if __name__ == '__main__':
    w = PlayerWindow()
    w.connect("destroy", gtk.main_quit)
    gtk.gdk.threads_init()
    gtk.main()
