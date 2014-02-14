#!/usr/bin/env python2
# copy-to-usb.py -- main file.
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
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from lib.__init__ import *
import os
import lib.fobj as fobj
import re
import datetime
import pytz

DST_DIR = "/home/erm/btsync/phone/Music"
ACTION_FILE = os.path.join(DST_DIR, "action.log")
RATING_DATA = os.path.join(DST_DIR, "rating.data")

UTC = pytz.timezone('Etc/UTC')

def get_by_true_score(uid, true_score, limit=100):
    limit_value = "%s" % (int(limit),)
    return get_results_assoc("""SELECT u.fid, rating, true_score, ultp, dir, basename
                                FROM user_song_info u, genres g, file_genres fg,
                                     files f
                                WHERE u.uid = %s AND 
                                      u.fid = fg.fid AND 
                                      u.fid = f.fid AND
                                      g.enabled = true AND 
                                      g.gid = fg.gid AND 
                                      true_score >= %s AND
                                      basename LIKE '%%.mp3'
                                ORDER BY CASE WHEN ultp IS NULL THEN 0 ELSE 1 END, 
                                       ultp, random()
                                LIMIT """+limit_value, (uid, true_score))


"""
rating.data format
id = Integer.parseInt(m2.group(1));
id_type = m2.group(2);
basename = m2.group(4);
rating = Integer.parseInt(m2.group(3));
ratings.add(new RatingInfo(m2.group(1), m2.group(2), m2.group(4), rating));

# id id_type rating basename
# -1 f -1 Plan B2083262995.mp3

"""
rating_data_re = re.compile(r"([\-0-9]+)\ ([fe])\ ([\-0-9]+)\ (.*)")
def get_rating_data():
    rating_filename = RATING_DATA
    rating_data = {}
    if not os.path.exists(rating_filename):
        return rating_data
    with open(rating_filename, "r") as f:
        for l in f:
            print "l:",l
            m = rating_data_re.match(l)
            if m:
                _id = m.group(1)
                id_type = m.group(2)
                rating = m.group(3)
                basename = m.group(4)
                print "_id:", _id, "id_type:", id_type, "rating:", rating, "basename:", basename
                rating_data[basename] = {
                    "id" : int(_id),
                    "id_type": id_type,
                    "rating": int(rating),
                    "basename": basename
                }
        f.close()
    return rating_data
"""
String log_line = String.format("%s %s %d %d %d %f %f %s\n", tf,
                    action, item.getFid(), pos, dur, percent,
                    mStars.getRating(), item.display_name);"""
def write_rating_data(rating_data):
    fp = open(RATING_DATA, "w")
    for k, f in rating_data.iteritems():
        # print f
        line = "%s %s %s %s\n" % (f['id'], f['id_type'], f['rating'], f['basename']);
        print line,
        fp.write(line);
    fp.close()

def copy_to_usb(files): 
    rating_data = get_rating_data()
    for f in files:
        src = os.path.join(f['dir'], f['basename'])
        basename = "%s.%s.mp3" % (f['basename'], f['fid'])
        dst = os.path.join(DST_DIR, basename)
        # String s = "\\.([0-9]+)\\.([A-Za-z0-9]{1,3})$";
        print f['true_score'],src
        if not os.path.exists(dst):
            os.link(src, dst)
        copied.append(basename)
        
        rating_data[basename] = {
            "id" : f['fid'],
            "id_type": "f",
            "rating": f['rating'],
            "basename": basename
        }
    write_rating_data(rating_data)

