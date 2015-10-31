
import sys
if "../" not in sys.path:
    sys.path.append("../")

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from sqlalchemy import Table, Column, ForeignKey, Integer, String

class Title(Base):
    __tablename__ = 'titles'

    id = Column(Integer, primary_key=True)
    name = Column(String)

    def json(self):
        return to_json(self, Title)