#!/usr/bin/env python
# lib/player.py -- main gstreamer player
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

## TODO: add appindicator in __main__ section

from __init__ import gtk_main_quit
import sys, os, time, thread, signal, urllib, gc
import gobject, pygst, pygtk, gtk, appindicator, pango
import base64
# gobject.threads_init()
pygst.require("0.10")
import gst

STOPPED = gst.STATE_NULL
PAUSED = gst.STATE_PAUSED
PLAYING = gst.STATE_PLAYING

class Player(gobject.GObject):
    __gsignals__ = {
        'error': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str,str)),
        'end-of-stream': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'show-window': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'time-status': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (gobject.TYPE_INT64, gobject.TYPE_INT64, gobject.TYPE_INT64, gobject.TYPE_DOUBLE, str, str, str, str)), # pos, length, left, decimal, pos_formatted, length_formatted, left_formatted, percent_formatted
        'state-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'tag-received': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (str, object)),
        'missing-plugin': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, (object,)),
        'SIGUSR1-received': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'SIGUSR2-received': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ()),
        'missing-plugin': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, ())
    }
    
    def __init__(self, filename=None):
        gobject.GObject.__init__(self)
        signal.signal(signal.SIGUSR1,self.signal_handler)
        signal.signal(signal.SIGUSR2,self.signal_handler)
        self.showingControls = False
        self.filename = filename
        self.playingState = STOPPED
        self.play_thread_id = None
        self.fullscreen = False
        self.seek_locked = False
        self.pos_data = {}
        self.dur_int = 0
        self.pos_int = 0
        self.volume = 1.0
        self.hide_window_timeout = None
        self.time_format = gst.Format(gst.FORMAT_TIME)
        self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
        self.window.set_title("Video-Player")
        
        img_path = ""
        if os.path.exists(sys.path[0]+"/images/"):
            img_path = sys.path[0]+"/"
        elif os.path.exists(sys.path[0]+"/../images/"):
            img_path = sys.path[0]+"/../"
        elif os.path.exists("../images/"):
            img_path = "../"
        
        
        self.window.set_icon_from_file(img_path+'images/tv.png');
            
        self.window.connect("destroy", gtk_main_quit)
        self.window.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        self.window.add_events(gtk.gdk.KEY_PRESS_MASK |
                               gtk.gdk.POINTER_MOTION_MASK |
                               gtk.gdk.BUTTON_PRESS_MASK |
                               gtk.gdk.SCROLL_MASK)
        self.window.connect('key-press-event', self.on_key_press)
        self.window.connect('motion-notify-event', self.show_controls)
        # self.window.connect('button-press-event', self.show_controls)
        self.window.connect('button-press-event', self.pause)
        # self.window.connect('key-press-event', self.show_controls)
        self.window.connect("scroll-event", self.on_scroll)
        
        self.window.set_title("Video-Player")
        self.window.set_default_size(600, 400)
        self.window.connect("destroy", gtk_main_quit, "WM destroy")
        

        #main Event Box
        mainEb = gtk.EventBox()
        mainEb.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        mainEb.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        mainEb.connect('motion-notify-event',self.show_controls)
        self.window.add(mainEb)

        # main box
        self.mainVBox = gtk.VBox()
        self.mainVBox.show()
        mainEb.add(self.mainVBox)

        
        ## Time label ##
                
        self.timeLabel = gtk.Label()
        self.timeLabel.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#FFFFFF"))
        self.timeLabel.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#000000"))
        self.timeLabel.set_property('xalign',1.0)
        self.timeLabel.modify_font(pango.FontDescription("15"))
        self.mainVBox.pack_start(self.timeLabel,False,True)
        self.timeLabel.show()
        
        ## movie_window
        
        self.movie_window = gtk.DrawingArea()
        # gtk.DrawingArea()
        # self.movie_window.set_has_window(True)
        self.movie_window.modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("#000000"))
        self.movie_window.add_events(gtk.gdk.KEY_PRESS_MASK | gtk.gdk.POINTER_MOTION_MASK)
        # self.movie_window.connect('key-press-event', self.on_key_press)
        self.movie_window.connect('motion-notify-event',self.show_controls)
        self.movie_window.show()
        self.mainVBox.pack_start(self.movie_window, True, True)

        self.connect('time-status',self.on_time_status)
        
        # eb = gtk.EventBox()
        # eb.add(self.controls)
        # eb.set_visible_window(False)

        ### SET UP CONTROLS ###
        self.controls = gtk.HBox()
        self.prev_button = gtk.Button('',gtk.STOCK_MEDIA_PREVIOUS)
        self.pause_button = gtk.Button('',gtk.STOCK_MEDIA_PAUSE)
        self.play_button = gtk.Button('',gtk.STOCK_MEDIA_PLAY)
        self.next_button = gtk.Button('',gtk.STOCK_MEDIA_NEXT)
        
        self.fs_button = gtk.Button('',gtk.STOCK_FULLSCREEN)
        self.unfs_button = gtk.Button('',gtk.STOCK_LEAVE_FULLSCREEN)
        
        self.pause_button.connect('clicked', self.pause)
        self.play_button.connect('clicked', self.pause)
        
        hb = gtk.HBox()
        e = gtk.EventBox()
        e.add(hb)
        e.modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("#000000"))
        hb.pack_start(self.prev_button,False,False)
        hb.pack_start(self.pause_button,False,False)
        hb.pack_start(self.play_button,False,False)
        hb.pack_start(self.next_button,False,False)
        
        self.controls.pack_start(e,False,False)

        
        
        hb = gtk.HBox()
        e = gtk.EventBox()
        e.add(hb)
        e.modify_bg(gtk.STATE_NORMAL,gtk.gdk.color_parse("#000000"))
        hb.pack_start(self.fs_button,False,False)
        hb.pack_start(self.unfs_button,False,False)
        
        self.controls.pack_end(e,False,False)
        
        self.fs_button.connect('clicked',self.toggle_full_screen)
        self.unfs_button.connect('clicked',self.toggle_full_screen)

        #### END OF SETTING UP CONTROLS ## ##

        self.mainVBox.pack_end(self.controls,False,True)

        self.player = gst.element_factory_make("playbin2", "player")
        
        vol = self.player.get_property("volume")
        print "DEFAULT VOLUME:",vol
        bus = self.player.get_bus()
        bus.add_signal_watch()
        bus.enable_sync_message_emission()
        bus.connect("message", self.on_message)
        bus.connect("sync-message::element", self.on_sync_message)
        
        pix_data = """/* XPM */
static char * invisible_xpm[] = {
"1 1 1 1",
"       c None",
" "};"""
        color = gtk.gdk.Color()
        pix = gtk.gdk.pixmap_create_from_data(None, pix_data, 1, 1, 1, color, color)
        self.invisble_cursor = gtk.gdk.Cursor(pix, pix, color, color, 0, 0)
        
        self.connect('state-changed',self.show_hide_play_pause)
        self.hide_timeout = None
        
        
        self.window.show_all()
        self.pause_button.hide()
        self.play_button.hide()
        self.controls.hide()
        self.show_hide_play_pause()
        self.window.hide()
        
        gobject.timeout_add(1000,self.update_time)
    
    def to_dict(self):
        return {
            "filename": self.filename,
            "pos_data": self.pos_data,
            "playingState": self.state_to_string(self.playingState),
            "tags": self.tags
        }

    def state_to_string(self, state):
        if state == PLAYING:
            return "PLAYING"
        if state == PAUSED:
            return "PAUSED"
        if state == STOPPED:
            return "STOPPED"
        return "ERROR"
        
    def show_hide_play_pause(self,*args):    
        if self.playingState in (STOPPED, PAUSED):
            self.play_button.show()
            self.pause_button.hide()
        else:
            self.play_button.hide()
            self.pause_button.show()
        if self.fullscreen:
            self.fs_button.hide()
            self.unfs_button.show()
        else:
            self.fs_button.show()
            self.unfs_button.hide()
        self.next_button.show()
        self.prev_button.show()
            
    def toggle_full_screen(self, *args):
        if self.fullscreen:
            self.fullscreen = False
            self.window.unfullscreen()
            self.movie_window.window.set_cursor(None)
        else:
            self.fullscreen = True
            self.window.fullscreen()
            self.movie_window.window.set_cursor(self.invisble_cursor)
        
        self.show_hide_play_pause()
        self.window.emit('check-resize')
        
    
    def on_scroll(self, widget, event):
        print "on_scroll:"
        gtk.gdk.threads_leave()
        if event.direction == gtk.gdk.SCROLL_UP:
            self.seek("+5")
        if event.direction == gtk.gdk.SCROLL_DOWN:
            self.seek("-5")
        print "/on_scroll"

    def ind_on_scroll(self, widget, steps, direction):
        if direction == 0:
            self.seek("+5")
        else:
            self.seek("-5")
        
    
    def show_controls(self,*args):
        # print "show_controls"
        
        self.controls.show()
        self.timeLabel.show()
        self.show_hide_play_pause()
        if self.hide_timeout:
            gobject.source_remove(self.hide_timeout)
            self.hide_timeout = None
        self.hide_timeout = gobject.timeout_add(3000, self.hide_controls)
        # if self.fullscreen:
        self.movie_window.window.set_cursor(None)
        self.showingControls = True
        
        
    def hide_controls(self):
        self.showingControls = False
        self.controls.hide()
        self.timeLabel.hide()
        self.hide_timeout = None
        #if self.fullscreen:
        self.movie_window.window.set_cursor(self.invisble_cursor)
        
    def on_key_press(self, widget, event):
        keyname = gtk.gdk.keyval_name(event.keyval)
        if keyname in ('f','F'):
            self.toggle_full_screen()

        if keyname in ('d','D'):
            if self.window.get_decorated():
                self.window.set_decorated(False)
            else:
                self.window.set_decorated(True)
            self.window.emit('check-resize')
                
        if keyname in ('Return','p','P','a','A','space'):
            self.show_controls()
            self.pause()
            
        if keyname == 'Up':
            self.seek("+5")
        
        if keyname == 'Down':
            self.seek("-5")
            
        if keyname == 'Right':
            self.next_button.emit('clicked')
        
        if keyname == 'Left':
            self.prev_button.emit('clicked')
        
            
    def next(self, *args, **kwargs):
        self.next_button.emit("clicked")

    def prev(self, *args, **kwargs):
        self.prev_button.emit('clicked')
        
    def start(self,*args):
        # self.play_thread_id = None
        self.tags = {}
        gc.collect()
        uri = self.filename
        if os.path.isfile(self.filename):
            self.filename = os.path.realpath(self.filename)
            uri = "file://" + urllib.quote(self.filename)
            # print "QUOTED:%s" % urllib.quote(self.filename);
        uri = uri.replace("\\'","%27")
        uri = uri.replace("'","%27")
        if uri == "":
            print "empty uri"
            return;
        print "playing uri:",uri
        self.player.set_state(STOPPED)
        self.player.set_property("uri", uri)
        self.player.set_property("volume",self.volume)
        self.player.set_state(PLAYING)
        self.hide_window_timeout = gobject.timeout_add(1000, self.hide_window)
        self.emit('state-changed', PLAYING)
        self.playingState = self.player.get_state()[1]
        try:
            self.dur_int = self.player.query_duration(self.time_format, None)[0]
        except gst.QueryError, e:
            print "gst.QueryError:",e
            self.dur_int = 0
        # self.play_thread_id = thread.start_new_thread(self.play_thread, ())
        # gc.collect()
        self.update_time()


    def stop(self):
        self.player.set_state(STOPPED)
        
        
    def set_volume(self,widget,value):
        self.volume = value
        print "set_volume:",self.volume
        self.player.set_property("volume",self.volume)

    def hide_window(self):
        gtk.gdk.threads_enter()
        self.window.hide()
        gtk.gdk.threads_leave()
        print "HIDE WINDOW"

        
    def convert_ns(self, time_int):
        time_int = time_int / 1000000000

        _hours = time_int / 3600
        time_int = time_int - (_hours * 3600)
        _mins = time_int / 60
        time_int = time_int - (_mins * 60)
        _secs = time_int
        
        if _hours:
            return "%d:%02d:%02d" % (_hours, _mins, _secs)

        if _mins:
            return "%d:%02d" % (_mins, _secs)

        return "0:%02d" % (_secs)

        

    def update_time(self):
        #if self.playingState != PLAYING :
        #    print "update_time:NOT PLAYING"
        #    return True

        # print 'update_time';
        try:
            dur_int = self.player.query_duration(self.time_format, None)[0]
            dur_str = self.convert_ns(dur_int)
            self.dur_int = dur_int
        except:
            return True
        
        try:
            pos_int = self.player.query_position(self.time_format, None)[0]
        except:
            pos_int = 0
            
        pos_str = self.convert_ns(pos_int)
        left_int = (dur_int - pos_int)
        left_str = self.convert_ns(left_int)
        decimal = float(pos_int) / dur_int
        percent = "%.2f%%" % (decimal * 100)
        try:
            # print pos_int, dur_int, left_int, decimal, pos_str, dur_str, left_str, percent
            self.pos_int = pos_int
            self.left_int = left_int
            self.emit('time-status', pos_int, dur_int, left_int, decimal, pos_str, dur_str, left_str, percent)
            self.pos_data = {
                "pos_str": pos_str, 
                "dur_str": dur_str, 
                "left_str": left_str,
                "percent": percent,
                "pos_int": pos_int,
                "dur_int": dur_int,
                "left_int": left_int,
                "decimal": decimal
            }
        except TypeError, e:
            print "TypeError:",e
        
        return True

    
        
    def pause(self, *args):
        self.playingState = self.player.get_state()[1]
        if self.playingState == STOPPED:
            self.start()
        elif self.playingState == PLAYING:
            self.player.set_state(PAUSED)
        elif self.playingState == PAUSED:
            self.player.set_state(PLAYING)
            
        self.playingState = self.player.get_state()[1]
        self.emit('state-changed', self.playingState)
        self.update_time()

    
    def on_message(self, bus, message):
        t = message.type
        # print "on_message:",t
        if t == gst.MESSAGE_EOS:
            print "END OF STREAM"
            # self.play_thread_id = None
            self.player.set_state(STOPPED)
            self.emit('end-of-stream')
        elif t == gst.MESSAGE_ERROR:
            # self.play_thread_id = None
            self.player.set_state(STOPPED)
            err, debug = message.parse_error()
            print "Error: '%s'" % err, "debug: '%s'" % debug
            if err == 'Resource not found.':
                print "RETURNING"
                return
            self.emit('error', err, debug)
        elif t == gst.MESSAGE_TAG:
            for key in message.parse_tag().keys():
                msg = message.structure[key]
                if isinstance(msg, (gst.Date, gst.DateTime)):
                    self.tags[key] = "%s" % msg
                elif key not in ('image','private-id3v2-frame', 'preview-image',
                                 'private-qt-tag'):
                    print "tags[%s]=%s" % (key, msg )
                    self.tags[key] = "%s" % msg
                else:
                    print "tags[%s]=%s" % (key,"[Binary]")
                    data = {}
                    if isinstance(msg, list):
                        for i, v in enumerate(msg):
                            data[i] = base64.b64encode(msg[i])
                    elif isinstance(msg, dict):
                        for k, v in enumerate(msg):
                            data[k] = base64.b64encode(msg[k])
                    else:
                        print "%s" % msg[0:10]
                        data = base64.b64encode(msg)
                    self.tags[key] = data
                    print self.tags[key]

                self.emit('tag-received', key, message.structure[key])
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        message_name = message.structure.get_name()
        print "on_sync_message:",message_name
        
        if message_name == "prepare-xwindow-id":
            # self.window.show_now()
            # self.window.set_decorated(True)
            gobject.source_remove(self.hide_window_timeout)
            self.imagesink = message.src
            self.imagesink.set_property("force-aspect-ratio", True)
            self.imagesink.set_xwindow_id(self.movie_window.window.xid)
            
            gobject.idle_add(self.window.show)
            if self.fullscreen:
                gobject.idle_add(self.window.fullscreen)
            # self.window.show()
            gobject.idle_add(self.emit,'show-window')
        elif message_name == 'missing-plugin':
            print "MISSING PLUGGIN"
            # self.play_thread_id = None
            # self.player.set_state(STOPPED)
            self.emit('missing-plugin')

            
    def control_seek(self,w,seek):
        print "control_seek:",seek
        self.seek(seek)
        
    
    def seek_ns(self,ns):
        print "SEEK_NS:",ns
        ns = int(ns)
        print "SEEK_NS:",ns
        self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, ns)
        self.update_time()
    
    def seek(self, string):
        if self.pos_int <= 0:
            print "self.pos_int <= 0"
            return
        if self.seek_locked:
            return
        self.seek_locked = True
        
        # print "player.seek:",string
        string = str(string)
        string = string.strip()
        firstChar = string[0]
        lastChar = string[-1]
        seek_ns = None
        
        if firstChar in ('+','-'):
            # skip ahead x xeconds
            skip_second = int(string[1:]) * 1000000000
            if firstChar == '+':
                seek_ns = self.pos_int + skip_second
            else:
                seek_ns = self.pos_int - skip_second
        elif lastChar == '%':
            seek_ns = int(float(string[0:-1]) * 0.01 * self.dur_int)
        else:
            seek_ns = int(string) * 1000000000
        
        #if not seek_ns:
        #    self.seek_locked = False
        #    return
        
        if seek_ns < 0:
            seek_ns = 0
        elif seek_ns > self.dur_int:
            self.seek_locked = False
            return
        
        try:
            self.player.seek_simple(self.time_format, gst.SEEK_FLAG_FLUSH, seek_ns)
        except:
            print "ERROR SEEKING"
            self.seek_locked = False
            return
            
        self.pos_int = seek_ns
        print "SEEK_NS:",seek_ns
        """
        left_int = (self.dur_int - seek_ns)
        pos_str = self.convert_ns(seek_ns)
        dur_str = self.convert_ns(self.dur_int)
        left_str = self.convert_ns(left_int)
        decimal = float(seek_ns) / self.dur_int
        percent = "%.2f%%" % (decimal * 100)
        try:
            self.emit('time-status', seek_ns, self.dur_int, left_int, decimal, pos_str, dur_str, left_str, percent)
        except TypeError, e:
            print "TypeError:",e
        """
        self.seek_locked = False

    def signal_handler(self, sig_id, frame):
        # We receive different signals depend on if
        # we have more data in the buffer to interpret
        if sig_id == signal.SIGUSR1:
            print "SIGUSR1"
            self.emit('SIGUSR1-received')
        elif sig_id == signal.SIGUSR2:
            print "SIGUSR2"
            self.emit('SIGUSR2-received')
    
    def on_time_status(self, player, pos_int, dur_int, left_int, decimal, pos_str, dur_str, left_str, percent):
        if not self.showingControls:
            return
        # print s
        # gtk.gdk.threads_enter()
        self.timeLabel.set_text(" -%s %s/%s" % (left_str, pos_str, dur_str) )



