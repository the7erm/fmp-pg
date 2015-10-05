#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# fobjs/listener_class.py -- listeners class.
#    Copyright (C) 2015 Eugene Miller <theerm@gmail.com>
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
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from user_file_info_class import UserFileInfo, UserNetcastInfo
from utils import utcnow
from misc import _listeners, jsonize, get_users

from log_class import Log, logging
logger = logging.getLogger(__name__)

users = get_users()

class Listeners(Log):
    __name__ = 'Listeners'
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.logger = logger
        super(Listeners, self).__init__(*args, **kwargs)
        self.listeners = _listeners(kwargs.get('listeners', None))
        self.parent = kwargs.get('parent')
        self.load_user_file_info(**self.kwargs)

    def reload(self):
        self.log_debug(".reload()")
        self.listeners = _listeners()
        self.load_user_file_info(**self.kwargs)

    def load_user_file_info(self, **kwargs):
        self.user_file_info = []
        self.non_listening_user_file_info = []
        if kwargs == {}:
            kwargs = self.kwargs

        ufi_class = UserFileInfo
        if kwargs.get('eid'):
            ufi_class = UserNetcastInfo

        users = get_users()
        for l in users:
            kwargs.update(l)
            kwargs['userDbInfo'] = l
            if l.get('listening'):
                self.user_file_info.append(ufi_class(**kwargs))
            else:
                self.non_listening_user_file_info.append(ufi_class(**kwargs))

    def init_mark_as_played_sql_args(self, sql_args):
        ultp = sql_args.get('ltp', 
                            sql_args.get('now', utcnow())
                         )
        sql_args.update({
            'ultp': ultp,
            'time_played': ultp,
            'date_played': ultp.date(),
            'fid': self.parent.fid,
            'eid': self.parent.eid,
        })

    def mark_as_played(self, **sql_args):
        self.log_debug(".mark_as_played()")
        self.reload()
        self.init_mark_as_played_sql_args(sql_args)
        self.log_debug("self.user_file_info:%s" % self.user_file_info)
        if not self.user_file_info:
            self.log_debug("RELOADING")
            self.load_user_file_info(**sql_args)

        for user_file_info in self.user_file_info:
            self.log_debug(".mark_as_played() user_file_info.mark_as_played()")
            user_file_info.mark_as_played(**sql_args)
        return

    def calculate_true_score(self, *args, **sql_args):
        for user_file_info in self.user_file_info:
            user_file_info.calculate_true_score()
            

    def inc_score(self, **sql_args):
        sql_args['edited'] = sql_args.get('edited', False)
        
        down_voted = []
        for uid, vote in sql_args.get('vote_data', {}).items():
            if not vote:
                down_voted.append(uid)

        sql_args['down_voted'] = down_voted
        for user_file_info in self.user_file_info:
            if user_file_info.uid not in down_voted:
                user_file_info.inc_score(**sql_args)
            else:
                user_file_info.deinc_score(**sql_args)

    def deinc_score(self, **sql_args):
        for user_file_info in self.user_file_info:
            user_file_info.deinc_score(**sql_args)

    def majority_deinc_score(self, **sql_args):
        self.log_debug(".majority_deinc_score()")
        down_voted = []
        vote_data = sql_args.get('vote_data', {})
        self.log_debug("vote_data:%s", vote_data)
        for uid, vote in vote_data.items():
            if vote:
                down_voted.append(uid)

        sql_args['down_voted'] = down_voted
        self.log_debug("sql_args:%s", sql_args)
        for user_file_info in self.user_file_info:
            if user_file_info.uid in down_voted:
                self.log_debug("majority_deinc_score uid:%s uname:%s" % (user_file_info.uid, user_file_info.uname))
                user_file_info.deinc_score(**sql_args)

    def json(self):
        user_file_infos = []
        non_listeners_ufi = []
        for ufi in self.user_file_info:
            user_file_infos.append(ufi.json())

        for ufi in self.non_listening_user_file_info:
            non_listeners_ufi.append(ufi.json())
        
        dbInfo = {
            'listeners': user_file_infos,
            'non_listeners': non_listeners_ufi
        }
        dbInfo = jsonize(dbInfo)
        return dbInfo
