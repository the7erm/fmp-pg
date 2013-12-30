
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode, Boolean

class Album(BaseClass, Base):
    __tablename__ = 'albums'
    __repr_fields__ = [
        'alid',
        'name',
        'seq'
    ]
    alid = Column(Integer, primary_key=True)
    name = Column(Unicode, index=True)
    seq = Column(Boolean, default=False)
