import os
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

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
