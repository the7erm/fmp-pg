
import os
from urllib import quote
from copy import deepcopy
from datetime import datetime, date
from time import time
from misc import jsonize

class FObj_Class(object):
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.filename = kwargs.get('filename', "")
        self.percent_played = kwargs.get("percent_played", -1)
        if self.percent_played is None:
            self.percent_played = 0

    @property
    def exists(self):
        if not self.filename:
            return False
        return os.path.exists(self.filename)

    @property
    def basename(self):
        return os.path.basename(self.filename)

    @property
    def dirname(self):
        return os.path.dirname(self.filename)

    @property
    def ext(self):
        base, ext = os.path.splitext(self.basename)
        ext = ext.lower()
        return ext

    @property
    def uri(self):
        if self.exists:
            return 'file://'.quote(self.filename)
        return self.filename

    @property
    def mtime(self):
        if self.exists:
            return os.path.getmtime(self.filename)
        return -1

    def json(self):
        dbInfo = jsonize(self.dbInfo)
        if hasattr(self, 'listeners'):
            dbInfo['user_file_info'] = self.listeners.json()

        if 'plid' in self.kwargs:
            kwargs = deepcopy(self.kwargs)
            if 'listeners' in kwargs:
                del kwargs['listeners']
            dbInfo['preloadInfo'] = jsonize(kwargs)
        elif 'nid' in self.kwargs and 'eid' in self.kwargs and \
            self.kwargs.get('eid'):
                dbInfo['netcastInfo'] = jsonize(self.kwargs)
        elif 'fid' in self.kwargs and self.kwargs.get('fid'):
            dbInfo['fileInfo'] = jsonize(self.kwargs)
        else:
            dbInfo['kwargs'] = jsonize(self.kwargs)
        return dbInfo
