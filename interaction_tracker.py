import time
from satellite_player import STOPPED, PAUSED, PLAYING
from pprint import pprint, pformat
import sys
from config_dir import config_dir
import os

debug = True

def _print(*args, **kwargs):
    if debug:
        for arg in args:
            print arg,
        if kwargs != {}:
            print kwargs
        print
        sys.stdout.flush()

def _pprint(*args, **kwargs):
    if debug:
        pprint(*args, **kwargs)
        sys.stdout.flush()

class InteractionTracker:
    def __init__(self, mode, player):
        self.mode = mode
        self.last_interaction = 0
        self.priority = self.mode
        self.config_file = os.path.join(config_dir, 
                                        "last-interaction-%s" % mode)
        self.read_last_interaction()

        self.player = player
        self.player.connect('state-changed', self.mark_interaction)

    def read_last_interaction(self):
        if not os.path.exists(self.config_file):
            return

        last_interaction = 0
        with open(self.config_file, 'r') as fp:
            try:
                last_interaction = float(fp.read())
            except:
                pass

        _print("last_interaction:", last_interaction)
        self.last_interaction = last_interaction

    def get_time(self, adjust=True):
        local_offset = time.timezone
        if time.daylight:
            local_offset = time.altzone
        _time = time.time()+local_offset
        if adjust and not self.system_clock_ok():
            _time = self.last_interaction + _time
        return _time

    def mark_interaction(self, *args, **kwargs):
        self.last_interaction = self.get_time()
        self.write_last_interaction()

    def write_last_interaction(self):
        _print ("write_last_interaction:", self.last_interaction)
        with open(self.config_file, 'w') as fp:
            fp.write("%s" % self.last_interaction)
            os.fsync(fp.fileno())

    def system_clock_ok(self):
        return self.time_is_ok(self.get_time(adjust=False))

    def time_is_ok(self, _time):
        return _time > (60 * 60 * 24 * 365)

    def get_priority(self, remote_last_interaction, remote_playing_state):

        remote_last_interaction = float(remote_last_interaction)
        
        if self.system_clock_ok():
            now = self.get_time(adjust=False)
            if not self.time_is_ok(remote_last_interaction):
                remote_last_interaction = (now - remote_last_interaction)
            elif remote_last_interaction > now:
                remote_last_interaction = now + 1

        if self.player.playingState == PLAYING:
            _print("PRIORITY self.mode:", self.mode.upper())
            return self.mode

        if remote_playing_state == 'PLAYING' and self.mode == 'client':
            _print("PRIORITY SERVER it's PLAYING")
            self.priority = 'server'
            return self.priority

        if remote_playing_state == 'PLAYING' and self.mode == 'server':
            _print("PRIORITY CLIENT it's PLAYING")
            self.priority = 'client'
            return self.priority

        if self.last_interaction == remote_last_interaction:
            _print("PRIORITY last_interaction == remote_last_interaction so "
                   "SERVER")
            self.priority = 'server'
            return self.priority

        if self.last_interaction > remote_last_interaction:
            _print("PRIORITY self.last_interaction > remote_last_interaction "
                   "self.mode", self.mode.upper())
            self.priority = self.mode
            return self.mode

        if self.last_interaction < remote_last_interaction:
            if self.mode == 'server':
                _print("PRIORITY "
                       "self.last_interaction < remote_last_interaction "
                       "self.mode == 'server' CLIENT")
                self.priority = 'client'
                return self.priority
            else:
                _print("PRIORITY "
                       "self.last_interaction < remote_last_interaction "
                       "self.mode != 'server' SERVER")
                self.priority = 'server'
                return self.priority

        _print("ERROR priority not determined using self.mode:", self.mode)
        return self.mode




