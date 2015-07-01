#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# __init__.py -- config
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

import os
import cfg_wrapper
from create_salt import create_salt

DEFAULTS = {
    "Netcasts": {
        "cue": False,
    },
    "password_salt": {
        "salt" : "",
    },
    "Misc": {
        "bedtime_mode": False
    },
    "postgres" : {
        "host": "127.0.0.1",
        "port": "5432",
        "username": "",
        "password": "",
        "database": "fmp"
    },
}

home = os.path.expanduser('~')
config_dir = os.path.join(home, ".fmp")
config_file = os.path.join(config_dir, "config")
cache_dir = os.path.join(config_dir,"cache")

if not os.path.isdir(config_dir):
    os.mkdir(config_dir, 0775)

if not os.path.isdir(cache_dir):
    os.mkdir(cache_dir, 0775)

cfg = cfg_wrapper.ConfigWrapper(config_file, DEFAULTS)

salt = cfg.get('password_salt', 'salt', create_salt(), str)
print "salt:", salt

cfg.set('password_salt', 'salt', salt, str)
