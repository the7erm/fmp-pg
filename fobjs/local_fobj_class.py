
from fobj_class import FObj_Class
import os
from datetime import datetime
from pprint import pprint

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from misc import _listeners, get_most_recent

class Locations(object):
    def __init__(self, parent=None):
        self.locations = []
        self.parent = parent
        self.existing_filename = None

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

        sql = """SELECT *
                 FROM file_locations 
                 WHERE {WHERE}""".format(WHERE=" OR \n".join(where))

        sql_args = {
            'fid': self.parent.fid,
            'diranme': dirname,
            'basename': basename,
            'fingerprint': self.parent.fingerprint
        }

        # print mogrify(sql, sql_args)
        self.locations = get_results_assoc_dict(sql, sql_args)

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
                break
        if self.existing_filename:
            return self.existing_filename
        return ""

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


class Listeners(object):
    def __init__(self, *args, **kwargs):
        self.listeners = _listeners(kwargs.get('listeners', None))
        self.parent = kwargs.get('parent')

    def init_mark_as_played_sql_args(self, sql_args):
        ultp = sql_args.get('ltp', 
                            sql_args.get('now', datetime.utcnow())
                         )
        sql_args.update({
            'ultp': ultp,
            'time_played': ultp,
            'date_played': ultp.date(),
            'fid': self.parent.fid,
            'target_type': 'f',
            'target_key': 'fid'
        })


    def mark_as_played(self, **sql_args):
        self.init_mark_as_played_sql_args(sql_args)
        for l in self.listeners:
            sql_args.update(l)
            self.mark_as_played_for_listener(**sql_args)

    def mark_as_played_for_listener(self, **sql_args):
        sql = """UPDATE user_song_info 
                 SET ultp = %(ultp)s,
                     percent_played = %(percent_played)s,
                     true_score = ((
                        (rating * 2 * 10) + (score * 10) +
                        %(percent_played)s
                     ) / 3)
                 WHERE uid = %(uid)s AND
                       fid = %(fid)s
                 RETURNING *"""
        
        updated = get_assoc_dict(sql, sql_args)
        if updated != {}:
            test_result = (
                              (updated['rating'] * 2 * 10) + 
                              (updated['score'] * 10) + 
                              updated['percent_played']
                          ) / 3
            print "updated:", updated['true_score'], 'test:', test_result
            sql_args.update(updated)
            sql_args['id'] = self.parent.fid
            sql_args['id_type'] = 'f'
            self.update_most_recent(**sql_args)

    def update_most_recent(self, **sql_args):
        most_recent = get_most_recent(**sql_args)
        target_type = sql_args.get('target_type', 'f')
        target_key = sql_args.get('target_key', 'fid')
        if target_type == 'e':
            if 'score' not in sql_args:
                sql_args['score'] = -1

            if 'rating' not in sql_args:
                sql_args['rating'] = -1

            if 'true_score' not in sql_args:
                sql_args['true_score'] = -1

            if 'reason' not in sql_args:
                    sql_args['reason'] = ''

        if most_recent.get('id') == sql_args.get(target_key) and \
           most_recent.get('id_type') == target_type:
            sql = """UPDATE user_history
                     SET time_played = %(time_played)s,
                         date_played = %(date_played)s,
                         percent_played = %(percent_played)s,
                         rating = %(rating)s,
                         score = %(score)s,
                         true_score = ((
                                (%(rating)s * 2) + 
                                (%(score)s * 10) +
                                %(percent_played)s
                            ) / 3)
                     WHERE uhid = %(uhid)s"""
            sql_args['uhid'] = most_recent['uhid']
            
            query(sql, sql_args)
        else:
            
            sql = """INSERT INTO user_history (time_played, date_played,
                                               id_type, id, uid, reason,
                                               score, rating, true_score)
                     VALUES(%(time_played)s, %(date_played)s, 
                            %(target_type)s, %(id)s, %(uid)s, %(reason)s,
                            %(score)s, %(rating)s, %(true_score)s)"""
            
            query(sql, sql_args)

    def calculate_true_score(self, *args, **sql_args):
        sql = """UPDATE user_song_info
                     SET true_score = ((
                        (rating * 2 * 10) + (score * 10) +
                        percent_played
                     ) / 3)
                 WHERE uid = %(uid)s AND
                       fid = %(fid)s
                 RETURNING *"""
        return get_assoc_dict(sql, sql_args)

    def inc_score(self, **sql_args):
        for l in self.listeners:
            sql = """UPDATE user_song_info 
                     SET score = score + 1,
                         true_score = ((
                            (rating * 2 * 10) + (score * 10) +
                            percent_played
                         ) / 3)
                     WHERE uid = %(uid)s AND
                           fid = %(fid)s"""
            sql_args.update(l)
            before = self.calculate_true_score(**sql_args)
            query(sql, sql_args)
            after = self.calculate_true_score(**sql_args)
            print "INC BEFORE:", before['true_score']
            print "INC AFTER:", after['true_score']


    def deinc_score(self, **sql_args):
        for l in self.listeners:
            sql = """UPDATE user_song_info 
                     SET score = score - 1,
                         true_score = ((
                            (rating * 2 * 10) + (score * 10) +
                            percent_played
                         ) / 3)
                     WHERE uid = %(uid)s AND
                           fid = %(fid)s
                     RETURNING *"""
            sql_args.update(l)
            query(sql, sql_args)
            before = self.calculate_true_score(**sql_args)
            query(sql, sql_args)
            after = self.calculate_true_score(**sql_args)
            print "DEINC BEFORE:", before['true_score']
            print "DEINC AFTER:", after['true_score']


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
        self.listeners = Listeners(parent=self)
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

    def load_from_fid(self, fid):
        if not fid:
            return fid
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
        self.dbInfo['ltp'] = kwargs.get('ltp', 
                                kwargs.get('now', datetime.utcnow())
                             )
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

if __name__ == "__main__":
    files = get_results_assoc_dict("""SELECT * FROM files LIMIT 100""")
    for f in files:
        obj = Local_FObj(**f)
        print obj.filename
