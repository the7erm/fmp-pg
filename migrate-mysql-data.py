#!/usr/bin/env python2
# migrate-mysql-data.py -- Migrate mysql data to postgres
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

from __init__ import *
import MySQLdb
import os
import datetime, time, pytz

import scanner
import file_object

file_object.pg_conn = pg_conn
file_object.pg_cur = pg_cur
file_object.get_results_assoc = get_results_assoc
file_object.get_assoc = get_assoc
file_object.query = query

tz = time.strftime("%Z", time.gmtime())
localtz = pytz.timezone(tz)

def add_tz(dt):
    if dt == None:
        return None
        # return datetime.datetime.now(localtz)
        
    print "dt:",dt
    dt = localtz.localize(dt)
    return dt

my_conn = MySQLdb.connect ("localhost", "erm", "samowen2223", "phpMUR", 3306)
my_cursor = my_conn.cursor(MySQLdb.cursors.DictCursor)


my_cursor.execute("SELECT * FROM users ORDER BY uid")
users = my_cursor.fetchall()

for myu in users:
    pgu = get_assoc("SELECT * FROM users WHERE uid = %s",(myu['uid'],))

    if pgu and (pgu['uname'] != myu['uname']):
        pgu = None
    elif not pgu:
        pgu = get_assoc("INSERT INTO users (uid, uname) VALUES(%s, %s) RETURNING *",(myu['uid'], myu['uname'],))

    if not pgu:
        pgu = get_assoc("SELECT * FROM users WHERE uname = %s",(myu['uname'],))

    if not pgu:
        pgu = get_assoc("INSERT INTO users (uname) VALUES(%s) RETURNING *",(myu['uname'],))

    my_cursor.execute("SELECT f.fid, f.filename, u.rating, u.ultp, u.score, u.perc, u.true_score FROM files f, user_song_info u WHERE u.uid = %s AND u.fid = f.fid",(myu['uid'],))
    myfiles = my_cursor.fetchall()

    for myf in myfiles:
        # if myf['rating'] == 6:
        #    print "\nskipping:%s\n" % myf['filename']
            # sys.stdout.write("-")
        #    continue
        sys.stdout.write(".")
        sys.stdout.flush()
        # print "myf:",myf
        dirname = os.path.dirname(myf['filename'])
        basename = os.path.basename(myf['filename'])
        pgf = get_assoc("SELECT fid, dir, basename FROM files WHERE dir = %s AND basename = %s",(dirname, basename))
        if not pgf:
            print "dirname:",dirname
            print "basename:",basename
            if not os.path.exists(myf['filename']):
                print "\nmissing:%s\n" % myf['filename']
                continue
            else:
                scanner.scan_file(filename=myf['filename'])
                pgf = get_assoc("SELECT fid, dir, basename FROM files WHERE dir = %s AND basename = %s",(dirname, basename))

        if not pgf:
            print "really missing:%s" % myf['filename']
            continue
            
        # print "pgf:",pgf
        pgui = get_assoc("SELECT * FROM user_song_info WHERE uid = %s AND fid = %s",(pgu['uid'], pgf['fid']))
        # print "pgui:",pgui
        if not pgui:
            # print "Before:",myf['ultp']
            myf['ultp'] = add_tz(myf['ultp'])
            # print "After:",myf['ultp']
            query = "INSERT INTO user_song_info (uid, fid, rating, score, true_score, ultp) VALUES(%s, %s, %s, %s, %s, %s) RETURNING *"
            values = (pgu['uid'], pgf['fid'], myf['rating'], myf['score'], myf['true_score'], myf['ultp'])
            print "\nquery:",pg_cur.mogrify(query, values)
            pgui = get_assoc(query, values)
            #print "pgui:",pgui






