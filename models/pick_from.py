

try:
    from .base import Base, to_json
except SystemError:
    from base import Base, to_json

from sqlalchemy import Column, Integer

class PickFrom(Base):
    __tablename__ = "pick_from"

    id = Column(Integer, primary_key=True)
    file_id = Column(Integer, index=True)