"""
2013-07-22 02:13:40 NEXT -1 2690 2942288 0.091425 0.000000 Plan B2083262995.mp3
2013-07-22 02:13:46 RATE 21750 5553 206680 2.686762 4.000000 A W E - Trip to Italy.mp3.21750.mp3
2013-07-22 02:14:00 RATE 21750 19706 206680 9.534546 5.000000 A W E - Trip to Italy.mp3.21750.mp3
2013-07-22 02:14:51 RATE 21750 70792 206680 34.251984 4.000000 A W E - Trip to Italy.mp3.21750.mp3
2013-07-22 02:18:05 NEXT -1 2766 6474409 0.042722 0.000000 TechSNAP MP3679702350.mp3
2013-07-22 02:18:10 NEXT -1 4144 3200094 0.129496 0.000000 NPR Car Talk Podcast-2129906264.mp3
2013-07-22 02:18:12 NEXT -1 1818 4674886 0.038889 0.000000 The Linux Action Show MP32047080133.mp3
2013-07-22 02:20:08 NEXT 18535 185102 259900 71.220467 4.000000 Alanis Morisette - Thank U.mp3.18535.mp3
2013-07-22 02:23:33 COMPLETE 18174 1 100 1.000000 4.000000 Angelica - A Little Love.mp3.18174.mp3
2013-07-22 02:25:11 NEXT -1 98011 3383813 2.896466 0.000000 Triangulation-53564463.mp3
2013-07-22 02:29:24 RATE 18171 248567 296419 83.856636 3.000000 Angelica - Cover Me.mp3.18171.mp3
2013-07-22 02:29:27 RATE 18171 252093 296419 85.046165 4.000000 Angelica - Cover Me.mp3.18171.mp3
2013-07-22 02:30:12 COMPLETE 18171 1 100 1.000000 4.000000 Angelica - Cover Me.mp3.18171.mp3
2013-07-22 02:30:31 NEXT -1 1146 3383813 0.033867 0.000000 Triangulation-53564463.mp3
2013-07-22 02:31:33 COMPLETE 18171 1 100 1.000000 4.000000 Angelica - Cover Me.mp3.18171.mp3
2013-07-22 02:34:30 COMPLETE 7094 1 100 1.000000 0.000000 10. Emiliana Torrini - Beggar's Prayer.mp3.7094.mp3
2013-07-22 02:35:58 RATE 18477 88160 302297 29.163372 3.000000 Air - Once upon a time.mp3.18477.mp3
2013-07-22 02:36:11 RATE 18477 100976 302297 33.402912 4.000000 Air - Once upon a time.mp3.18477.mp3
2013-07-22 02:36:31 NEXT 18477 121086 302297 40.055309 4.000000 Air - Once upon a time.mp3.18477.mp3
2013-07-22 02:36:32 COMPLETE -1 1 100 1.000000 0.000000 hangouts_message.ogg
2013-07-22 02:39:06 RATE 18552 152525 164045 92.977539 5.000000 Anthrax - Got the Time.mp3.18552.mp3
2013-07-22 02:39:07 RATE 18552 153725 164045 93.709045 4.000000 Anthrax - Got the Time.mp3.18552.mp3

2013-07-22 02:39:24 NEXT -1 6490 1263767 0.513544 0.000000 Hacker Public Radio177655222.mp3
2013-07-22 02:42:43 NEXT 18195 73634 190074 38.739647 4.000000 Angelica - It's My Turn.mp3.18195.mp3
2013-07-22 02:42:46 NEXT     -1   2414 8071277 0.029909 0.000000 this WEEK in TECH MP3 Edition1632169355.mp3
2013-07-22 02:39:17 COMPLETE 18552 1   100     1.000000 4.000000 Anthrax - Got the Time.mp3.18552.mp3
date       time     act      fid   ?   ???     percent      rating   filename
                                               played?
"""

action_re = re.compile("([\d]{4}-[\d]{2}-[\d]{2}\ [\d]{2}\:[\d]{2}\:[\d]{2})\ "+ # date/time
                       "(NEXT|COMPLETE|RATE)\ "+ # action
                       "([\-\d]+)\ " + # fid
                       "([\d]+)\ " + # current frame?
                       "([\d]+)\ " + # total frames
                       "([\d\.]+)\ " + # percent played
                       "([\d\.]+)\ " + # rating
                       "(.*)" # filename
                      )

def parse_action_line(m, l, done):
    print m.groups()
    time_occured = UTC.localize(datetime.datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S"))
    action = m.group(2)
    fid = int(m.group(3))
    current_frame = m.group(4)
    total_frames = m.group(5)
    percent_played = float(m.group(6))
    rating = int(float(m.group(7)))
    basename = m.group(8)

    print "time_occured:", time_occured
    print "action:", action
    print "fid:", fid
    print "current_frame:", current_frame
    print "total_frames:", total_frames
    print "percent_played:", percent_played
    print "rating:", rating
    print "basename:", basename
    if fid == -1:
        done.append(l)
        return
    fileObject = None
    if action in ("COMPLETE", "RATE", "NEXT"):
        fileObject = fobj.get_fobj(fid=fid, hash=False, register_as_new=False)
    if action == "COMPLETE" and fileObject is not None:
        fileObject.ratings_and_scores.mark_as_played_for_uid(
            uid=1, percent_played=100, when=time_occured)
        fileObject.ratings_and_scores.inc_score_for_uid(uid=1, percent_played=100)
        done.append(l)
    if action == "NEXT" and fileObject is not None:
        fileObject.ratings_and_scores.mark_as_played_for_uid(
            uid=1, percent_played=percent_played, when=time_occured)
        fileObject.ratings_and_scores.deinc_score_for_uid(uid=1, percent_played=percent_played)
        done.append(l)
    if action == "RATE" and fileObject is not None:
        fileObject.ratings_and_scores.mark_as_played_for_uid(
            uid=1, percent_played=percent_played, when=time_occured)
        fileObject.ratings_and_scores.rate(uid=1, rating=rating)
        done.append(l)


def read_action_file():
    done = []
    file_lines = []
    if os.path.exists(ACTION_FILE):
        fp = open(ACTION_FILE,"r")
        for l in fp:
            file_lines.append(l)
            m = action_re.match(l)
            if m:
                parse_action_line(m, l, done)

    remove_done_lines_from_action_file(done, file_lines)

def remove_done_lines_from_action_file(done, file_lines):
    diff = set(file_lines) - set(done)
    fp = open(ACTION_FILE,"w")
    for l in diff:
        fp.write(l)
    fp.close()



read_action_file()

files = get_by_true_score(1, 90, 9) + \
        get_by_true_score(1, 80, 8) + \
        get_by_true_score(1, 70, 7) + \
        get_by_true_score(1, 60, 6) + \
        get_by_true_score(1, 50, 5)

print files
copied = []
copy_to_usb(files)

print "rating_data:",

for root, dirs, files in os.walk(DST_DIR):
    diff = set(files) - set(copied)

print "diff:", diff

for f in diff:
    if f.endswith(".mp3"):
        fname = os.path.join(DST_DIR, f)
        print "removing from phone:",fname
        os.unlink(fname)
