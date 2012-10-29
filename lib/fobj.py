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
import os, time
import pprint
pp = pprint.PrettyPrinter(depth=6)

class Listeners:
    def __init__(self):
        self.refresh()

    def __getattr__(self, name):
        if name == 'listeners':
            if time.time() < self.expires():
                self.refresh()
            return self.listeners

        return getattr(self, name)

    def __str__(self):
        return "listeners:%s\n%s" % (pp.pformat(self.listeners),pp.pformat(self.selected))

    def refresh(self):
        self.expires = time.time() + 60
        self.listeners = get_results_assoc("SELECT * FROM users WHERE listening = true ORDER BY admin DESC, uname")
        self.selected = get_assoc("SELECT * FROM users WHERE selected = true AND listening = true")
        if not self.selected and self.listeners:
            query("UPDATE users SET selected = false")
            query("UPDATE users SET selected = true WHERE uid = %s", (self.listeners[0]['uid']))
            self.selected = get_assoc("SELECT * FROM users WHERE selected = true AND listening = true")


    def mark_fid_as_played(self, fid):
        print "mark_fid_as_played:",fid

    def mark_eid_as_played(self, eid):
        print "mark_eid_as_played:",eid


    def pp(self):
        pp.pprint(self.listeners)
        pp.pprint(self.selected)

listeners = Listeners()

class NotImpimented(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)

class Fobj:
    def __init__(self, filename=None):
        self.filename = filename
        self.dirname = os.path.dirname(filename)
        self.basename = os.path.basename(filename)

    def mark_as_played(self):
        raise NotImpimented("mark_as_played")

    def exists(self):
        return os.path.exists(self.filename)

class Local_File(Fobj):
    def __init__(self, dirname=None, basename=None, fid=None, filename=None):
        if filename != None:
            dirname = os.path.dirname(filename)
            basename = os.path.basename(filename)

        if fid:
            db_info = get_assoc("SELECT * FROM files WHERE fid = %s LIMIT 1",(fid,))

        if dirname != None and basename != None:
            db_info = get_assoc("SELECT * FROM files WHERE dir = %s AND basename = %s LIMIT 1",(dirname, basename))

        if db_info:
            filename = os.path.join(self.db_info['dir'], self.db_info['basename'])

        super(Fobj, self).__init__(filename=filename)

        self.db_info = db_info

    def mark_as_played(self):
        listeners.mark_fid_as_played(self.db_info['fid'])
        

class Netcast_File(Fobj):
    def __init__(self, filename=None, dirname=None, basename=None, eid=None, episode_url=None):
        super(Fobj, self).__init__(filename=filename)

    def mark_as_played(self):
        listeners.mark_eid_as_played(self.db_info['eid'])


if __name__ == "__main__":
    import sys
    print listeners
    for arg in sys.argv:
        print arg

