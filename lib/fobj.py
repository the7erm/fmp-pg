#!/usr/bin/env python
# -*- coding: utf-8 -*-
# fobj.py -- File object
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
import os
import time
import datetime
import pprint
import urllib
import pytz
from excemptions import CreationFailed, NotImpimented

try:
    import mutagen
    from mutagen.id3 import APIC, PRIV, GEOB, MCDI, TIPL, ID3TimeStamp, UFID, \
                            TMCL, PCNT, RVA2, WCOM, COMM, Frame
except ImportError, err:
	print "mutagen isn't installed"
	print "run sudo apt-get install python-mutagen"
	exit(1)

pp = pprint.PrettyPrinter(depth=6)

audio_ext = ['.mp3','.wav','.ogg','.wma','.flac']
audio_with_tags = ['.mp3','.ogg','.wma','.flac']
video_ext = ['.wmv','.mpeg','.mpg','.avi','.theora','.div','.divx','.flv',
             '.mp4', '.m4a', '.mov', '.m4v']

def is_video(ext=None):
    return ext.lower() in video_ext


def is_audio(ext=None):
    return ext.lower() in audio_ext


def has_tags(ext=None):
    return ext.lower() in audio_with_tags


class FObj:
    def __init__(self, filename=None, dirname=None, basename=None, **kwargs):
        self.filename = None
        self.is_stream = False
        self.exists = False
        self.can_rate = False
        self.uri = None
        self.tags_easy = None
        self.tags_hard = None

        if kwargs:
            for k, v in kwargs.iteritems():
                setattr(self, k, v)

        if filename is not None and filename.startswith("file://"):
            self.uri = filename
            filename = urllib.url2pathname(filename).replace("file://", '', 1)

        if dirname is not None and basename is not None:
            if dirname.startswith("file://"):
                dirname = urllib.url2pathname(dirname).replace("file://", '', 1)
                basename = urrllib.url2pathname(basename)

            self.filename = os.path.join(dirname, basename)
            self.dirname = dirname
            self.basename = basename
        elif filename is not None:
            self.filename = filename
            self.dirname = os.path.dirname(filename)
            self.basename = os.path.basename(filename)
        else:
            raise CreationFailed(
                "Unabled to allocate filename:%s\n" % filename + 
                "Unabled to allocate dirname:%s\n" % dirname + 
                "Unabled to allocate basename:%s" % basename
            )
        
        if self.filename and (
                self.filename.startswith('http://') or 
                self.filename.startswith('https://') or 
                self.filename.startswith("rtsp://")
            ):
            self.is_stream = True
            self.uri = self.filename
        elif self.uri is None:
            self.uri = "file://%s" % urllib.pathname2url(self.filename)

        if not self.is_stream and self.filename:
            self.exists = os.path.exists(self.filename)

        if self.exists:
            self.filename = os.path.realpath(self.filename)
            self.dirname = os.path.dirname(self.dirname)
            self.basename = os.path.basename(self.basename)
            

        self.root, self.ext = os.path.splitext(self.basename)
        self.has_tags = has_tags(self.ext)
        self.is_audio = is_audio(self.ext)
        self.is_video = is_video(self.ext)
        self.mtime = None
        self.getmtime()


    def mark_as_played(self, *args, **kwargs):
        raise NotImpimented("mark_as_played")

    def update_history(id, id_type, percent_played=0):
        raise NotImpimented("mark_as_played")

    def deinc_score(self, *args, **kwargs):
        raise NotImpimented("deinc_score")

    def inc_score(self,*args,**kwargs):
        raise NotImpimented("inc_score")

    def get_tags(self):
        if self.exists and self.has_tags:
            self.tags_easy = mutagen.File(self.filename, easy=True)

    def getmtime(self):
        if self.exists:
            t = os.path.getmtime(self.filename)
            self.mtime = datetime.datetime.fromtimestamp(t)
            tz = time.strftime("%Z", time.gmtime())
            localtz = pytz.timezone(tz)
            self.mtime = localtz.localize(self.mtime)
            return self.mtime

    def __getitem__(self, key):
        if hasattr(self, 'db_info'):
            if self.db_info.has_key(key):
                return self.db_info[key]
        print "__getitem__",key
        return getattr(self, key)

    def to_dict(self):
        ratings = {}
        if hasattr(self,"ratings_and_scores") and \
           hasattr(self.ratings_and_scores,"ratings_and_scores"):
            for r in self.ratings_and_scores.ratings_and_scores:
                ultp = r["ultp"]
                if hasattr(ultp,"isoformat"):
                    ultp = r["ultp"].isoformat()
                print "R:",dict(r)
                r = dict(r)
                ratings[r['uid']] = {}
                for k, v in r.iteritems():
                    if k == "pword":
                        continue
                    if isinstance(v,datetime.datetime):
                        v = v.isoformat()
                    ratings[r['uid']][k] = v
                
            print "RATINGS:",ratings
        return {
            "basename":self.basename,
            "ratings":ratings
        }

