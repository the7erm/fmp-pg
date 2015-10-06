#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# folder_class.py -- assign owners
#    Copyright (C) 2015 Eugene Miller <theerm@gmail.com>
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

import os
import sys
import subprocess
from copy import deepcopy
from pprint import pprint, pformat
from collections import Counter

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from log_class import Log, logging
logger = logging.getLogger(__name__)

def insert_missing_folders():
    sql = """INSERT INTO folders (dirname) SELECT DISTINCT fl.dirname
             FROM file_locations fl 
                  LEFT JOIN folders fo ON fo.dirname = fl.dirname
             WHERE fo.dirname IS NULL
             ORDER BY fl.dirname"""
    query(sql)

def find_common_parent(folder_list, refine=True):
    folder_structure = {}
    many_children = []
    only_one_child = []
    no_children = []
    folder_list_copy = deepcopy(folder_list)

    most_common_dir = ""
    dirname = folder_list[0]
    highest_match = len(dirname)

    for dirname2 in folder_list_copy:
        for i in range(0, len(dirname2)):
            try:
                if dirname[i] != dirname2[i]:
                    if i < highest_match:
                        highest_match = i
                    break
            except IndexError:
                if i < highest_match:
                        highest_match = i
                break
            
        # print "highest_match:",highest_match, dirname[0:highest_match]

    most_common_dir = dirname[0:highest_match]
    print "dirname:", dirname
    print most_common_dir

    return most_common_dir



class Folders(Log):
    __name__ == "Folders"
    logger = logger
    def __init__(self, *args, **kwargs):
        super(Folders, self).__init__(*args, **kwargs)
        self.dbInfo = {}
        self.kwargs = deepcopy(kwargs)
        self.dirname = kwargs.get("dirname")
        self.folder_id = kwargs.get("folder_id")
        print "dirname:", self.dirname

    @property
    def folder_id(self):
        return self.dbInfo.get('folder_id')

    @folder_id.setter
    def folder_id(self, value):
        if not value or self.folder_id == value:
            return

        dbInfo = get_dbInfo_from_folder_id(value)
        if dbInfo:
            self.dbInfo = dbInfo
            return
        self.insert(**{'folder_id': value})

    def get_dbInfo_from_folder_id(self, folder_id):
        sql = """SELECT * FROM folders 
                 WHERE folder_id = %(folder_id)s
                 LIMIT 1"""
        spec = {'folder_id': folder_id}
        return get_assoc_dict(sql, spec)

    def get_dbInfo_from_dirname(self, dirname):
        sql = """SELECT * FROM folders 
                 WHERE dirname = %(dirname)s
                 LIMIT 1"""
        spec = {'dirname': dirname}
        return get_assoc_dict(sql, spec)

    @property
    def dirname(self):
        return self.dbInfo.get("dirname")

    @dirname.setter
    def dirname(self, value):
        if not value or value == self.dirname:
            return

        if os.path.exists(value):
            value = os.path.realpath(value)

        dbInfo = self.get_dbInfo_from_dirname(value)
        if dbInfo:
            self.dbInfo = dbInfo
            return

        self.insert(**{'dirname': value})

    def insert(self, **dbInfo):
        insert_dbInfo = deepcopy(self.dbInfo)
        insert_dbInfo.update(dbInfo)
        if not insert_dbInfo.get('dirname'):
            raise Exception('Folders', 'required field dirname is empty')
        sql = """INSERT INTO folders ({cols})
                 VALUES({values})
                 RETURNING *"""
        cols = []
        values = []
        for k, v in insert_dbInfo.items():
            cols.append(k)
            values.append('%({k})s'.format(k=k))
        sql = sql.format(cols=",".join(cols), values=",".join(values))
        self.dbInfo = get_assoc_dict(sql, insert_dbInfo)

    @property
    def mtime(self):
        if not os.path.exists(self.dirname):
            return 0.0
        return os.path.getmtime(self.dirname)

    @property
    def db_mtime(self):
        return self.dbInfo.get('mtime')

    @property
    def scan_mtime(self):
        return self.dbInfo.get('scan_mtime')

    @property
    def time_to_scan(self):
        mtime = self.mtime
        return mtime != self.scan_mtime or mtime != self.db_mtime


    def get_parent_from_folder_id(self):
        if not self.dbInfo.get('folder_id'):
            return self.get_parent_from_dirname()

        sql = """SELECT *
                 FROM folders
                 WHERE folder_id = %(parent_folder_id)s
                 LIMIT 1"""
        parent_dbInfo = get_assoc_dict(sql, self.dbInfo)
        if parent_dbInfo == {}:
            return self.get_parent_from_dirname()

    def get_parent_from_dirname(self):
        parent, folder = os.path.split(self.dirname)
        if self.dirname == '/':
            mtime = os.path.getmtime('/')
            parent_dbInfo = {
                'dirname': '',
                'folder_id': 0,
                'parent_folder_id': 0,
                'scan_mtime': mtime,
                'mtime': mtime
            }
            return parent_dbInfo
        sql = """SELECT *
                 FROM folders
                 WHERE dirname = %(parent)s"""
        parent_dbInfo = get_assoc_dict(sql, {'parent': parent})
        if not parent_dbInfo:
            self.parent = Folders(dirname=parent)
            parent_dbInfo = self.parent.dbInfo
        return parent_dbInfo



    def get_children(self):
        like = "{dirname}%%".format(dirname=self.dirname)
        sql = """SELECT *
                 FROM folders
                 WHERE parent_folder_id = %(folder_id)s 
                 ORDER BY dirname"""
        return get_results_assoc_dict(sql, **self.dbInfo)

    def save(self):
        if self.dirname == '/':
            self.folder_id = 0
        parent = self.get_parent_from_dirname()

        sql = """UPDATE folders
                 SET dirname = %(dirname)s,
                     scan_mtime = %(scan_mtime)s,
                     mtime = %(mtime)s,
                     parent_folder_id = %(parent_folder_id)s
                 WHERE folder_id = %(folder_id)s
                 RETURNING *"""
        spec = {
            'folder_id': self.folder_id,
            'scan_mtime': self.scan_mtime,
            'mtime': self.mtime,
            'dirname': self.dirname,
            'parent_folder_id': parent.get('folder_id')
        }
        self.dbInfo = get_assoc_dict(sql, spec)



    def scan(self, force=False, background=False):
        if not self.time_to_scan and not force:
            return
        if not self.dirname:
            return
        cmd = ['scan.py', self.dirname]

        self.scan_process = subprocess.Popen(cmd)
        
        if not background:
            self.scan_process.wait()

