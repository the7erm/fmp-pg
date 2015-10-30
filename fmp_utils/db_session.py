
import os
import sys
import configparser

from sqlalchemy import create_engine

config = configparser.RawConfigParser()
config.read(os.path.expanduser('~/.fmp/config'))
user = config.get('postgres', 'username')
pword = config.get('postgres', 'password')
host = config.get('postgres', 'host')
port = config.get('postgres', 'port')
connection_string = 'postgresql+psycopg2://{user}:{pword}@{host}:{port}/fmp2'
connection_string = connection_string.format(
    user=user, pword=pword, host=host, port=port)
engine = create_engine(connection_string, echo=False)
from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine, expire_on_commit=False)
session = Session()

def create_all(Base):
    Base.metadata.create_all(engine)

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


