
try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from sqlalchemy import Table, Column, Integer, String, Boolean, BigInteger,\
                       Float, Date, ForeignKey

class Album(Base):
    __tablename__ = 'albums'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=False)

    def json(self):
        return to_json(self, Album)
