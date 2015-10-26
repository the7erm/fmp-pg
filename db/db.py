#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# __init__.py -- fobj inits
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

print "import db.py"

import psycopg2
import psycopg2.extras
from config import cfg
from pprint import pprint
import sys
from log_class import outer_applicator

pg_conn = psycopg2.connect("dbname=%s user=%s password=%s host=%s" % (
                            cfg.get('postgres','database', 'fmp', str), 
                            cfg.get('postgres','username', '', str), 
                            cfg.get('postgres','password', '', str), 
                            cfg.get('postgres','host', '127.0.0.1', str)),
                            cursor_factory=psycopg2.extras.DictCursor)

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

def execute(cur, sql, args=None):
    cur.execute('COMMIT;')
    outer_applicator(cur.execute, sql, args)
    pg_conn.commit()

def get_results_assoc(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    res = cur.fetchall()
    return res

def get_results_assoc_dict(sql, args=None):
    res = get_results_assoc(sql, args)
    res_dict = []
    for r in res:
        res_dict.append(dict(r))
    return res_dict

def get_assoc(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    res = cur.fetchone()
    return res

def get_assoc_dict(sql, args=None):
    res = get_assoc(sql, args)
    if not res:
        res = {}
    return dict(res)

def query(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    return cur

def mogrify(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # print "QUERY:", query
    # print "ARGS:", 
    # pprint(args)
    return cur.mogrify(sql, args)
