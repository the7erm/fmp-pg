
from fmp_utils.player import Player, Playlist, TrayIcon, Gdk
from fmp_utils import picker
from fmp_utils.jobs import jobs

from pprint import pprint, pformat

class FmpPlaylist(Playlist):

    def __init__(self, *args, **kwargs):
        super(FmpPlaylist, self).__init__(*args, **kwargs)
        self.skip_countdown = 5
        self.server = kwargs.get('server')
        self.server.playlist = self
        self.files = []
        self.preload = []
        if not kwargs.get('first_run'):
            self.files = picker.get_recently_played()
            if not self.files:
                self.files = picker.get_preload()
            self.preload = picker.get_preload()

            self.set_player_uri()
            self.player.state = 'PLAYING'
            self.player.position = "%s%%" % self.files[self.index].percent_played
        self.tray_icon = TrayIcon(playlist=self)


    def init_connections(self):
        self.player.connect('time-status', self.on_time_status)

    def on_time_status(self, player, pos_data):
        # print("on_time_status:", pos_data)
        playing_item = self.files[self.index]
        playing_item.mark_as_played(**pos_data)

        skip_user_file_infos = self.do_countdown(playing_item, pos_data)
        self.server.broadcast({"time-status": pos_data})

        if self.skip_countdown == 0:
            self.skip_majority(skip_user_file_infos)
        jobs.run_next_job()

    def do_countdown(self, playing_item, pos_data):
        users = playing_item.get_users()
        skip_cnt = 0
        skip_user_file_infos = []
        for user in users:
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
        for ufi in skip_user_file_infos:
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
        self.files[self.index].clear_voted_to_skip()
        filename = self.files[self.index].filename
        print ("set_player_uri:", filename)
        # setproctitle("fmp.py %r" % filename)
        self.player.uri = filename
        self.broadcast_playing()

    def broadcast_playing(self):
        self.server.broadcast(self.json())

    def json(self):
        self.player.last_time_status['skip_countdown'] = self.skip_countdown
        return {
            'player-playing': self.files[self.index].json(),
            'time-status': self.player.last_time_status
        }

    def on_eos(self, *args, **kwargs):
        self.files[self.index].inc_score()
        super(FmpPlaylist, self).on_eos(*args, **kwargs)
        self.preload = picker.get_preload()

    def next(self, *args, **kwargs):
        self.files[self.index].deinc_score()
        super(FmpPlaylist, self).next(*args, **kwargs)

    def pause(self, *args, **kwargs):
        self.player.pause()
        self.server.broadcast({"time-status": self.player.get_time_status()})