if __name__ == '__main__':

    def next(*args):
        print "play_files"
        if len(files) == 0:
            print "done playing files"
            return
        f = files.pop(0)
        if currentFile:
            prevFiles.append(currentFile.pop())
        currentFile.append(f)
        print "f:",f
        if not f:
            print "f was empty"
            return
        player.filename = f
        player.start()
        
    def prev(*args):
        if not prevFiles:
            return
        if currentFile:
            files.insert(0,currentFile.pop())
        f = prevFiles.pop()
        currentFile.append(f)
        player.filename = f
        player.start()
        
    def status(w, *args):
        # (56525313000L, 217583333333L, 161058020333L, 0.25978696131790086, '00:56', '03:37', '02:41', '25.98%')
        # print "status:", args
        pass
    
    def error_msg(player, msg,debug):
        print "ERROR MESSAGE:", msg, ',', debug
        if not os.path.isfile(player.filename):
            player.emit('end-of-stream')

    def on_menuitem_clicked(item):
        # CLICKED:(<gtk.ImageMenuItem object at 0x8f6bb44 (GtkImageMenuItem at 0x8bc40f8)>,) {}
        label = item.get_label()
        if label == 'Pause':
            
            player.pause()
        elif label == 'Play':
            player.pause()
        elif label == 'Next':
            next()
        elif label == 'Prev':
            prev()
        elif label == 'Quit':
            gtk_main_quit()
        
        print "CLICKED:%s " % (item.get_label())

    def on_playing_state_changed(p, state):
        # (<Player object at 0x975f6bc (__main__+Player at 0x97be220)>, <enum GST_STATE_PAUSED of type GstState>)
        if state == gst.STATE_PLAYING:
            play_pause_item.set_label('Pause')
            play_pause_item.set_image(pause_img)
        elif state == gst.STATE_PAUSED:
            play_pause_item.set_label('Play')
            play_pause_item.set_image(play_img)

        
        

    import appindicator, random
    ind = appindicator.Indicator("fmp-player-cmd-indicator",
                                       gtk.STOCK_CDROM,
                                       appindicator.CATEGORY_APPLICATION_STATUS)


    pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
    play_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PLAY, gtk.ICON_SIZE_BUTTON)
    
    menu = gtk.Menu()

    play_pause_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PAUSE, gtk.ICON_SIZE_BUTTON)
    play_pause_item = gtk.ImageMenuItem("Pause")
    play_pause_item.set_image(play_pause_img)
    play_pause_item.connect("activate", on_menuitem_clicked)
    play_pause_item.show()
    menu.append(play_pause_item)

    next_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_NEXT, gtk.ICON_SIZE_BUTTON)
    next_item = gtk.ImageMenuItem("Next")
    next_item.set_image(next_img)
    next_item.connect("activate", on_menuitem_clicked)
    next_item.show()
    menu.append(next_item)

    prev_img = gtk.image_new_from_stock(gtk.STOCK_MEDIA_PREVIOUS, gtk.ICON_SIZE_BUTTON)
    prev_item = gtk.ImageMenuItem("Prev")
    prev_item.set_image(next_img)
    prev_item.connect("activate", on_menuitem_clicked)
    prev_item.show()
    menu.append(prev_item)

    quit_item = gtk.ImageMenuItem("Quit")
    quit_item.connect("activate", on_menuitem_clicked)
    img = gtk.image_new_from_stock(gtk.STOCK_QUIT, gtk.ICON_SIZE_BUTTON)
    quit_item.set_image(img)
    quit_item.show()
    menu.append(quit_item)

    ind.set_menu(menu)
    ind.set_status(appindicator.STATUS_ACTIVE)
    
    prevFiles = []
    currentFile = []
    files = []
    args = sys.argv[1:]
    cwd = os.getcwd()
    shuffle = False

    for arg in args:
        if os.path.exists(arg):
            print "file:%s" % arg
            files.append(arg)
        elif arg in ('-s','--shuffle','-shuffle'):
            shuffle = True
            
    
    if shuffle:
        print "SHUFFLE"
        random.shuffle(files)

    player = Player()
    player.connect('end-of-stream', next)
    player.connect('time-status', status)
    player.connect('error', error_msg)
    ind.connect('scroll-event', player.ind_on_scroll)
    player.connect('state-changed', on_playing_state_changed)

    player.next_button.connect('clicked',next)
    player.prev_button.connect('clicked',prev)
    gobject.idle_add(next)
    while gtk.events_pending(): gtk.main_iteration(False)
    gtk.main()


