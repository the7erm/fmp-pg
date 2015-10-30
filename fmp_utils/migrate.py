
import sys
sys.path.append('../')

from fmp_utils.db_session import session, user, pword, host, port
from sql_alchemy_models.db_models import File, User, UserFileInfo, PickFrom,\
                                         Preload, Location

from sqlalchemy.sql import not_, and_, text
import psycopg2

pg_conn = psycopg2.connect("dbname='fmp' user='%s' host='localhost' password='%s'"
                           % (user, pword),
                           cursor_factory=psycopg2.extras.DictCursor)

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

from pprint import pprint

def execute(cur, sql, args=None):
    cur.execute('COMMIT;')
    cur.execute(sql, args)
    pg_conn.commit()

def get_results_assoc(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    res = cur.fetchall()
    return res

def get_results_assoc_dict(sql, args=None):
    res = get_results_assoc(sql, args)
    res_dict = []
    for r in res:
        res_dict.append(dict(r))
    return res_dict

def get_assoc(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    res = cur.fetchone()
    return res

def get_assoc_dict(sql, args=None):
    res = get_assoc(sql, args)
    if not res:
        res = {}
    return dict(res)

def query(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    execute(cur, sql, args)
    return cur

def mogrify(sql, args=None):
    cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)
    # print "QUERY:", query
    # print "ARGS:",
    # pprint(args)
    return cur.mogrify(sql, args)

sql = """SELECT *
         FROM users"""

users = get_results_assoc_dict(sql)
for u in users:
    user = session.query(User)\
                  .filter(User.id==u['uid'])\
                  .first()
    if not user:
        user = User()
        user.id = u['uid']
        user.name = u['uname']
        session.add(user)
        session.commit()

sql = """SELECT *
         FROM user_song_info usi, file_locations fl
         WHERE rating != 6 AND fl.fid = usi.fid"""

ratings = get_results_assoc_dict(sql)
for r in ratings:
    location = session.query(Location)\
                      .filter(and_(Location.dirname==r['dirname'],
                                   Location.basename==r['basename']))\
                      .first()
    if location:
        user_file_info = None
        for ufi in location.file.user_file_info:
            if ufi.user_id == r['uid']:
                user_file_info = ufi
                break

        if not user_file_info:
            user_file_info = UserFileInfo()

        if user_file_info.true_score == r['true_score']:
            print("continue")
            continue

        user_file_info.user_id = r['uid']
        user_file_info.rating = r['rating']
        user_file_info.true_score = r['true_score']
        user_file_info.skip_score = r['score']
        if r['ultp']:
            user_file_info.date_played = r['ultp'].date()
            user_file_info.time_played = int(r['ultp'].strftime("%s"))
        user_file_info.percent_played = r['percent_played']
        user_file_info.file_id = location.file_id
        session.add(user_file_info)
        session.commit()


