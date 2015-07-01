
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango

def wait():
    # print "leave1"
    Gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    Gdk.threads_enter()
    # print "/enter"
    if Gtk.events_pending():
        while Gtk.events_pending():
            # print "pending:"
            Gtk.main_iteration(False)
    # print "leave"
    Gdk.threads_leave()
    # print "/leave"

def enter(msg=None):
    # print "enter:",msg
    Gdk.threads_enter()
    # print "/enter:",msg

def leave(msg=None):
    # print "leave:",msg
    Gdk.threads_leave()
    # print "/leave:",msg
