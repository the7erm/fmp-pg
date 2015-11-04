
import sys
if "../" not in sys.path:
    sys.path.append("../")

from fmp_utils.db_session import session_scope
from sqlalchemy import Column, Integer, String, BigInteger,\
                       Float, Boolean
from sqlalchemy.orm import relationship

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from .user_file_info import UserFileInfo

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    pword = Column(String)
    admin = Column(Boolean)
    listening = Column(Boolean)
    user_file_info = relationship("UserFileInfo", backref="user")
    history = relationship("UserFileHistory", backref="user")

    def json(self):
        d = to_json(self, User)
        del d['pword']
        return d

    def __repr__(self):
       return "<User(name=%r)>" % (
                    self.name)

def get_users(user_ids=[]):
    users = []
    with session_scope() as session:
        user_query = session.query(User)
        if user_ids:
            user_query = user_query.filter(User.id.in_(user_ids))
        else:
            user_query = user_query.filter(User.listening==True)

        users_query = user_query.order_by(User.name.asc())
        users = user_query.all()

        if not users:
            users = session.query(User)\
                           .order_by(User.name.asc())\
                           .all()
    return users
