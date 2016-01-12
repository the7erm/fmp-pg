print ("IMPORTED CONFIG")
import configparser
import os

cfg = configparser.RawConfigParser()
cfg.read(os.path.expanduser('~/.fmp/config'))
db_type = ""
user = ""
pword = ""
host = ""
port = ""
try:
    user = cfg.get('postgres', 'username')
    pword = cfg.get('postgres', 'password')
    host = cfg.get('postgres', 'host')
    port = cfg.get('postgres', 'port')
    database = cfg.get("postgres", "database")
    connection_string = 'postgresql+psycopg2://{user}:{pword}@{host}:{port}/{database}'
    connection_string = connection_string.format(
        user=user, pword=pword, host=host, port=port,
        database=database)
    # print("self.connection_string:", self.connection_string)
    db_type = 'postgres'
except:
    connection_string = "sqlite://"
    db_type = 'sqlite'
    print("FALLBACK")
