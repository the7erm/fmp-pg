
import gtk
import gobject
gobject.threads_init()
gtk.gdk.threads_init()

global threads
threads = []

def kill_threads():
    if not threads or len(threads) == 0:
        return
    print "__init__ threads:",threads
    for t in threads:
        print "KILLING THREAD:",t
        try:
            t._Thread__stop()
        except:
            print "COULDN'T KILL"

def gtk_main_quit(*args, **kwargs):
    kill_threads()
    gtk.main_quit()
