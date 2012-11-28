#!/usr/bin/env python
# -*- coding: utf-8 -*-
# excemptions.py -- Exceptions
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

class NotImpimented(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return repr(self.value)


class CreationFailed(Exception):
    def __init__(self, value):
        self.value = value
    def __str__(self):
        return str(self.value)


