
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, ForeignKey, Unicode

class DontPick(BaseClass, Base):
    __tablename__ = 'dont_pick'
    dpfid = Column(Integer, primary_key=True)
    fid = Column(Integer, ForeignKey('files_info.fid'))
    reason = Column(Unicode, default="No reason")
    junk = Column(Unicode, default="")
    # TODO: alembic
    # alter table dont_pick  add column junk VARCHAR
    __repr_fields__ = [
        'dpfid',
        'fid',
        'file.basename',
        "reason"
    ]
