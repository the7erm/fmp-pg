
from fmp_utils.player import Player, Playlist, TrayIcon, Gdk, ActionTracker, \
                             Wnck, Gtk
from fmp_utils import picker
from fmp_utils.jobs import jobs

from pprint import pprint, pformat
from fmp_utils.db_session import Session, session_scope
from fmp_utils.misc import session_add
from fmp_utils.constants import CONFIG_DIR
import os
import sys
import json
from subprocess import check_output
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject

GObject.threads_init()


class WnckTracker:
    def __init__(self):
        Gtk.main_iteration()
        self.wnck_file = os.path.join(CONFIG_DIR, "wnck.json")
        self.geometry = None
        self.window = None
        self.timeout = None
        self.locked = False

    def check_window(self):
        Gtk.main_iteration()
        self.screen = Wnck.Screen.get_default()
        self.screen.force_update()
        self.windows = self.screen.get_windows()
        self.workspaces = self.screen.get_workspaces()

        for w in self.windows:
            name = w.get_class_instance_name()
            if "fmp.py" not in name:
                continue
            self.window = w
            self.window.connect("geometry-changed", self.on_geometry_changed)
            self.window.connect("state-changed", self.on_state_change)
            self.window.connect("workspace-changed", self.on_state_change)

    def on_geometry_changed(self, *args, **kwargs):
        # print("on_geometry_changed:", args, kwargs)
        if self.timeout:
            GObject.source_remove(self.timeout)
            self.timeout = False
        self.timeout = GObject.timeout_add_seconds(1, self.write_once)

    def on_state_change(self, *args, **kwargs):
        # print ("on_state_change")
        if self.timeout:
            GObject.source_remove(self.timeout)
            self.timeout = False
        self.timeout = GObject.timeout_add_seconds(1, self.write_once)

    def write_once(self):
        GObject.source_remove(self.timeout)
        self.timeout = False
        print("+"*100)
        print("write_once")
        self.write_wnck_file()
        return True

    def write_wnck_file(self, *args, **kwargs):
        print ("write_wnck_file")
        if self.locked:
            self.timeout = GObject.timeout_add_seconds(1, self.write_once)
            return
        self.locked = True
        if self.window is None:
            self.check_window()
        if self.window is None:
            self.locked = False
            return False

        self.workspace = self.window.get_workspace()
        spec = {
            "client_window_geometry": self.window.get_client_window_geometry(),
            "geometry": self.window.get_geometry(),
            "is_above": self.window.is_above(),
            "is_below": self.window.is_below(),
            "is_fullscreen": self.window.is_fullscreen(),
            "is_in_viewport": self.window.is_in_viewport(self.workspace),
            "is_maximized": self.window.is_maximized(),
            "is_maximized_horizontally": self.window.is_maximized_horizontally(),
            "is_maximized_vertically": self.window.is_maximized_vertically(),
            "is_minimized": self.window.is_minimized(),
            "is_pinned": self.window.is_pinned(),
            "is_shaded": self.window.is_shaded(),
            "is_skip_pager": self.window.is_skip_pager(),
            "is_skip_tasklist": self.window.is_skip_tasklist(),
            "is_sticky": self.window.is_sticky(),
            "is_visible_on_workspace": self.window.is_visible_on_workspace(self.workspace),
            "sort_order": self.window.get_sort_order(),
            "workspace": {
                "number": self.workspace.get_number(),
                "name": self.workspace.get_name()
            },
        }
        pprint(spec)
        with open(self.wnck_file, 'w') as fp:
            fp.write(json.dumps(spec, sort_keys=True,
                     indent=4, separators=(',', ': ')))
        self.locked = False
        return False

    def restore_window(self):
        if not os.path.exists(self.wnck_file):
            return
        self.locked = True
        try:
            with open(self.wnck_file, "r") as fp:

                data = json.loads(fp.read())
                self.check_window()
                print ("RESTORE:", data)
                pprint(dir(Wnck.WindowMoveResizeMask))

                self.window.set_geometry(Wnck.WindowGravity.STATIC,
                                         Wnck.WindowMoveResizeMask.X |
                                         Wnck.WindowMoveResizeMask.Y |
                                         Wnck.WindowMoveResizeMask.WIDTH |
                                         Wnck.WindowMoveResizeMask.HEIGHT,
                                         *data["geometry"])

                if data.get("is_above", False):
                    self.window.make_above()

                if data.get("is_below", False):
                    self.window.make_below()

                self.window.set_fullscreen(data.get("is_fullscreen", False))

                if data.get("is_maximized", False):
                    self.window.maximize()

                if data.get("is_maximized_horizontally", False):
                    self.window.maximize_horizontally()

                if data.get("is_maximized_vertically", False):
                    self.window.maximize_vertically()

                if data.get("is_minimized", False):
                    self.window.minimize()

                if data.get("is_pinned", False):
                    self.window.pin()

                if data.get("is_shaded", False):
                    self.window.shade()

                if data.get("is_sticky", False):
                    self.window.stick()

                """
                 'is_above': False,
                 'is_below': False,
                 'is_fullscreen': False,
                 'is_in_viewport': True,
                 'is_maximized': False,
                 'is_maximized_horizontally': False,
                 'is_maximized_vertically': False,
                 'is_minimized': True,
                 'is_pinned': False,
                 'is_shaded': False,
                 'is_skip_pager': False,
                 'is_skip_tasklist': False,
                 'is_sticky': False,
                 'is_visible_on_workspace': False,
                 'sort_order': 13,
                """

                workspace = data.get("workspace", {})
                workspace_number = int(workspace.get("number", 0))
                workspace_name = workspace.get("name", "")
                for workspace in self.workspaces:
                    if workspace.get_number() == workspace_number:
                        self.window.move_to_workspace(workspace)
                        break
        except:
            print ("WRITE ERROR")
        self.locked = False

wnck_tracker = WnckTracker()


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
        ips.sort()
        return "IP_ADDRESSES = %s\n" % ips

    def write_ip_address_file(self, ip_data):
        wnck_tracker.write_wnck_file()
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
            self.files = picker.get_preload(remove_item=False)
        self.preload = picker.get_preload(remove_item=False)
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