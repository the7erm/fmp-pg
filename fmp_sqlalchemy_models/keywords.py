
from baseclass import BaseClass
from alchemy_session import Base

from sqlalchemy import Column, Integer, Unicode

class Keywords(BaseClass, Base):
    __tablename__ = 'keywords'
    __repr_fields__ = [
        'kid',
        'word'
    ]

    kid = Column(Integer, primary_key=True)
    word = Column(Unicode, unique=True)
