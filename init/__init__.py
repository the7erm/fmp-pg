#!/usr/bin/env python2
# init/__init.py__ -- Initialize the database, and load config
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
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


import sys
import os
additional_path = os.path.realpath(os.path.join(sys.path[0], '..'))
if additional_path not in sys.path:
    print "additional_path:",additional_path
    sys.path.append(additional_path)

import psycopg2
import psycopg2.extras
import pprint
import ConfigParser
import gc
import time
import random
import hashlib
import cfg_wrapper

from util.gtk_utils import *

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

pp = pprint.PrettyPrinter(depth=6)

home = os.path.expanduser('~')
config_dir = os.path.join(home, ".fmp")
config_file = os.path.join(config_dir, 'config')
cache_dir = os.path.join(config_dir, "cache")

if not os.path.isdir(config_dir):
	os.mkdir(config_dir, 0775)

if not os.path.isdir(cache_dir):
	os.mkdir(cache_dir, 0775)

cfg = cfg_wrapper.ConfigWrapper(config_file, DEFAULTS)

def create_salt():
    random_string = "%s%s" % (random.random(), time.time())
    salt = hashlib.sha256(random_string).hexdigest()
    return salt

pg_conn = psycopg2.connect("dbname=%s user=%s password=%s host=%s" % (
                            cfg.get('postgres','database', 'fmp', str), 
                            cfg.get('postgres','username', '', str), 
                            cfg.get('postgres','password', '', str), 
                            cfg.get('postgres','host', '127.0.0.1', str)))
salt = cfg.get('password_salt', 'salt', create_salt(), str)

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

def get_results_assoc(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(query, args)
    pg_conn.commit()
    res = cur.fetchall()
    return res

def get_assoc(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    cur.execute(query, args)
    pg_conn.commit()
    res = cur.fetchone()
    return res

def query(query, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # print cur.mogrify(query,args)
    cur.execute(query, args)
    pg_conn.commit()
    return cur

MAX_RATING = 6
MAX_SCORE = 10

DEFAULT_RATING = cfg.get('Defaults', 'rating', 6, int)
DEFAULT_SCORE = cfg.get('Defaults', 'score', 5, int)
DEFAULT_PERCENT_PLAYED = cfg.get('Defaults', 'percent_played', 50.0, float)
DEFAULT_TRUE_SCORE = (((DEFAULT_RATING * 2 * 10.0) + (DEFAULT_SCORE * 10.0) + 
                        DEFAULT_PERCENT_PLAYED) / 3)

MAX_TRUE_SCORE = (((MAX_RATING * 2 * 10.0) + (MAX_SCORE * 10.0) + 
                    100.0) / 3)

# print "IMPORTED __init__"


