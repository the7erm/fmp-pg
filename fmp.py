#!/usr/bin/env python3

from setproctitle import setproctitle
setproctitle("fmp.py")

import sys
import fmp_utils
from fmp_utils.player import Player, Gtk
from fmp_utils.fmp_playlist import FmpPlaylist
from fmp_utils import picker
from fmp_utils.first_run import first_run
from server import server
from threading import Thread
fmp_utils.fmp_playlist.setproctitle = setproctitle
from subprocess import Popen

server_thread = Thread(target=server.cherry_py_worker)
server_thread.start()

if first_run:
    print("FIRST RUN", first_run)
    Popen(["xdg-open", "http://localhost:5050/#/setup"])
else:
    from models.base import Base
    from fmp_utils.db_session import create_all
    create_all(Base)

playlist = FmpPlaylist(server=server, first_run=first_run.first_run)

Gtk.main()