import netcast_fobj
import local_file_fobj
import generic_fobj

def get_fobj(dirname=None, basename=None, fid=None, filename=None, eid=None, 
             nid=None, episode_url=None, local_filename=None, 
             register_as_new_file=False, register_as_new_netcast=False, 
             pub_date=None, _id=None, id_type=None, silent=False, **kwargs):

    if not silent:
        print "get_fobj Unused kwargs:",kwargs

    if kwargs.has_key('id') and _id is None:
        _id = kwargs['id']

    if kwargs.has_key('dir') and dirname is None:
        dirname = kwargs['dir']

    if id_type is not None and _id is not None:
        if id_type == 'f':
            try:
                return local_file_fobj.Local_File(fid=_id, silent=silent, **kwargs)
            except CreationFailed, e:
                print "local_file_fobj.CreationFailed:",e
        elif id_type == 'e':
            try:
                return netcast_fobj.Netcast_File(eid=_id, silent=silent, **kwargs)
            except CreationFailed, e:
                print "netcast_fobj.CreationFailed:", e
        elif id_type == 'g':
            try:
                return generic_fobj.Generic_File(_id=_id, silent=silent, 
                                                 **kwargs)
            except CreationFailed, e:
                print "generic_fobj.CreationFailed:", e

    try:
        return local_file_fobj.Local_File(dirname=dirname, basename=basename, 
                                           fid=fid, filename=filename, 
                                           insert=register_as_new_file, 
                                           silent=silent, **kwargs)

    except CreationFailed, e:
        print "local_file_fobj.CreationFailed:",e

    if register_as_new_file:
        raise CreationFailed('File was unable to be registered.')

    try:
        print "Attempting Netcast"
        return netcast_fobj.Netcast_File(filename=filename, dirname=dirname, 
                                          basename=basename, eid=eid, 
                                          episode_url=episode_url, 
                                          local_filename=local_filename, 
                                          nid=nid, pub_date=pub_date,
                                          insert=register_as_new_netcast,
                                          **kwargs)

    except CreationFailed, e:
        print "netcast_fobj.CreationFailed:", e

    if register_as_new_netcast:
        raise CreationFailed("File was not registered as a netcast.")

    return generic_fobj.Generic_File(dirname=dirname, basename=basename, 
                                      filename=filename, **kwargs)

def recently_played(limit=10):
    return get_results_assoc("""SELECT DISTINCT id, id_type, percent_played,
                                               time_played
                                FROM user_history uh, users u
                                WHERE u.uid = uh.uid AND u.uid IN (
                                        SELECT uid FROM users 
                                        WHERE listening = true)
                                ORDER BY time_played DESC
                                LIMIT %d""" % limit)

def recently_played_fobjs(limit=10, silent=False):
    recent = recently_played(limit)
    res = []
    for f in recent:
        r = get_fobj(silent=silent, **f)
        if r:
            res.append(r)

    return res

if __name__ == '__main__':
    import sys
    for arg in sys.argv[1:]:
        obj = get_fobj(filename=arg)
        print obj
        print "filename:",obj.filename

