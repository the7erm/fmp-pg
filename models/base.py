from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.ext.declarative import declarative_base
import json
from datetime import datetime, date

from fmp_utils.db_session import Session, session_scope

Base = declarative_base()

def to_json(inst, cls):
    with session_scope() as session:
        session.add(inst)
        # stolen from http://stackoverflow.com/questions/7102754/jsonify-a-sqlalchemy-result-set-in-flask
        """
        Jsonify the sql alchemy query result.
        """
        convert = dict()
        # add your coversions for things like datetime's
        # and what-not that aren't serializable.
        d = dict()
        for c in cls.__table__.columns:
            v = getattr(inst, c.name)
            if isinstance(v, (datetime, date)):
                v = "%s" % v

            if c.type in convert.keys() and v is not None:
                try:
                    d[c.name] = convert[c.type](v)
                except:
                    d[c.name] = "Error:  Failed to covert using ", str(convert[c.type])
            elif v is None:
                d[c.name] = str()
            else:
                d[c.name] = v
        return d
