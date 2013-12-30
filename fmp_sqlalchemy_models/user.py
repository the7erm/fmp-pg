
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode, Boolean, DateTime
from sqlalchemy.orm import relationship, deferred

class User(BaseClass, Base):
    __tablename__ = "users"
    __repr_fields__ = [
        'uid',
        'uname',
        'listening',
        'admin',
        'last_time_cued',
        'selected'
    ]

    uid = Column(Integer, primary_key=True)
    admin = Column(Boolean)
    uname = Column(Unicode, unique=True)
    pword = deferred(Column(Unicode(132)))
    listening = Column(Boolean, default=True)
    selected = Column(Boolean, default=False)
    last_time_cued = Column(DateTime, index=True)
    rating_data = relationship("UserFileInfo", backref="user")
    preload = relationship("Preload", backref="user",
                           primaryjoin="User.uid == Preload.uid")
