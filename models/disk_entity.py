
import os
from math import floor

from .base import Base, to_json

from sqlalchemy import Column, Integer, BigInteger, Boolean, String

class DiskEntitiy(object):
    id = Column(Integer, primary_key=True)
    dirname = Column(String)
    mtime = Column(BigInteger)
    file_exists = Column(Boolean)
    type = Column(String(50))

    @property
    def exists(self):
        return os.path.exists(self.filename)

    @property
    def actual_mtime(self):
        mtime = os.path.getmtime(self.filename)
        return floor(mtime)

    @property
    def changed(self):
        return self.mtime != self.actual_mtime

    @property
    def filename(self):
        return self.dirname