if __name__ == "__main__":
    sql = """SELECT DISTINCT dirname, folder_id
             FROM file_locations
             ORDER BY dirname"""
    dirnames = get_results_assoc_dict(sql)

    for f in dirnames:
        sql = """SELECT *
                 FROM folders
                 WHERE dirname = %(dirname)s
                 LIMIT 1"""
        folder = get_assoc(sql, f)
        if not folder:
            sql = """INSERT INTO folders (dirname)
                     VALUES (%(dirname)s)
                     RETURNING *"""
            folder = get_assoc(sql, f)
        sql = """UPDATE file_locations 
                 SET folder_id = %(folder_id)s
                 WHERE dirname = %(dirname)s"""
        spec = {
            'folder_id':folder['folder_id'],
            'dirname': f['dirname']
        }
        if f['folder_id'] != folder['folder_id']:
            query(sql, spec)
            print mogrify(sql, spec)

    folders = get_results_assoc_dict("""SELECT *
                                        FROM folders
                                        ORDER BY dirname DESC""")
    folder_list = []
    for f in folders:
        folder_list.append(f['dirname'])

    for dirname in folder_list:
        folder = Folders(dirname=dirname)
        dbInfo = folder.get_parent_from_dirname()
        print "parent :",dbInfo['dirname']
        folder.save()
    sys.exit()

    most_common_parent = find_common_parent(folder_list)
    print "RESULT:"
    pprint(most_common_parent)
    most_common_parent = Folders(dirname=most_common_parent)
