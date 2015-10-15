import os
import time
from datetime import datetime
from pprint import pprint
import pytz

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from fingerprint_util import calculate_file_fingerprint
from folder_class import Folders

class Locations(object):
    def __init__(self, parent=None):
        self.locations = []
        self.owners = []
        self.parent = parent
        self.existing_filename = None
        self.existing_fid = None

    def load_locations(self):
        self.locations = []
        where = []
        if self.parent.fid:
            where.append("fid = %(fid)s")
        dirname = ""
        basename = ""
        if os.path.exists(self.parent.real_filename):
            where.append("""(dirname = %(dirname)s AND 
                             basename = %(basename)s)""")
            dirname = os.path.dirname(self.parent.real_filename)
            basename = os.path.basename(self.parent.real_filename)

        if self.parent.fingerprint:
            where.append("""fingerprint = %(fingerprint)s""")

        sql = """SELECT *, fld.folder_id AS fld_folder_id
                 FROM file_locations fl
                      LEFT JOIN folders fld ON fld.dirname = fl.dirname
                 WHERE {WHERE}""".format(WHERE=" OR \n".join(where))

        sql_args = {
            'fid': self.parent.fid,
            'dirname': dirname,
            'basename': basename,
            'fingerprint': self.parent.fingerprint
        }

        print mogrify(sql, sql_args)
        self.locations = get_results_assoc_dict(sql, sql_args)
        self.load_folders()
        self.check_records_integrity()
        self.load_owners()

    def load_folders(self):
        self.folders = []
        for loc in self.locations:
            folder = Folders(**{'dirname':loc['dirname']})
            if folder.folder_id != loc.get('folder_id') or not\
               loc.get('fld_folder_id'):
                sql = """UPDATE file_locations
                         SET folder_id = %(folder_id)s
                         WHERE flid = %(flid)s"""
                loc = query(sql, loc)
                loc['fld_folder_id'] = folder.folder_id
                loc.update(folder.dbInfo)

            self.folders.append(folder)


    def load_owners(self):
        # TODO FACTOR THIS TO USE folder_id
        dirnames = [l['dirname'] for l in self.locations]
        sql = """SELECT DISTINCT admin, listening, u.uid, uname, 
                fo.uid AS owner
                FROM users u
                     LEFT JOIN folder_owners fo ON 
                               fo.uid = u.uid AND folder_id IN 
                    (
                        SELECT folder_id
                        FROM folders
                        WHERE dirname in (
                            SELECT DISTINCT dirname 
                            FROM file_locations 
                            WHERE fid = %(fid)s
                        )
                    )
                ORDER BY admin DESC, listening DESC, uname"""

        self.owners = get_results_assoc_dict(sql, {'fid': self.fid})
        for o in self.owners:
            del o['admin']
            del o['listening']


    @property
    def filename(self):
        if self.existing_filename:
            return self.existing_filename

        if not self.locations:
            self.load_locations()

        for l in self.locations:
            filename = os.path.join(l['dirname'], l['basename'])
            if os.path.exists(filename):
                self.existing_filename = filename
                self.existing_fid = l['fid']
                break
        if self.existing_filename:
            return self.existing_filename
        return ""

    @property
    def fid(self):
        if self.parent.fid:
            return self.parent.fid
        if self.filename and self.existing_fid:
            return self.existing_fid
        return None

    @property
    def basename(self):
        if self.existing_filename:
            return os.path.basename(self.existing_filename)
        return os.path.basename(self.filename)

    @property
    def dirname(self):
        if self.existing_filename:
            return os.path.dirname(self.existing_filename)
        return os.path.dirname(self.filename)

    def check_records_integrity(self):
        print "!"*100
        print "check_records_integrity"
        for l in self.locations:
            filename = os.path.join(l['dirname'], l['basename'])
            res = self.scan(filename, record=l)
            l.update(res)

    def set_exists(self, flid, exists):
        sql = """UPDATE file_locations
                 SET exists = %(exists)s
                 WHERE flid = %(flid)s
                 RETURNING *"""
        sql_args = {
            'flid': flid,
            'exists': exists
        }
        return get_assoc_dict(sql, sql_args)

    def scan(self, filename, record={}):
        exists = os.path.exists(filename)
        is_readable = os.access(filename, os.R_OK)
        if not exists or not is_readable:
            if record == {} or record.get('exists') == exists:
                return record
            return self.set_exists(record['flid'], exists)
        existing_fid = record.get('fid')
        if existing_fid:
            self.existing_fid = existing_fid

        print "existing_fid:", existing_fid

        dirname = os.path.dirname(filename)
        basename = os.path.basename(filename)
        (mode, ino, dev, nlink, uid, gid, size, atime, mtime, 
             ctime) = os.stat(filename)
        mtime_int = int(mtime)
        mtime = datetime.utcfromtimestamp(mtime_int)
        mtime = mtime.replace(tzinfo=pytz.utc)
        print "+"*100
        print "last modified: %s" % mtime

        scan = False
        if record.get('exists') != exists:
            # self.set_exists(l['flid'], exists)
            scan = True

        if record.get('mtime') != mtime:
            scan = True
            print "last modified: %s != %s" % (record.get('mtime'), mtime)

        if record.get('size') != size:
            scan = True

        if not scan:
            print "!scan"
            return record
        
        fingerprint, front_fingerprint, middle_fingerprint, end_fingerprint = \
            calculate_file_fingerprint(filename)

        sql_args = {
            'fingerprint': fingerprint,
            'front_fingerprint': front_fingerprint,
            'middle_fingerprint': middle_fingerprint,
            'end_fingerprint': end_fingerprint,
            'basename': basename,
            'dirname': dirname,
            'size': size,
            'exists': exists,
            'mtime': mtime
        }

        sql = """SELECT * 
                 FROM file_locations
                 WHERE dirname = %(dirname)s AND 
                       basename = %(basename)s
                 LIMIT 1"""

        if record == {}:
            record = get_assoc_dict(sql, sql_args)

        sql = """UPDATE file_locations
                 SET fingerprint = %(fingerprint)s,
                     front_fingerprint = %(front_fingerprint)s,
                     middle_fingerprint = %(middle_fingerprint)s,
                     end_fingerprint = %(end_fingerprint)s,
                     mtime = %(mtime)s,
                     size = %(size)s,
                     exists = %(exists)s
                 WHERE flid = %(flid)s
                 RETURNING *"""
        
        if record == {}:
            sql = """INSERT INTO file_locations
                     (fingerprint, front_fingerprint, middle_fingerprint,
                      end_fingerprint, mtime, size, exists)
                     VALUES(%(fingerprint)s, %(front_fingerprint)s,
                            %(middle_fingerprint)s, %(end_fingerprint)s,
                            %(mtime)s, %(size)s, %(exists)s)
                     RETURNING *"""

        record.update(sql_args)
        return get_assoc_dict(sql, record)