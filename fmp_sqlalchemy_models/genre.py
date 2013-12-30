
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode, Boolean

class Genre(BaseClass, Base):
    __tablename__ = 'genres'
    __repr_fields__ = [
        'gid',
        'name',
        'seq',
        'enabled'
    ]

    gid = Column(Integer, primary_key=True, nullable=False)
    name = Column(Unicode, index=True)
    enabled = Column(Boolean, default=True, index=True)
    seq = Column(Boolean, default=False)
