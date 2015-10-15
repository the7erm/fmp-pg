
from datetime import datetime, timedelta
from fobj_class import FObj_Class
from location_class import Locations
from listeners_class import Listeners
from player1 import SUPPORTED_EXTENSIONS

import pytz
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
    __name__ == "Local_FObj"
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.artistDbInfo = []
        self.vote_data = {}
        self.genresDbInfo = []
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
        self.artistDbInfo = []
        self.vote_data = {}
        self.genresDbInfo = []

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
            if not self.fid:
                self.log_debug("Using fid from locations:%s" % self.locations.fid)
                self.fid = self.locations.fid

    @property
    def fid(self):
        return self.dbInfo.get('fid')

    @property
    def fingerprint(self):
        return self.dbInfo.get('fingerprint')

    @fid.setter
    def fid(self, value):
        try:
            value = int(value)
        except:
            self.log_debug("TRIED TO SET FID TO:%s" % value)
            return

        if value != self.fid:
            self.load_from_fid(value)

    def reload(self):
        self.log_debug(".reload()")
        self.load_from_fid(self.fid)
        self.listeners.reload()

    @property
    def eid(self):
        return self.dbInfo.get('eid')

    def load_from_fid(self, fid):
        if not fid:
            return {}
        spec = {'fid': fid}
        sql = """SELECT *
                 FROM files f
                 WHERE fid = %(fid)s"""
        self.dbInfo = get_assoc_dict(sql, spec)
        sql = """SELECT *
                 FROM artists a, file_artists fa
                 WHERE fa.aid = a.aid AND fa.fid = %(fid)s
                 ORDER BY artist"""
        self.artistDbInfo = get_results_assoc_dict(sql, spec)

        sql = """SELECT *
                 FROM genres g, file_genres fg
                 WHERE g.gid = fg.gid AND fg.fid = %(fid)s
                 ORDER BY genre"""
        self.genresDbInfo = get_results_assoc_dict(sql, spec)

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
            self.dbInfo['mtime'].replace(tzinfo=pytz.utc)
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
        kwargs.update({'vote_data': self.vote_data})
        self.listeners.inc_score(**kwargs)

    def deinc_score(self, *args, **kwargs):
        kwargs.update(self.dbInfo)
        kwargs.update({'vote_data': self.vote_data})
        self.listeners.deinc_score(**kwargs)

    def majority_deinc_score(self, *args, **kwargs):
        kwargs.update(self.dbInfo)
        kwargs.update({'vote_data': self.vote_data})
        self.listeners.majority_deinc_score(**kwargs)

    def dict(self):
        return self.dbInfo


already_scanned = []

skip = [
    '.crazycraft',
    '.fellowship',
    '.minecraft',
    '.technic',
    '/assets/',
    '/resources/',
    '/sound',
]

def scan_file(filename):
    filename = os.path.realpath(filename)
    for s in skip:
        if s in filename:
            return
    
    if not os.path.exists(filename):
        return
    is_readable = os.access(filename, os.R_OK)
    if not is_readable:
        return
    base, ext  = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in SUPPORTED_EXTENSIONS or ext == '':
        return
    obj = Local_FObj(filename=filename)
    print "filename:",obj.filename

def scan_dir(directory):
    for s in skip:
        if s in directory:
            return
    
    directory = os.path.realpath(directory)
    if not os.path.exists(directory):
        return
    if directory in already_scanned:
        return
    already_scanned.append(directory)
    
    for root, dirs, files in os.walk(directory):
        skip_it = False
        for s in skip:
            if s in root:
                skip_it = True
                break
        if skip_it:
            continue
        print "scanning:", root
        for basename in files:
            filename = os.path.join(root, basename)
            scan_file(filename)

if __name__ == "__main__":
    import sys
    
    from pprint import pprint
    for arg in sys.argv:
        print "arg:", arg
        if os.path.isfile(arg):
            scan_file(arg)
            continue
        if os.path.isdir(arg):
            scan_dir(arg)

    if "--folders" in sys.argv:
        sql = """SELECT dirname 
                 FROM file_locations
                 ORDER BY dirname"""

        dirs = get_results_assoc_dict(sql)
        for d in dirs:
            skip_it = False
            for s in skip:
                if s in d['dirname']:
                    skip_it = True
            if skip_it:
                continue
            if not os.path.exists(d['dirname']):
                dirname = d['dirname']

                if dirname.startswith("/home/erm/") and not \
                   dirname.startswith("/home/erm/disk2/"):
                   print "before dirname:%s" % dirname
                   dirname = dirname.replace("/home/erm/", 
                                             "/home/erm/disk2/acer-home/")

                   print "after dirname:%s" % dirname
                   if os.path.exists(dirname):
                        scan_dir(dirname)


                

