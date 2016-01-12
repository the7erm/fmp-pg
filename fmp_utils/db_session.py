
import os
import sys

try:
    import config as fmp_config
except ImportError:
    import fmp_utils.config as fmp_config

from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from contextlib import contextmanager

class FmpSession():
    # This is a simpleton class so we can replace the Session object when
    # we really connect to the database.
    # During setup we want a fake db environment so we're not throwing
    # a bunch of errors.
    def __init__(self):
        self.Session = None
        self.connect()

    def connect(self):
        if self.Session:
            self.Session = None
        print("fmp_config:", dir(fmp_config))
        self.connection_string = fmp_config.connection_string
        self.db = fmp_config.db_type

        try:
            self.engine = create_engine(self.connection_string, echo=False)
        except:
            self.connection_string = "sqlite://"
            self.db = 'sqlite'
            self.engine = create_engine(self.connection_string, echo=False)

        self.session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(self.session_factory)

    def create_all(self, Base):
        Base.metadata.create_all(self.engine)


def Session(*args, **kwargs):
    # Return the fmp_session.Session object
    return fmp_session.Session(*args, **kwargs)

# session = Session()

def create_all(Base):
    Base.metadata.create_all(fmp_session.engine)

def object_session(obj):
    created = False
    _session = None
    try:
        _session = Session.object_session(obj)
    except:
        e = sys.exc_info()[0]
        print("Exemption:", e)
        _session = Session()
        created = True
    if not _session:
        _session = Session()
        created = True

    return created, _session

def close_session(created, session):
    session.commit()
    if created:
        session.close()

def commit(obj):
    created, _session = object_session(obj)
    _session.add(obj)
    close_session(created, _session)



@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except:
        session.rollback()
        raise
    finally:
        session.close()


fmp_session = FmpSession()

