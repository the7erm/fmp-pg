#!/usr/bin/env python
# -*- coding: utf-8 -*-
# listeners.py -- Listeners object
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
import time

class Listeners:
    def __init__(self):
        self.expires = time.time() - 1;
        self.refresh()

    def __getattr__(self, name):
        if name == 'listeners':
            if time.time() < self.expires:
                print "REFRESH LISTENERS!"
                self.refresh()
            return self.listeners

        if name == 'realtime_listeners':
            self.refresh()
            return self.listeners

        if name == 'recheck_listeners':
            if self.listeners:
                return self.listeners
            self.refresh()
            return self.listeners

        return getattr(self, name)

    def __str__(self):
        return "listeners:%s\n%s" % (pp.pformat(self.listeners),pp.pformat(self.selected))

    def refresh(self):
        self.expires = time.time() + 60
        self.listeners = get_results_assoc("SELECT * FROM users WHERE listening = true ORDER BY admin DESC, uname")
        self.selected = get_assoc("SELECT * FROM users WHERE selected = true AND listening = true LIMIT 1")
        if not self.selected and self.listeners:
            query("UPDATE users SET selected = false")
            query("UPDATE users SET selected = true WHERE uid = %s", (self.listeners[0]['uid']))
            self.selected = get_assoc("SELECT * FROM users WHERE selected = true AND listening = true LIMIT 1")

    def pp(self):
        pp.pprint(self.listeners)
        pp.pprint(self.selected)

listeners = Listeners()


if __name__ == "__main__":
    print listeners
    


