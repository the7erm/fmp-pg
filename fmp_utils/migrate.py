
import sys
sys.path.append('../')

from fmp_utils.db_session import session_scope, fmp_session
from models.file import File
from models.user import User
from models.user_file_info import UserFileInfo
from models.user_file_history import UserFileHistory
from models.location import Location

from sqlalchemy.sql import not_, and_, text
import psycopg2

user = fmp_session.user
pword = fmp_session.pword

pg_conn = psycopg2.connect("dbname='fmp' user='%s' host='localhost' password='%s'"
                           % (user, pword),
                           cursor_factory=psycopg2.extras.DictCursor)

pg_cur = pg_conn.cursor(cursor_factory=psycopg2.extras.DictCursor)

from time import time
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
with session_scope() as session:



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

    sql = """SELECT count(*) AS total
             FROM user_song_info usi, file_locations fl
             WHERE rating != 6 AND fl.fid = usi.fid"""

    print("counting")
    total = get_assoc_dict(sql)
    total = total['total']

    sql = """SELECT *
             FROM user_song_info usi, file_locations fl
             WHERE rating != 6 AND fl.fid = usi.fid"""


    print("fetching ratings")
    ratings = get_results_assoc_dict(sql)
    show_progress = time() + 1
    for i, r in enumerate(ratings):
        if time() > show_progress:
            percent = (i / float(total)) * 100
            print("%s:%s %0.2f%%" % (i, total, percent))
            show_progress = time() + 1
            sys.stdout.flush()

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

            # if user_file_info.true_score == r['true_score']:
            #    continue

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

            sql = """SELECT *
                     FROM user_history uh
                     WHERE uid = %(uid)s AND
                           uh.fid = %(fid)s"""
            history = get_results_assoc_dict(sql, {
                'uid': r['uid'],
                'fid': r['fid']
            })
            session.add(user_file_info)
            session.commit()
            for h in history:
                user_file_history = None
                for uh in user_file_info.history:
                    if uh.date_played == h['date_played']:
                        user_file_history = uh
                        break
                if user_file_history:
                    continue
                user_file_history = UserFileHistory()
                user_file_history.user_file_id = user_file_info.id
                user_file_history.user_id = user_file_info.user_id
                user_file_history.file_id = user_file_info.file_id
                user_file_history.time_played = \
                    int(h['time_played'].strftime("%s"))
                user_file_history.date_played = h['date_played']
                user_file_history.percent_played = h['percent_played']
                user_file_history.reason = h['reason']
                user_file_history.voted_to_skip = False
                user_file_history.rating = h['rating']
                user_file_history.skip_score = h['score']
                user_file_history.true_score = h['true_score']
                # print ("adding:", h)
                # print ("adding:", user_file_history)
                session.add(user_file_history)
                session.commit()
