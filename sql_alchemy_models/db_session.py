
import os
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
Session = sessionmaker(bind=engine)
session = Session()

def create_all(Base):
    Base.metadata.create_all(engine)

