#!/usr/bin/env python
# fmp_sqlalchemy_models/baseclass.py -- baseclass for models.
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

import json
import gtk
import datetime
import logging

from sqlalchemy.exc import IntegrityError, InvalidRequestError, InterfaceError,\
                           OperationalError

gtk.gdk.threads_init()

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)
hanlder = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
hanlder.setFormatter(formatter)
hanlder.setLevel(logging.DEBUG)
log.addHandler(hanlder)

class BaseClass(object):

    def pre_save(self, session=None):
        return

    def post_save(self, session=None):
        return

    def save(self, session=None):
        wait()
        start_save = datetime.datetime.now()
        self.pre_save(session=session)
        saved = False
        try:
            session.add(self)
            session.commit()
            saved = True
        except IntegrityError, e:
            session.rollback()
            log.error("IntegrityError:%s ROLLBACK", e)
        except InvalidRequestError, e:
            session.rollback()
            log.error("InvalidRequestError:%s ROLLBACK", e)
        except OperationalError, e:
            log.error("OperationalError:%s ROLLBACK", e)
            session.rollback()
        if saved:
            self.post_save(session=session)
        delta = datetime.datetime.now() - start_save
        log.info("%s save time:%s", self.__class__.__name__, delta.total_seconds())
        wait()
        

    def getattr(self, obj, name, default=None):
        if '.' in name:
            name, rest = name.split('.', 1)
            obj = getattr(obj, name)
            if obj:
                return self.getattr(obj, rest, default=default)
            return None
        if not hasattr(obj, name):
            return default

        return getattr(obj, name)

    def get_value_repr(self, values, value, field=None, padding=0):
        this_padding = " "*padding
        if isinstance(value, list) and value:
            start_string = "%s=[" % (field,)
            values.append(start_string)
            for val in value:
                self.get_value_repr(values, val, padding=4)
                 
            values.append("]")
            return
        values_string = value.__repr__()
        lines = values_string.split("\n")
        if field:
            values.append("%s=%s" % (field, lines[0]))
        else:
            values.append(this_padding+lines[0])
        for l in lines[1:]:
            values.append(this_padding+l)

    def get_repr(self, obj, fields):
        title = self.__class__.__name__
        values = []
        title_length = len(title) + 2
        padding = " "*title_length
        join_text = "\n%s" % padding

        for field in fields:
            value = self.getattr(obj, field)
            self.get_value_repr(values, value, field, padding=len(field)+2)
        
        return "<%s(%s)>" % (title, join_text.join(values))

    def __repr__(self):
        return self.get_repr(self, self.__repr_fields__)

    def utf8(self, string):
        if not isinstance(string, unicode):
            return unicode(string, "utf8", errors="replace")
        return string

    def now_if_none(self, datetime_object=None):
        if datetime_object is not None:
            return datetime_object
        return datetime.datetime.now()

    def json(self, fields=None, session=None):
        if fields is None:
            if hasattr(self, '__json_fields__') and getattr(self, '__json_fields__'):
                fields = getattr(self, '__json_fields__')
            else:
                fields = self.__repr_fields__
        obj = {}

        for field in fields:
            val = self.getattr(self, field)
            # print "Field:%s" % field
            # print "field %s:%s %s" % (field, val, type(val))
            
            if isinstance(val, (datetime.datetime, datetime.date)):
                val = val.isoformat()
                # print "field %s:%s %s" % (field, val, type(val))
            obj[field] = val
            if isinstance(val, list):
                new_val = []
                for v in val:
                    new_val.append(v.to_dict(session=session))
                obj[field] = new_val

        return json.dumps(obj, indent=4)

    def to_dict(self, fields=None, session=None):
        if fields is None:
            if hasattr(self, '__json_fields__') and getattr(self, '__json_fields__'):
                fields = getattr(self, '__json_fields__')
            else:
                fields = self.__repr_fields__
        obj = {}
        for field in fields:
            val = self.getattr(self, field)
            if isinstance(val, (datetime.datetime, datetime.date)):
                val = val.isoformat()
            # print "to_dict:%s %s %s" % (field, val, type(val))
            obj[field] = val
            if isinstance(val, list):
                new_val = []
                for v in val:
                    new_val.append(v.to_dict(session=session))
                obj[field] = new_val
        return obj


def wait():
    # print "leave1"
    gtk.gdk.threads_leave()
    # print "/leave1"
    # print "enter"
    gtk.gdk.threads_enter()
    # print "/enter"
    if gtk.events_pending():
        while gtk.events_pending():
            # print "pending:"
            gtk.main_iteration(False)
    # print "leave"
    gtk.gdk.threads_leave()
    # print "/leave"

