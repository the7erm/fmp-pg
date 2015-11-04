
import os
import sys
if "../" not in sys.path:
    sys.path.append("../")

try:
    from fmp_utils.constants import CONFIG_DIR, CONFIG_FILE
except:
    from .constants import CONFIG_DIR, CONFIG_FILE
import psycopg2
from pprint import pprint
import subprocess
import configparser

INSTALL_COMMANDS = {
    'apt-get': {
        'postgres' :{
            'cmd': 'sudo apt-get install postgresql',
            'tested': True
        }
    },
    'emerge': {
        'postgres': {
            'cmd': 'emerge postgresql',
            'tested': False
        }
    },
    'pacman': {
        'postgres': {
            'cmd': 'pacman -S postgresql',
            'tested': False
        }
    },
    'yum': {
        'postgres' :{
            'cmd': 'sudo yum install postgresql',
            'tested': False
        }
    },
}

def load_config():
    if not os.path.exists(CONFIG_FILE):
        return {
            'username': '',
            'password': '',
            'database': 'fmp',
            'host': 'localhost',
            'port': '5432',
            'locked': False
        }
    config = configparser.RawConfigParser()
    config.read(CONFIG_FILE)
    config_data = {}
    defaults = {
        'username': '',
        'password': '',
        'database': 'fmp',
        'host': 'localhost',
        'port': '5432',
        'locked': False
    }

    for k, default in defaults.items():
        try:
            config_data[k] = config.get('postgres', k)
        except:
            config_data[k] = default

        if not config_data[k]:
            config_data[k] = default

    return config_data

def test_conn(config):
    print("CONFIG:", config)
    result = {
        'connected': False,
        'username': config.get('username',''),
        'password': config.get('password',''),
        'database': config.get('database','fmp'),
        'host': config.get("host", 'localhost'),
        'port': config.get('port', 5432),
        'errors': []
    }

    if not os.path.exists(CONFIG_FILE):
        result['errors'].append('Config file doesn\'t exist')
        return result

    username = config.get('username', '')
    password = config.get('password', '')
    host = config.get('host', 'localhost')
    port = config.get('port', '5432')
    database = config.get('database', 'fmp')

    conn = None
    try:
        conn = psycopg2.connect(**{
                                  'database': database,
                                  'user': username,
                                  'password': password,
                                  'host': host,
                                  'port': int(port)
                                })
    except:
        print ("I am unable to connect to the database.")
        result['errors'].append('Can\'t connect to database')
        result['errors'].append("sys.exc_info()[0], sys.exc_info()[1]:%s %s" %
            (sys.exc_info()[0], sys.exc_info()[1]))
        conn = None
        print ("sys.exc_info()[0]:", sys.exc_info()[0], sys.exc_info()[1])


    if not conn:
        return result

    cur = conn.cursor()
    total_folders = 0
    total_files = 0
    total_users = 0

    try:
        total_folders = cur.execute("SELECT count(*) AS 'total' FROM folders").fetchone()[0]
    except:
        result['errors'].append("Can't count totals for table `folders`")

    try:
        sql = """SELECT count(*) AS 'total'
                 FROM files f, locations l
                 WHERE f.id = l.file_id"""
        total_files = cur.execute(sql).fetchone()[0]
    except:
        result['errors'].append("Can't count totals for table `files`")

    try:
        sql = """SELECT count(*) AS 'total'
                 FROM users u"""
        total_users = cur.execute(sql).fetchone()[0]
    except:
        result['errors'].append("Can't count totals for table `users`")

    result["totals"] = {
        "folders": total_folders,
        "files": total_files,
        "users": total_users
    }
    result['connected'] = True
    conn.close()
    return result

