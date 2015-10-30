#!/usr/bin/env python3

from setproctitle import setproctitle
setproctitle("fmp.py")

import fmp_utils
from fmp_utils.player import Player, Gtk
from fmp_utils.fmp_playlist import FmpPlaylist
from fmp_utils import picker
import cherry_py_server.server as server
from threading import Thread

def start_server():
    print("start_server")

server_thread = Thread(target=server.cherry_py_worker)
server_thread.start()

fmp_utils.fmp_playlist.setproctitle = setproctitle
playlist = FmpPlaylist(server=server)


Gtk.main()