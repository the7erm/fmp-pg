from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import os
import sys
from sqlalchemy.pool import StaticPool

"""
engine = create_engine(
            "postgresql+pg8000://scott:tiger@localhost/test",
            isolation_level="READ UNCOMMITTED"
        )

"""
CONFIG_PATH = os.path.expanduser("~/.fmp/")
print "CONFIG_PATH:{CONFIG_PATH}".format(**{
    "CONFIG_PATH": CONFIG_PATH
})

if not os.path.exists(CONFIG_PATH):
    os.path.mkdirs(CONFIG_PATH)

db_connection_string = 'sqlite:///{CONFIG_PATH}file_info_idea.sqlite.db'.format(**{
    "CONFIG_PATH": CONFIG_PATH
})

if "--pgsql" in sys.argv:
    CONNECTION_FILE = os.path.join(CONFIG_PATH,"db-connection-string")
    if os.path.exists(CONNECTION_FILE):
        fp = open(CONNECTION_FILE, 'r')
        db_connection_string = fp.read().strip()
        fp.close()

class DB:
    def __init__(self, db_connection_string):
        self.db_connection_string = db_connection_string
        kwargs = {
            'echo': False,
            'encoding': 'utf-8',
            'convert_unicode': True
        }
        if db_connection_string.startswith('sqlite'):
            kwargs['poolclass'] = StaticPool
            kwargs['connect_args'] = { 'check_same_thread': False }

        self.engine = create_engine(db_connection_string, **kwargs)
        self.session_factory = None
        self.Base = None
        self.Session = None

    def create_all(self, base):
        if base is None or \
           self.Base is not None or \
           self.session_factory is not None:
            return
        self.Base = base
        self.Base.metadata.create_all(self.engine)

    def init_session_factory(self, base=None):
        if self.session_factory is not None:
            return
        self.create_all(base)
        self.session_factory = sessionmaker(bind=self.engine)

    def session(self, base=None):
        self.init_session_factory(base)

        if self.Session is not None:
            return self.Session()

        self.Session = scoped_session(self.session_factory)
        return self.Session()

db = DB(db_connection_string)

def make_session(Base):
    return db.session(Base)
