#!/usr/bin/env python
# /lib/__init__.py -- Initialize fmp
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

import psycopg2
import psycopg2.extras
import sys
import os
import pprint
import ConfigParser
import gc
import time
import random
import hashlib

pp = pprint.PrettyPrinter(depth=6)
sys.path.append(sys.path[0]+'/lib/')

home = os.path.expanduser('~')
config_dir = home+"/.fmp"
config_file = config_dir+"/config"
cache_dir = config_dir+"/cache"

if not os.path.isdir(config_dir):
	os.mkdir(config_dir,0775)

if not os.path.isdir(cache_dir):
	os.mkdir(cache_dir,0775)

cfg = ConfigParser.ConfigParser()
cfg.read(config_file)

def create_salt(cfg, config_file):
    random_string = "%s%s" % (random.random(),time.time())
    salt = hashlib.sha256(random_string).hexdigest()
    try:
        cfg.add_section('password_salt')
    except ConfigParser.DuplicateSectionError:
        pass
    cfg.set("password_salt","salt",salt)
    with open(config_file, 'w') as fp:
        cfg.write(fp)
        fp.flush()
    return salt

pg_conn = psycopg2.connect("dbname=%s user=%s password=%s host=%s" % (
                            cfg.get('postgres','database'), 
                            cfg.get('postgres','username'), 
                            cfg.get('postgres','password'), 
                            cfg.get('postgres','host')))

try:
    salt = cfg.get('password_salt','salt')
except ConfigParser.NoSectionError:
    salt = create_salt(cfg, config_file)

if not salt:
    salt = create_salt(cfg, config_file)


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

DEFAULT_RATING = 6
DEFAULT_SCORE = 5
DEFAULT_PERCENT_PLAYED = 50.0
DEFAULT_TRUE_SCORE = (((DEFAULT_RATING * 2 * 10.0) + (DEFAULT_SCORE * 10.0) + 
                        DEFAULT_PERCENT_PLAYED) / 3)

MAX_TRUE_SCORE = (((6 * 2 * 10.0) + (6 * 10.0) + 
                    100.0) / 3)

print "IMPORTED __init__"