from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import func
import os
import sys
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

def make_session(Base):

    # fmp_sqlalchemy_test
    engine = create_engine(db_connection_string, echo=False, encoding='utf-8',
                           convert_unicode=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)

    session = Session()
    return session
