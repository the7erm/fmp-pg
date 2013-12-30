
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, ForeignKey, Unicode

class Preload(BaseClass, Base):
    __tablename__ = "preload"
    __repr_fields__ = [
        'prfid',
        'fid',
        'uid',
        'reason'
    ]
    prfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files_info.fid'))
    uid = Column(Integer, ForeignKey('users.uid'))
    priority = Column(Integer, default=1)
    reason = Column(Unicode)
