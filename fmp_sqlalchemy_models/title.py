
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode

class Title(BaseClass, Base):
    __tablename__ = 'titles'
    __repr_fields__ = [
        'tid',
        'name',
    ]
    tid = Column(Integer, primary_key=True)
    name = Column(Unicode, index=True)
