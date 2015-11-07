
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.constants import VALID_EXT
from fmp_utils.media_tags import MediaTags
from fmp_utils.jobs import jobs

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date
from sqlalchemy.sql.expression import func
from .disk_entity import DiskEntitiy
from .location import Location
from .utils import do_commit
from .base import Base, to_json
from fmp_utils.db_session import Session, session_scope
from time import time
from pprint import pprint

class FolderScanner(object):
    def __init__(self):
        self.locations_to_scan = []
        self.folders_to_scan = []
        self.processed_folders = []
        self.processed_location = []
        self.len_folders_to_scan = 0
        self.len_locations_to_scan = 0
        self.len_folders_scanned = 0
        self.len_locations_scanned = 0
        self.total_folders = 0
        self.total_locations = 0
        self.offset = 0

    def append_folder(self, folder):
        if not folder:
            return
        print("APPEND FOLDER:", folder)
        if isinstance(folder, Folder):
            with session_scope() as session:
                session.add(folder)
                self.append_folder(folder.dirname)
                return
        realpath = os.path.realpath(folder)
        if os.path.exists(realpath) and not realpath in self.folders_to_scan \
           and realpath not in self.processed_folders:
            self.folders_to_scan.append(realpath)

        jobs.append_low(self.scan, unique=True)

    def append_location(self, location):
        realpath = os.path.realpath(location)
        _dirname = os.path.dirname(realpath)
        _basename = os.path.basename(realpath)
        base, ext = os.path.splitext(_basename)
        ext = ext.lower()
        if ext not in VALID_EXT:
            jobs.append_low(self.scan, unique=True)
            return
        print("APPEND LOCATION:", location)
        if not location:
            return
        if isinstance(location, Location):
            with session_scope() as session:
                session.add(location)
                self.append_location(location.filename)
                return
        realpath = os.path.realpath(location)
        if os.path.exists(realpath) and realpath not in \
           self.locations_to_scan and realpath not in \
           self.processed_location:
            self.locations_to_scan.append(realpath)

        jobs.append_low(self.scan, unique=True)


    def scan(self, *args, **kwargs):
        # FolderScanner.scan()
        end_time = time() + 0.25
        while self.folders_to_scan:
            dirname = self.folders_to_scan.pop(0)
            print("SCAN DIRNAME:", dirname)
            # Go 1 level, and always add to scanner
            scan_folder(dirname=dirname,
                        add_to_folder_scanner=True,
                        recurse=1,
                        force=True,
                        add_to_location_scanner=True)
            if dirname not in self.processed_folders:
                self.processed_folders.append(dirname)
            if time() > end_time:
                # break so we scan at least 1 file during a cycle
                break
        # End of while self.folders_to_scan:

        while self.locations_to_scan:
            filename = self.locations_to_scan.pop(0)
            if filename not in self.processed_location:
                scan_location(filename)
                if filename not in self.processed_location:
                    self.processed_location.append(filename)

            if time() > end_time:
                break

        self.print_progress()

    def print_progress(self):
        self.len_folders_to_scan = len(self.folders_to_scan)
        self.len_folders_scanned = len(self.processed_folders)
        self.total_folders = (self.len_folders_to_scan +
                              self.len_folders_scanned)
        try:
            self.folders_percent_complete = (
                float(self.len_folders_scanned) / float(self.total_folders)
            ) * 100
        except ZeroDivisionError:
            self.folders_percent_complete = 0

        print("Folders progress %s:%s %0.2f%%" % (
            self.len_folders_scanned,
            self.total_folders,
            self.folders_percent_complete)
        )

        self.len_locations_to_scan = len(self.locations_to_scan)
        self.len_locations_scanned = len(self.processed_location)
        self.total_locations = (self.len_locations_to_scan +
                                self.len_locations_scanned)

        try:
            self.location_percent_complete = (
                float(self.len_locations_scanned) / float(self.total_locations)
            ) * 100
        except ZeroDivisionError:
            self.location_percent_complete = 0

        print("Locations progress %s:%s %0.2f%%" % (
            self.len_locations_scanned,
            self.total_locations,
            self.location_percent_complete)
        )

        if self.len_locations_to_scan or self.len_folders_to_scan:
            jobs.append_low(self.scan, unique=True)
        """
        else:
            with session_scope() as session:
                last_24_hrs = time() - (60*60*24)
                folders = session.query(Folder)\
                                 .filter(Folder.scan_time < last_24_hrs)\
                                 .order_by(
                                    Folder.scan_time.asc(),
                                    func.random()
                                 ).limit(1)
                for folder in folders:
                    self.append_folder(folder.dirname)

            jobs.append_low(self.scan, unique=True)
        """


