
from fmp_utils.player import Player, Playlist, TrayIcon, Gdk, ActionTracker
from fmp_utils import picker
from fmp_utils.jobs import jobs

from pprint import pprint, pformat
from fmp_utils.db_session import Session, session_scope
from fmp_utils.misc import session_add
from fmp_utils.constants import CONFIG_DIR
import os
import sys
from subprocess import check_output
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject

GObject.threads_init()
class HostnameTracker:
    def __init__(self):
        self.ip_address_file = os.path.join(sys.path[0], "ip_addresses.py")
        GObject.timeout_add_seconds(30, self.check_host)
        self.check_host()

    def check_host(self):
        # print("CHECK HOST")
        file_ip_data = self.read_ip_address_file()
        current_ip_data = self.format_ip_data(check_output(["hostname","-I"]))
        # print ("self.ip_address_file:",self.ip_address_file)

        if not os.path.exists(self.ip_address_file) or \
           file_ip_data != current_ip_data:
            self.write_ip_address_file(current_ip_data)
        return True

    def format_ip_data(self, ip_data):
        ip_data = ip_data.decode("utf8")
        ip_data = ip_data.strip()
        if '"' in ip_data:
            return ""

        ips = ip_data.split(" ")
        return "IP_ADDRESSES = %s\n" % ips

    def write_ip_address_file(self, ip_data):
        with open(self.ip_address_file, 'w') as fp:
            fp.write(ip_data)

    def read_ip_address_file(self):
        if not os.path.exists(self.ip_address_file):
            return ""

        with open(self.ip_address_file, 'r') as fp:
            file_ip_data = fp.read()
        return file_ip_data

host_tracker = HostnameTracker()

import ip_addresses


class FmpActionTracker(ActionTracker):
    __name__ = "FmpActionTracker"
    def __init__(self, *args, **kwargs):
        super(FmpActionTracker, self).__init__(*args, **kwargs)
        self.tracking_file = os.path.join(CONFIG_DIR, 'last_action')
        if os.path.exists(self.tracking_file):
            with open(self.tracking_file, 'r') as fp:
                self.last_action = float(fp.read())

    def mark(self, *args, **kwargs):
        super(FmpActionTracker, self).mark(*args, **kwargs)
        with open(self.tracking_file, 'w') as fp:
            fp.write("%s" % self.last_action)

action_tracker = FmpActionTracker()

class StateKeeper:
    def __init__(self, *args, **kwargs):
        self.state = "PAUSED"
        self.state_file = os.path.join(CONFIG_DIR, "fmp-state")
        self.valid_states = ("PAUSED", "PLAYING")
        self.load()

    def load(self):
        if os.path.exists(self.state_file):
            fp = open(self.state_file, "r")
            state = fp.read().strip().upper()
            if state in self.valid_states:
                self.state = state
            fp.close()

    def set_state(self, state):
        state = state.upper()
        if state in self.valid_states:
            self.state = state
            self.save()

    def save(self):
        if self.state in self.valid_states:
            fp = open(self.state_file,"w")
            fp.write(self.state)
            fp.close()

state_keeper = StateKeeper()

