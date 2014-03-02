#!/usr/bin/env python2
# lib/history_dialog.py -- Dialog that shows history for a song.
#    Copyright (C) 2013 Eugene Miller <theerm@gmail.com>
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
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307 

from __init__ import *
import gtk
import datetime
import time
import math
import gobject
import pytz

from lib.preload import convert_delta_to_str

"""
SELECT * FROM user_history WHERE fid = 22833;
 uhid | uid |  fid  | percent_played |          time_played          | date_played 
------+-----+-------+----------------+-------------------------------+-------------
 1904 |   1 | 22833 |             99 | 2012-09-11 13:47:27.922461-06 | 2012-09-11
  839 |   1 | 22833 |             57 | 2012-09-10 20:26:34.474485-06 | 2012-09-10

"""

EPOCH = datetime.datetime(1970,1,1, tzinfo=pytz.UTC)

class History_Tree(gtk.TreeView):
    def __init__(self, fid=None, uid=None):
        self.fid = fid
        self.uid = uid
        gtk.TreeView.__init__(self)
        self.store = gtk.ListStore(
            int, # fid
            int, # uid
            str, # uname
            int, # percent_played
            str, # time_played
            int, # time_played_int
            str, # time between
            int, # rating
            int, # score
            float # true_score
        )
        self.set_model(self.store)
        self.set_headers_visible(True)
        self.append_simple_col("User",2)
        self.append_simple_col("Rating",7)
        self.append_simple_col("Score",8)
        self.append_simple_col("True Score",9)
        self.append_simple_col("Percent Played",3)
        self.append_simple_col("Time Played", 4, 5)
        self.append_simple_col("Time Between",6)

        # SELECT uh.*, age(uh.time_played, lag(time_played, 1, (SELECT max(time_played) FROM user_history uhl WHERE uhl.id = uh.id AND uhl.uid = uh.uid AND uhl.time_played < uh.time_played )) OVER ( PARTITION BY time_played ORDER BY time_played DESC )) AS time_between FROM user_history uh WHERE uh.id = 21067 AND uh.uid = 1 ORDER BY time_played DESC;

        # SELECT u.*, uh.*, age(uh.time_played, lag(time_played, 1, (SELECT max(time_played) FROM user_history uhl WHERE uhl.id_type = uh.id_type AND uhl.id = uh.id AND uhl.uid = uh.uid AND uhl.time_played < uh.time_played )) OVER ( PARTITION BY time_played ORDER BY time_played DESC )) AS time_between FROM users u, user_history uh WHERE u.uid = uh.uid AND uh.id = %s AND uh.id_type = 'f' AND u.uid IN (SELECT uid FROM users WHERE listening = true) ORDER BY admin DESC, uname, time_played DESC;
        
        
        # self.query = pg_cur.mogrify("SELECT * FROM users u, user_history uh WHERE u.uid = uh.uid AND uh.id = %s AND uh.id_type = 'f' AND u.uid IN (SELECT uid FROM users WHERE listening = true) ORDER BY admin DESC, uname, time_played DESC", (fid,))


        self.query = pg_cur.mogrify("""SELECT u.*, uh.*, 
                                              age(uh.time_played, 
                                                  lag(time_played, 1, 
                                                      (
                                                        SELECT max(time_played) 
                                                        FROM user_history uhl 
                                                        WHERE uhl.id_type = uh.id_type AND 
                                                              uhl.id = uh.id AND 
                                                              uhl.uid = uh.uid AND 
                                                              uhl.time_played < uh.time_played 
                                                     )
                                                  ) OVER (
                                                    PARTITION BY time_played 
                                                    ORDER BY time_played DESC )
                                                  ) AS time_between 
                                        FROM users u, user_history uh 
                                        WHERE u.uid = uh.uid AND 
                                              uh.id = %s AND 
                                              uh.id_type = 'f' AND 
                                              u.uid IN (
                                                SELECT uid 
                                                FROM users 
                                                WHERE listening = true)
                                                ORDER BY admin DESC, 
                                                         uname, 
                                                         time_played DESC""", (fid,))

        self.populate_liststore()

        gobject.timeout_add(10000, self.populate_liststore)
        

    def populate_liststore(self):
        self.store.clear()
        history = get_results_assoc(self.query)
        low = datetime.datetime.now()
        high = datetime.datetime.now()
        for i, h in enumerate(history):
            h = dict(h)
            uname = h['uname']
            if uname == None:
                uname = ""

            perc = "%s" % h['percent_played']
            if perc == "-1":
                perc = "Unknown"
            elif perc == "-2":
                perc = "Unknown - mp3 player"

            """
            self.store = gtk.ListStore(
                int, # fid
                int, # uid
                str, # uname
                int, # percent_played
                str, # time_played
                int, # time_played_int
                str, # time between
                int, # rating
                int, # score
                float # true_score
            ) """
            # uname, time_played, time_played_int, percent, time_between, int_time_between
            if  not isinstance(h['true_score'], float):
                h['true_score'] = 0

            if isinstance(h['time_played'], datetime.datetime):
                h['time_played_int'] = (h['time_played'] - EPOCH).total_seconds()
                h['time_played'] = h['time_played'].strftime("%c")
            else:
                h['time_played'] = 'Never'
                h['time_played_int'] = 0

            if isinstance(h['time_between'], datetime.timedelta):
                h['time_between'] = convert_delta_to_str(h['time_between'])
            else:
                h['time_between'] = ""

            try:
                self.store.append([
                    h['id'],
                    h['uid'],
                    uname, # uname
                    h['percent_played'],
                    h['time_played'], # time_played
                    h['time_played_int'], # time_played_int
                    h['time_between'], # time_between
                    h['rating'],
                    h['score'],
                    h['true_score']
                ])
            except AttributeError,err:
                print "AttributeError:",err
                print "value:"
                print h
                pp.pprint(h)
            except TypeError, err:
                print "TypeError:",err
                print h
                for k in h.keys():
                    print "k[%s]=%s" % (k, h[k])
                pp.pprint(h)
        return True

    def append_simple_col(self, text, col_id, sort_col=None):
        col = gtk.TreeViewColumn(text, gtk.CellRendererText(), text=col_id)
        if sort_col is None:
            sort_col = col_id
        col.set_sort_column_id(sort_col)
        self.append_column(col)

    def timeBetween(self, lowDateTime, highDateTime):
        if lowDateTime == None or highDateTime == None:
            return (0, '')

        string = '';
        try:
            low = int(time.mktime(lowDateTime.timetuple()))
        except:
            low = 0
            
        high = int(time.mktime(highDateTime.timetuple()))
        if low <= 0:
            return (0,'')
        
        mmin = 60
        hr = mmin * 60
        d = hr * 24
        wk = d * 7
        yr = wk * 52
        month = math.floor(yr / 12)

        diff = high - low
        diff_total = high - low

        years = math.floor(diff / yr)
        diff = diff - (years * yr)
        months = math.floor(diff / month)
        diff = diff - (months * month)
        weeks = math.floor(diff / wk)
        diff = diff - (weeks * wk)
        days = math.floor(diff / d)
        diff = diff - (days * d)
        hours = math.floor(diff / hr)
        diff = diff - (hours * hr)
        mins = math.floor(diff / mmin)
        diff = diff - (mins * mmin)
        secs = diff

        if (years > 0):
            if years > 1:
                string += "%d years" % years
            else:
                string += "%d year" % years

        if (months > 0):
            if months > 1:
                string += " %d months" % months
            else:
                string += " %d month" % months

        if (weeks > 0):
            if weeks > 1:
                string += " %d weeks" % weeks
            else:
                string += " %d week" % weeks

        if (days > 0):
            if days > 1:
                string += " %d days" % days
            else:
                string += " %d day" % days
        
        string = string.strip()
        if (string):
            return (diff_total, string)

        if (hours > 0):
            string += " %d:" % hours

        if string:
            string += "%02d:%02d" % (mins, secs)
        else:
            string += "%d:%02d" % (mins, secs)

        string = string.strip()
        if string == "0:00":
            string = ""

        return (diff_total, string)
    
if __name__ == "__main__":
    # SELECT * FROM user_history WHERE fid = 22833;
    w = gtk.Window()
    w.set_position(gtk.WIN_POS_CENTER)
    w.connect('delete-event', gtk_main_quit)
    t = History_Tree(fid=22833)
    w.add(t)

    w.show_all()
    gtk.main()


