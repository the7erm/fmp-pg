
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date

from .disk_entity import DiskEntitiy
from .location import Location
from .utils import do_commit
from .base import Base, to_json


class Folder(DiskEntitiy, Base):
    __tablename__ = "folders"
    __mapper_args__ = {'concrete':True}

    id = Column(Integer, primary_key=True)

    def scan(self):
        if not self.exists:
            print("MISSING:", self.dirname)
            return

        if not self.changed:
            print("NOT CHANGED:", self.dirname)
            return

        print ("scanning:", self.dirname)
        for dirname, dirs, files in os.walk(self.dirname):
            # pprint(files)
            for _dir in dirs:
                d = os.path.realpath(os.path.join(dirname, _dir))
                if not d or d == "/":
                    continue
                folder = session.query(Folder).filter_by(dirname=d).first()
                if not folder:
                    folder = Folder(dirname=d)
                session.add(folder)
                folder.scan()

            for basename in files:
                filename = os.path.realpath(os.path.join(dirname, basename))
                _dirname = os.path.dirname(filename)
                _basename = os.path.basename(filename)
                base, ext = os.path.splitext(_basename)
                ext = ext.lower()
                if ext not in VALID_EXT:
                    continue
                loc = session.query(Location).filter_by(
                    dirname=_dirname,
                    basename=_basename
                ).first()
                if not loc:
                    loc = Location()
                    loc.dirname = _dirname
                    loc.basename = _basename
                loc.scan()
            break
        self.mtime = self.actual_mtime
        do_commit(self)


