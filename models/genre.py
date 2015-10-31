
from sqlalchemy import Column, Integer, String, Boolean

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

class Genre(Base):
    __tablename__ = 'genres'
    id = Column(Integer, primary_key=True)
    name = Column(String)
    seqential = Column(Boolean, default=False)
    enabled = Column(Boolean, default=True)

    def json(self):
        return to_json(self, Genre)
