#!/usr/bin/env python
# fmp_sqlalchemy_models/user_history.py -- User History Table.
#    Copyright (C) 2014 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from baseclass import BaseClass
from alchemy_session import Base
from sqlalchemy import Column, Integer, String, DateTime, Float,\
                       UniqueConstraint, ForeignKey, Date
from sqlalchemy.orm import relationship

class UserHistory(BaseClass, Base):
    __tablename__ = 'user_history'

    __table_args__ = (
        UniqueConstraint('uid', 'fid', 'date_played', 
                         name='uniq_idx_user_history_uid_fid_date_played'),
    )
    __repr_fields__ = [
        'uhid',
        'uid',
        'ufid',
        'fid',
        'rating',
        'skip_score',
        'percent_played',
        'true_score',
        'time_played',
        'date_played',
        'user.uname'
    ]
    uhid = Column(Integer, primary_key=True)
    uid = Column(Integer, ForeignKey("users.uid"))
    ufid = Column(Integer, ForeignKey("user_file_info.ufid"))
    fid = Column(Integer, ForeignKey("files_info.fid"))
    # eid = Column(Integer, ForeignKey("episodes.eid"))
    rating = Column(Integer)
    skip_score = Column(Integer)
    percent_played = Column(Float)
    true_score = Column(Float)
    time_played = Column(DateTime(timezone=True))
    date_played = Column(Date)
    user = relationship("User")
