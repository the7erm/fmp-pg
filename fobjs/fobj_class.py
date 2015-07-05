
import os
from urllib import quote

class FObj_Class(object):
    def __init__(self, *args, **kwargs):
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