def db_list():
    try:
        db_list = subprocess.check_output(['psql', '--list', '-t'])
    except:
        return []
    lines = db_list.decode("utf8").split("\n")

    dbs = []
    for l in lines:
        try:
            name, owner, encoding, collate, ctype, access_privileges = l.split("|")
        except:
            continue
        dbs.append({
            'name': name.strip(),
            'owner': owner.strip(),
            'encoding': encoding.strip(),
            'collate': collate.strip(),
            'ctype': ctype.strip(),
            'access_privileges':access_privileges.strip()
        })
    return dbs

def db_user_list():

    try:
        db_users = subprocess.check_output(['psql', '-c', '\du', '-t'])
    except:
        return []
    lines = db_users.decode("utf8").split("\n")

    users = []
    for l in lines:
        l = l.strip()
        try:
            role_name, attributes, member_of = l.split("|")
        except:
            continue
        users.append({
            'role_name': role_name.strip(),
            'attributes': attributes.strip(),
            'member_of': member_of.strip()
        })
    return users

def which(prg):
    try:
        output = subprocess.check_output(['which', prg])
        output = output.strip()
        return output.decode("utf8")
    except:
        pass
    return ''

def psql_installed():
    return which('psql') or False

def postgres_running():
    # import pdb; pdb.set_trace()
    output = u''

    try:
        output = subprocess.check_output(['pgrep', 'postgres', '-a'])
        print ("OUTPUT1:", output)
    except:
        pass
    print ("OUTPUT2:", output)
    return output.decode("utf8")

def get_installer():
    for prg in INSTALL_COMMANDS.keys():
        _which = which(prg)
        if _which:
            print("FOUND:",_which)
            return prg

    return ''

def get_install_cmd(installer, pkg):
    return INSTALL_COMMANDS.get(installer, {}).get(pkg, {})

def check_config():
    installer = get_installer()
    os.makedirs(CONFIG_DIR, 0o775, True)
    config = load_config()

    con_result = test_conn(config)
    dbs = db_list()
    users = db_user_list()
    db_exists = False
    role_exists = False
    if con_result["connected"]:
        db_exists = True
        role_exists = True
    else:
        for db in dbs:
            if config['database'] and db['name'] == config['database']:
                db_exists = True

        for user in users:
            if config['username'] and user['role_name'] == config['username']:
                role_exists = True

    response = {
        'connected': True, # ajax request succeeded.
        'postgres': {
            'installed': psql_installed(),
            'running': postgres_running(),
            'can_connect': con_result,
            'db_exists': db_exists,
            'db_list': dbs,
            'db_user_list': users,
            'config': config,
            'install': get_install_cmd(installer, 'postgres'),
            'role_exists': role_exists
        },
        'config': {
            'dir': {
                'exists': os.path.exists(CONFIG_DIR),
                'R_OK': os.access(CONFIG_DIR, os.R_OK),
                'W_OK': os.access(CONFIG_DIR, os.W_OK),
                'X_OK': os.access(CONFIG_DIR, os.X_OK),
                'dirname': CONFIG_DIR,
            },
            'file': {
                'exists': os.path.exists(CONFIG_FILE),
                'R_OK': os.access(CONFIG_FILE, os.R_OK),
                'W_OK': os.access(CONFIG_FILE, os.W_OK),
                'X_OK': os.access(CONFIG_FILE, os.X_OK),
                'filename': CONFIG_FILE,
            }
        }
    }

    return response

def is_first_run():
    response = check_config()
    config = response['config']
    postgres = response['postgres']
    pprint(config)
    try:
        if not config['dir']['exists'] or not config['file']['exists'] or\
           not postgres['installed'] or not postgres['running'] or \
           not postgres['running'] or not postgres['db_exists'] or\
           not postgres['can_connect']['connected']:
            print ("IS FIRST RUN")
            print("^"*100)
            return True
    except KeyError:
        return True

    return False

first_run = is_first_run()

if not os.path.exists(CONFIG_DIR):
    first_run = True



print ("FIRST RUN", first_run)
print("^"*100)

if __name__ == "__main__":

    pprint(check_config())
