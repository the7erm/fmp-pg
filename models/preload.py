
import os
import sys
from time import time
if "../" not in sys.path:
    sys.path.append("../")

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from sqlalchemy import Table, Column, ForeignKey, String, Integer, Boolean,\
                       BigInteger

class Preload(Base):
    __tablename__ = "preload"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    reason = Column(String)
    from_search = Column(Boolean, default=False)
    timestamp = Column(BigInteger, onupdate=time)

    def json(self):
        return to_json(self, Preload)