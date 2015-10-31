
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")
from sqlalchemy import Table, Column, ForeignKey, String, Integer, Boolean
from fmp_utils.db_session import engine, session, create_all, Session
try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

class Preload(Base):
    __tablename__ = "preload"
    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    reason = Column(String)
    from_search = Column(Boolean, default=False)

    def json(self):
        return to_json(self, Preload)