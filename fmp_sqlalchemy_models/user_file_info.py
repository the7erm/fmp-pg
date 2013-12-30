
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship

class UserFileInfo(BaseClass, Base):
    __tablename__ = "user_file_info"
    __table_args__ = (
        UniqueConstraint('fid', 'uid', name='uniq_idx_fid_uid'),
    )
    __repr_fields__ = [
        'ufid',
        'uid',
        'fid',
        'user.uname',
        'rating',
        'skip_score',
        'true_score',
        'percent_played',
        'ultp'
    ]
    ufid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey('users.uid'))
    fid = Column(Integer, ForeignKey('files_info.fid'))
    rating = Column(Integer(2), index=True, default=DEFAULT_RATING)
    skip_score = Column(Integer(2), index=True, default=DEFAULT_SKIP_SCORE)
    percent_played = Column(Float, index=True, default=DEFAULT_PERCENT_PLAYED)
    true_score = Column(Float, index=True, default=DEFAULT_TRUE_SCORE)
    ultp = Column(DateTime(timezone=True))
    history = relationship("UserHistory", 
                           backref="user_file_info",
                           order_by=UserHistory.time_played.desc)

    """
    listening_history = relationship("UserHistory", 
                                     order_by=UserHistory.time_played.desc,
                                     primaryjoin="and_(UserHistory.fid == UserFileInfo.fid, "
                                                 "User.listening == True, "
                                                 "User.uid == UserHistory.uid)")
    
    history = relationship("UserHistory",
                           backref="file",
                           primaryjoin="and_(UserHistory.fid == FileInfo.fid, "
                                             "User.listening == True, "
                                             "User.uid == UserHistory.uid)")"""

    def mark_as_played(self, when=None, percent_played=0, session=None):
        self.ultp = self.now_if_none(when)
        self.percent_played = percent_played
        self.calculate_true_score(session=session)
        self.update_history(session=session)
        self.save(session=session)
        # session.add(self)

    def update_history(self, session=None):
        found = False
        today = self.ultp.date()
        current_history = None
        log.info("Looping through history")
        for h in self.history:
            if h.date_played == today:
                current_history = h
                break
        log.info("done looping through history")
        if current_history is None:
            current_history = UserHistory(uid=self.uid, fid=self.fid)
            self.history.append(current_history)

        current_history.rating = self.rating
        current_history.skip_score = self.skip_score
        current_history.percent_played = self.percent_played
        current_history.true_score = self.true_score
        current_history.date_played = self.ultp.date()
        current_history.time_played = self.ultp
        self.save(session=session)

    def calculate_true_score(self, session=None):
        session.add(self)
        try:
            recent = self.history[0:5]
        except IndexError, e:
            log.error("IndexError:%s",e)
            recent = None
        except InterfaceError, e:
            log.error("InterfaceError:%s",e)
            recent = None
        
        if not recent:
            avg = DEFAULT_PERCENT_PLAYED
        else:
            total = 0
            for h in recent:
                if h.percent_played:
                    total += h.percent_played
            avg = total / len(recent)

        self.true_score = ((self.rating * 2 * 10.0) +
                           (self.skip_score * 10.0) +
                           (self.percent_played) +
                           avg
                          ) / 4

    def rate(self, rating, session=None):
        log.info("UserFileInfo.RATE:%s", rating)
        if rating is None:
            return
        rating = int(rating)
        if rating < 0 or rating > 5 or rating == self.rating:
            return
        self.rating = rating
        self.save(session=session)

    def inc_skip_score(self, session=None):
        skip_score = self.skip_score
        skip_score += 1
        self.set_skip_score(skip_score, session=session)

    def deinc_skip_score(self, session=None):
        skip_score = self.skip_score
        skip_score -= 1
        self.set_skip_score(skip_score, session=session)

    def set_skip_score(self, skip_score, session=None):
        skip_score = int(skip_score)
        if skip_score > 10 or skip_score < 1:
            return

        self.skip_score = skip_score
        self.save(session=session)

    def pre_save(self, session=None):
        self.calculate_true_score(session=session)
