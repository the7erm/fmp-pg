
import sys
from time import time
from sqlalchemy import ForeignKey, Column, Integer, String, BigInteger,\
                       Float, Date, Boolean
from sqlalchemy.orm import relationship
from datetime import date

if "../" not in sys.path:
    sys.path.append("../")

from .utils import do_commit

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json


class UserFileHistory(Base):
    __tablename__ = "user_file_history"

    id = Column(Integer, primary_key=True)
    rating = Column(Integer)
    skip_score = Column(Integer)
    true_score = Column(Float)
    time_played = Column(BigInteger)
    date_played = Column(Date)
    percent_played = Column(Float)
    reason = Column(String)
    voted_to_skip = Column(Boolean)
    user_id = Column(Integer, ForeignKey('users.id'))
    file_id = Column(Integer, ForeignKey('files.id'))
    user_file_id = Column(Integer, ForeignKey('user_file_info.id'))

    def mark_as_played(self, **kwargs):
        print ("UserFileHistory.mark_as_played()")
        self.time_played = int(kwargs.get('now', time()))
        self.percent_played = kwargs.get('percent_played', 0)
        self.date_played = date.fromtimestamp(self.time_played)
        do_commit(self)