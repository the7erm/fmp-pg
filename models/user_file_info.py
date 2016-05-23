
import sys
from time import time

if "../" not in sys.path:
    sys.path.append("../")
from sqlalchemy import ForeignKey, Column, Integer, String, BigInteger,\
                       Float, Date, Boolean
from sqlalchemy.orm import relationship
from fmp_utils.db_session import Session, session_scope
from fmp_utils.misc import to_int

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from .user_file_history import UserFileHistory
from .utils import do_commit
from datetime import date
from pprint import pprint
from time import time

class UserFileInfo(Base):
    __tablename__ = "user_file_info"

    id = Column(Integer, primary_key=True)

    rating = Column(Integer, default=6)
    skip_score = Column(Integer, default=5)
    true_score = Column(Float, default=((6 * 2 * 10) + (5 * 10)) / 2)
    time_played = Column(BigInteger)
    date_played = Column(Date)
    percent_played = Column(Float)
    reason = Column(String)
    voted_to_skip = Column(Boolean)

    file_id = Column(Integer, ForeignKey('files.id'))
    user_id = Column(Integer, ForeignKey('users.id'))
    timestamp = Column(BigInteger, onupdate=time)
    history = relationship("UserFileHistory", backref="user_file_info",
                           order_by="UserFileHistory.date_played.desc()")

    def mark_as_played(self, **kwargs):
        with session_scope() as session:
            session.add(self)
            print ("UserFileInfo.mark_as_played()")
            pprint(kwargs)
            self.time_played = to_int(kwargs.get('now', time()))
            print("time():", time())
            print("kwargs.now:", kwargs.get("now", time()))
            print("kwargs.percent_played:", kwargs.get("percent_played", 0))
            self.percent_played = to_int(kwargs.get('percent_played', 0))
            self.date_played = date.fromtimestamp(self.time_played)
            do_commit(self)
            session.add(self)

            for h in self.history:
                print("H:",h)
                if h.date_played == self.date_played and \
                   h.user_id == self.user_id:
                    self.update_ufh(h, session)
                    h.mark_as_played(**kwargs)
                    return

            ufh = UserFileHistory()
            session.add(ufh)
            self.update_ufh(ufh, session)
            session.add(self)
            ufh.mark_as_played(**kwargs)
            session.add(self)
            session.add(ufh)
            self.history.append(ufh)

    def update_ufh(self, ufh, session):
        ufh.user_file_id = self.id
        ufh.user_id = self.user_id
        ufh.file_id = self.file_id
        ufh.rating = self.rating
        ufh.reason = self.reason
        ufh.voted_to_skip = self.voted_to_skip
        ufh.skip_score = self.skip_score
        ufh.true_score = self.true_score

    def inc_score(self, *args, **kwargs):
        if self.skip_score is None:
            self.skip_score = 5

        if self.voted_to_skip:
            # The user voted to skip, but the other users didn't so they
            # were forced to listen to the whole song.
            # We'll take it down by 2 notches for them.
            self.skip_score += -2
        else:
            self.skip_score += 1
        self.calculate_true_score()

    def deinc_score(self, *args, **kwargs):
        if self.skip_score is None:
            self.skip_score = 5
        self.skip_score += -1
        self.calculate_true_score()

    def calculate_true_score(self):
        with session_scope() as session:
            session.add(self)
            print("UserFileInfo.calculate_true_score()")
            if self.rating is None:
                self.rating = 6
            if self.skip_score is None:
                self.skip_score = 5

            true_score = (((self.rating * 2 * 10) + (self.skip_score * 10)) / 2)

            """
            if true_score < -20:
                true_score = -20

            if true_score > 125:
                true_score = 125
            """

            self.true_score = true_score

            do_commit(self)

    def __repr__(self):
        return "<UserFileInfo(file_id=%r, user_id=%r)>" % (
                          self.file_id, self.user_id)

    def json(self, history=False):
        with session_scope() as session:
            session.add(self)
            ufi = to_json(self, UserFileInfo)
            ufi['history'] = []
            if ufi:
                session.add(self)
                ufi['user'] = self.user.json()
            if history:
                session.add(self)
                for h in self.history:
                    session.add(h)
                    ufi['history'].append(h.json())
        return ufi

