
from datetime import datetime, timedelta
from fobj_class import FObj_Class
from location_class import Locations
from listeners_class import Listeners

import os

from pprint import pprint
import json
from copy import deepcopy

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from misc import _listeners, get_most_recent, \
                 date_played_info_for_uid, get_most_recent_for_uid
from utils import utcnow, convert_to_dt


class Local_FObj(FObj_Class):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.clean()
        self.real_filename = kwargs.get('filename', "")
        self.insert_new = kwargs.get("insert", False)
        self.fid = kwargs.get("fid", None)
        self.filename = kwargs.get('filename', "")
        self.reason = kwargs.get('reason', "")
        super(Local_FObj, self).__init__(*args, **kwargs)
        self.listeners = Listeners(parent=self, **kwargs)
        if not self.dbInfo or self.dbInfo == {}:
            self.insert()

    def clean(self):
        self.locations = []
        self.dbInfo = {}

    @property
    def filename(self):
        if not self.locations:
            self.locations = Locations(self)
        if self.locations:
            return self.locations.filename

        return self.real_filename

    @filename.setter
    def filename(self, value):
        if os.path.exists(value):
            self.real_filename = value
            self.locations = Locations(self)

    @property
    def fid(self):
        return self.dbInfo.get('fid')

    @property
    def fingerprint(self):
        return self.dbInfo.get('fingerprint')

    @fid.setter
    def fid(self, value):
        value = int(value)
        if value != self.fid:
            self.load_from_fid(value)

    @property
    def eid(self):
        return self.dbInfo.get('eid')

    def load_from_fid(self, fid):
        if not fid:
            return {}
        sql = """SELECT *
                 FROM files
                 WHERE fid = %(fid)s"""
        self.dbInfo = get_assoc_dict(sql, {'fid': fid})

    def insert(self):
        print "TODO INSERT"
        if not self.insert_new:
            return

    def save(self):
        sql = """UPDATE files 
                 SET ltp = %(ltp)s,
                     mtime = %(mtime)s,
                     edited = %(edited)s
                 WHERE fid = %(fid)s
                 RETURNING *"""
        mtime = self.mtime
        if mtime != -1:
            self.dbInfo['mtime'] = datetime.fromtimestamp(mtime)
        self.dbInfo = get_assoc_dict(sql, self.dbInfo)

    def mark_as_played(self, *args, **kwargs):
        fid = self.fid
        if fid:
            self.load_from_fid(fid)
        self.dbInfo['ltp'] = kwargs.get('now', utcnow())
        self.save()
        kwargs.update(self.dbInfo)
        kwargs.update({'reason': self.reason})
        self.listeners.mark_as_played(**kwargs)

    def inc_score(self, *args, **kwargs):
        kwargs.update(self.dbInfo)
        self.listeners.inc_score(**kwargs)

    def deinc_score(self, *args, **kwargs):
        kwargs.update(self.dbInfo)
        self.listeners.deinc_score(**kwargs)

    def dict(self):
        return self.dbInfo

if __name__ == "__main__":
    files = get_results_assoc_dict("""SELECT * FROM files LIMIT 100""")
    for f in files:
        obj = Local_FObj(**f)
        print obj.filename