class FmpPlaylist(Playlist):

    def __init__(self, *args, **kwargs):
        super(FmpPlaylist, self).__init__(*args, **kwargs)
        self.action_tracker = action_tracker
        self.player.action_tracker = action_tracker
        self.player.state_keeper = state_keeper
        self.skip_countdown = 5
        self.server = kwargs.get('server')
        self.server.playlist = self
        self.server.IP_ADDRESSES = ip_addresses.IP_ADDRESSES
        self.server.picker = picker
        self.files = []
        self.preload = []
        self.broadcast_playing_cnt = 0
        if not kwargs.get('first_run'):
            self.reset()
        self.tray_icon = TrayIcon(playlist=self)


    def init_connections(self):
        self.player.connect('time-status', self.on_time_status)

    def populate_preload(self, user_ids=[]):
        items = picker.get_preload(user_ids)
        for item in items:
            self.preload.append(item)

    def reset(self):
        print("PLAYLIST RESET")
        self.files = picker.get_recently_played(10)
        if not self.files:
            self.files = picker.get_preload()
        self.preload = picker.get_preload()
        self.index = len(self.files) - 1
        self.set_player_uri()
        self.player.state = state_keeper.state
        try:
            with session_scope() as session:
                session_add(session, self.files[self.index])
                self.player.position = "%s%%" % \
                    self.files[self.index].percent_played
        except IndexError:
            pass
        # self.player.position = "%s%%" % self.files[self.index].percent_played


    def on_time_status(self, player, pos_data):
        Gdk.threads_leave()
        # print("on_time_status:", pos_data)
        try:
            playing_item = self.files[self.index]
        except IndexError:
            jobs.run_next_job()
            return
        self.broadcast_playing_cnt += -1
        if self.player.state_string in("PLAYING", "READY"):
            playing_item.mark_as_played(**pos_data)

        skip_user_file_infos = self.do_countdown(playing_item, pos_data)
        self.server.broadcast({"time-status": pos_data})

        if self.skip_countdown == 0:
            self.skip_majority(skip_user_file_infos)
        jobs.run_next_job()
        if self.broadcast_playing_cnt <= 0:
            self.broadcast_playing()

    def do_countdown(self, playing_item, pos_data):
        with session_scope() as session:
            session_add(session, playing_item)
            users = playing_item.get_users()
            skip_cnt = 0
            skip_user_file_infos = []
            for user in users:
                session_add(session, user)
                session_add(session, playing_item)
                for ufi in playing_item.user_file_info:
                    if ufi.user_id == user.id and ufi.voted_to_skip:
                        skip_cnt += 1
                        skip_user_file_infos.append(ufi)
            len_users = len(users)
            half = len_users * 0.5

            if skip_cnt == len_users:
                self.skip_countdown = 0
            elif skip_cnt < half:
                self.skip_countdown = 5
            elif skip_cnt >= half:
                self.skip_countdown += -1

            pos_data['skip_countdown'] = self.skip_countdown
            return skip_user_file_infos

    def skip_majority(self, skip_user_file_infos):
        with session_scope() as session:
            for ufi in skip_user_file_infos:
                session_add(session, ufi)
                ufi.deinc_score()

        self.inc_index()


    def sanity_check(self, *args, **kwargs):
        last_index = len(self.files) - 1
        if len(self.preload) <= 0:
            self.preload = picker.get_preload()
        f = self.preload.pop()
        if f:
            self.files.append(f)

        super(FmpPlaylist, self).sanity_check(*args, **kwargs)

    def set_player_uri(self):
        pprint(self.files)
        try:
            self.files[self.index].clear_voted_to_skip()
        except IndexError:
            return
        filename = self.files[self.index].filename
        print ("set_player_uri:", filename)
        # setproctitle("fmp.py %r" % filename)
        self.player.uri = filename
        self.broadcast_playing()

    def broadcast_playing(self):
        self.broadcast_playing_cnt = 10
        self.server.broadcast(self.json())

    def json(self):
        self.player.last_time_status['skip_countdown'] = self.skip_countdown
        try:
            return {
                'player-playing': self.files[self.index].json(history=True),
                'time-status': self.player.last_time_status
            }
        except IndexError:
            print("IndexError")
            return {
                'player-playing': {},
                'time-status': self.player.last_time_status
            }

    def on_eos(self, *args, **kwargs):
        try:
            self.files[self.index].inc_score()
        except IndexError:
            return
        super(FmpPlaylist, self).on_eos(*args, **kwargs)
        self.preload = picker.get_preload()

    def next(self, *args, **kwargs):
        try:
            self.files[self.index].deinc_score()
        except IndexError:
            return
        super(FmpPlaylist, self).next(*args, **kwargs)

    def pause(self, *args, **kwargs):
        self.player.pause()
        self.server.broadcast({"time-status": self.player.get_time_status()})

    @property
    def last_action(self):
        return self.action_tracker.last_action