class Folder(DiskEntitiy, Base):
    __tablename__ = "folders"
    __mapper_args__ = {'concrete':True}

    id = Column(Integer, primary_key=True)
    skip_folder = Column(Boolean, default=False)
    scan_time = Column(Integer, default=0)
    parent_id = Column(Integer, default=0)

    def json(self):
        _json = {}
        with session_scope() as session:
            session.add(self)
            _json = to_json(self, Folder)
        return _json

    def scan(self, add_to_folder_scanner=False, recurse=-1, force=False,
             add_to_location_scanner=False, **kwargs):
        print("folder.scan()")
        with session_scope() as session:
            session.add(self)
            if not self.exists:
                print("MISSING:", self.dirname)
                return
            session.add(self)
            if not self.changed and not force:
                session.add(self)
                print("NOT CHANGED:", self.dirname)
                return
            session.add(self)
            print ("scanning:", self.dirname)
            session.add(self)
            for dirname, dirs, files in os.walk(self.dirname):
                print("CONTINUE TOP")
                session.add(self)
                # pprint(files)

                if recurse: # recurse is not 0 we stop at 0 keep going at negative
                            # or positive numbers
                    for _dir in dirs:
                        print("CONTINUE _DIR")
                        d = os.path.realpath(os.path.join(dirname, _dir))
                        if not d or d == "/":
                            continue

                        if add_to_folder_scanner:
                            folder_scanner.append_folder(d)
                            continue
                        scan_folder(dirname=d,
                                    add_to_folder_scanner=add_to_folder_scanner,
                                    add_to_location_scanner=add_to_location_scanner,
                                    recurse=recurse-1,
                                    force=force)

                for basename in files:
                    filename = os.path.realpath(
                        os.path.join(dirname, basename))
                    realpath = os.path.realpath(filename)
                    _dirname = os.path.dirname(realpath)
                    _basename = os.path.basename(realpath)
                    base, ext = os.path.splitext(_basename)
                    ext = ext.lower()
                    if ext not in VALID_EXT:
                        continue

                    if add_to_folder_scanner or add_to_location_scanner:
                        folder_scanner.append_location(realpath)
                        continue
                    scan_location(filename)

                break
            session.add(self)
            self.mtime = self.actual_mtime
            self.scan_time = time()
            do_commit(self)

def scan_location(filename):
    print("progress scan_location:", filename)
    realpath = os.path.realpath(filename)
    _dirname = os.path.dirname(realpath)
    _basename = os.path.basename(realpath)
    base, ext = os.path.splitext(_basename)
    ext = ext.lower()
    if ext not in VALID_EXT:
        return

    with session_scope() as session:
        loc = session.query(Location).filter_by(
            dirname=_dirname,
            basename=_basename
        ).first()
        if not loc:
            loc = Location()
            loc.dirname = _dirname
            loc.basename = _basename
        loc.scan()

def scan_folder(dirname, add_to_folder_scanner=False, recurse=-1, force=False,
                add_to_location_scanner=False):
    realpath = os.path.realpath(dirname)
    if not realpath or realpath == "/" or not os.path.exists(realpath):
        return
    with session_scope() as session:
        folder = session.query(Folder)\
                        .filter_by(dirname=realpath)\
                        .first()
        if not folder:
            folder = Folder()
            folder.dirname = realpath
            session.add(folder)
            session.commit()
        if add_to_folder_scanner:
            folder_scanner.append_folder(realpath)
        folder.scan(recurse=recurse,
                    add_to_folder_scanner=add_to_folder_scanner,
                    force=force,
                    add_to_location_scanner=add_to_location_scanner)

folder_scanner = FolderScanner()
