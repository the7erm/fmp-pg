
import sys
if "../" not in sys.path:
    sys.path.append("../")
try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from .associations import album_artist_association_table
from sqlalchemy import Column, Integer, String, Boolean, BigInteger
from sqlalchemy.orm import relationship, backref
from time import time

class Artist(Base):
    __tablename__ = 'artists'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean)
    albums = relationship("Album",
                          secondary=album_artist_association_table,
                          backref="artists")
    timestamp = Column(BigInteger, onupdate=time)

    def json(self):
        return to_json(self, Artist)