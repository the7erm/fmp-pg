#!/usr/bin/env python3

from setproctitle import setproctitle
setproctitle("scan.py")

import os
import sys
from time import time
from pprint import pprint, pformat

from fmp_utils.constants import VALID_EXT
from fmp_utils.db_session import create_all, session_scope
from models.folder import Folder
from models.location import Location

from sqlalchemy.sql import and_

dirs_to_scan = []
folders_to_create = []
files_to_scan = []

print("Getting files/folders list")
for arg in sys.argv[1:]:

    if arg in ("-folders", "--folders"):
        root_folders = []
        with session_scope() as session:
            for result in session.query(Location.dirname)\
                                  .distinct()\
                                  .order_by(Location.dirname):
                found = False
                for root in root_folders:
                    if result.dirname.startswith(root):
                        found = True
                        break
                if not found:
                    print ("adding root folder:", result.dirname)
                    root_folders.append(result.dirname)
                    if result.dirname not in dirs_to_scan:
                        dirs_to_scan.append(result.dirname)

    realpath = os.path.realpath(
        os.path.expanduser(arg)
    )
    if not realpath or not os.path.exists(realpath):
        continue

    if os.path.isdir(arg):
        dirs_to_scan.append(arg)
    if os.path.isfile(arg):
        files_to_scan.append(arg)

for _dir in dirs_to_scan:
    folders_to_create.append(_dir)
    for root, dirs, files in os.walk(_dir):
        for __dir in dirs:
            dirname = os.path.join(root, __dir)
            dirname = os.path.realpath(dirname)
            folders_to_create.append(dirname)

        for basename in files:
            base, ext = os.path.splitext(basename)
            ext = ext.lower()
            if ext not in VALID_EXT:
                continue
            filename = os.path.join(root, basename)
            filename = os.path.realpath(filename)

            files_to_scan.append(filename)

total = len(folders_to_create)

folders_to_create.sort()

print("Creating Folder objects")
time_to_update = time() + 1
with session_scope() as session:
    for i, dirname in enumerate(folders_to_create):
        if time() > time_to_update:
            time_to_update = time() + 1
            percent = (i / float(total)) * 100
            print("folder progress %s:%s %0.2f%%" % (i, total, percent))
            sys.stdout.flush()
        folder = session.query(Folder)\
                        .filter(Folder.dirname==dirname)\
                        .first()
        if folder:
            folder.dirname = dirname
            folder.mtime = folder.actual_mtime
            session.commit()
            continue

        folder = Folder()
        folder.dirname = dirname
        folder.mtime = folder.actual_mtime
        session.add(folder)
        session.commit()

    print("folder progress %s:%s %0.2f%%" % (total, total, 100))

    time_to_update = time() + 1
    total = len(files_to_scan)
    for i, filename in enumerate(files_to_scan):
        if time() > time_to_update:
            time_to_update = time() + 1
            percent = (i / float(total)) * 100
            print("file progress %s:%s %0.2f%%" % (i, total, percent))
            sys.stdout.flush()
        dirname, basename = os.path.split(filename)
        location = session.query(Location)\
                          .filter(Location.dirname==dirname,
                                  Location.basename==basename)\
                          .first()
        if location:
            if location.changed:
                session.add(location)
                location.scan()
                session.add(location)
                session.commit()
            continue
        location = Location()
        location.dirname = dirname
        location.basename = basename
        session.add(location)
        location.scan()
        session.add(location)
        session.commit()

    print("file progress %s:%s %0.2f%%" % (total, total, 100))