
import gtk

def wait():
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"

def enter(msg=None):
    # print "enter:",msg
    gtk.gdk.threads_enter()
    # print "/enter:",msg

def leave(msg=None):
    # print "leave:",msg
    gtk.gdk.threads_leave()
    # print "/leave:",msg
