
import sys
if "../" not in sys.path:
    sys.path.append("../")
try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date, ForeignKey

from time import time

class Album(Base):
    __tablename__ = 'albums'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=False)
    timestamp = Column(BigInteger, onupdate=time)

    def json(self):
        return to_json(self, Album)
