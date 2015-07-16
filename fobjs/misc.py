try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from utils import utcnow
from pprint import pprint
import sys
import traceback
import logging
import sqlparse
from copy import deepcopy
from datetime import date, datetime

logger = logging.getLogger(__name__)

def get_fobj(*args, **kwargs):
    from netcast_episode_class import Netcast_FObj
    from local_fobj_class import Local_FObj
    if 'fid' in kwargs and kwargs.get('fid'):
        return Local_FObj(*args, **kwargs)
    if 'eid' in kwargs and kwargs.get("eid"):
        return Netcast_FObj(*args, **kwargs)
    print "DEPRICATED id id_type"
    print "*"*20
    print args
    print kwargs
    print sys.exc_info()[0]
    traceback.print_exc()
    traceback.print_stack()
    print "*"*20
    sys.exit()
    return None

def get_recently_played(limit=10, convert_to_fobj=False, listeners=None):
    user_history_sanity_check()
    listeners = _listeners(listeners)
    uids = get_uids(listeners)

    limit = int(limit)
    user_limit = limit * 3
    # TODO user user_history
    sql = """SELECT uh.eid, uh.fid, uh.time_played, percent_played, count(*)
             FROM user_history uh,
                  users u
             WHERE u.uid IN ({uids}) AND
                   uh.uid = u.uid AND
                   time_played IS NOT NULL
             GROUP BY uh.eid, uh.fid, uh.time_played, uh.percent_played
             ORDER BY time_played DESC
             LIMIT {limit}""".format(
                    limit=limit,
                    uids=",".join(uids)
             )

    print "get_recently_played:", sql

    res = get_results_assoc_dict(sql)
    if not convert_to_fobj:
        return res
    results = []
    for r in res:
        fobj = get_fobj(**r)
        if fobj is None:
            print "NONE FOBJ DETECTED"
            sys.exit()
        results.append(fobj)
    return results

def time_to_cue_netcast(listeners=None):
    listeners = _listeners(listeners)
    recent = get_recently_played(listeners=listeners)
    cue = True
    for r in recent:
        if r.get('eid') is not None:
            cue = False
            logger.debug("FOUND EID")
            break
    logger.debug("TIME TO CUE NETCAST:%s", cue)
    return cue

def get_users():
    sql = """SELECT uid, uname, listening, admin
             FROM users
             ORDER BY admin DESC, uname"""

    return get_results_assoc_dict(sql)

def get_listeners():
    sql = """SELECT uid, uname, listening, admin
             FROM users
             WHERE listening = True
             ORDER BY admin DESC, uname"""

    return get_results_assoc_dict(sql)

def _listeners(listeners=None):
    if listeners is None:
        listeners = get_listeners()
    return listeners

def fid_eid_match(most_recent, sql_args):
    check_keys = ['fid', 'eid']
    all_match = True
    for key in check_keys:
        if sql_args.get(key) != most_recent.get(key):
            all_match = False
            break
    return all_match

def get_most_recent(**sql_args):
    return get_most_recent_for_uid(**sql_args)

def get_most_recent_for_uid(**sql_args):
    user_history_sanity_check()
    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s AND
                   time_played IS NOT NULL
             ORDER BY time_played DESC
             LIMIT 1"""
    most_recent_for_uid = get_assoc_dict(sql, sql_args)
    return most_recent_for_uid

def date_played_info_for_uid(**sql_args):
    user_history_sanity_check()
    # This one makes sure it hasn't been played today.
    fid = sql_args.get('fid')
    fid_query = "fid = %(fid)s"

    if fid is None:
        fid_query = "fid IS NULL"

    eid = sql_args.get('eid')
    eid_query = "eid = %(eid)s"

    if eid is None:
        eid_query = "eid IS NULL"

    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s AND
                   {fid_query} AND
                   {eid_query} AND
                   date_played = %(date_played)s
             LIMIT 1""".format(fid_query=fid_query,
                               eid_query=eid_query)
    return get_assoc_dict(sql, sql_args)

def get_uids(listeners=None):
    listeners = _listeners(listeners)
    uids = []
    for listener in listeners:
        uids.append(str(int(listener['uid'])))
    return uids

def get_unlistend_episode(listeners=None, limit=1):
    logger.debug("GET_unlistend_episode")
    listeners = _listeners(listeners)
    uids = get_uids(listeners)
    limit = int(limit)

    if not uids:
        return None

    sql = """SELECT ne.*, n.*
             FROM netcast_episodes ne 
                  LEFT JOIN netcast_listend_episodes nle ON 
                            nle.eid = ne.eid,
                  netcast_subscribers ns,
                  netcasts n
             WHERE ns.uid IN ({uids}) AND
                   ne.nid = ns.nid AND
                   nle.uid IS NULL AND
                   n.nid = ne.nid
             ORDER BY ne.pub_date DESC
             LIMIT {limit}""".format(uids=",".join(uids), limit=limit)

    from netcast_episode_class import Netcast_FObj
    if limit == 1:
        res = get_assoc_dict(sql)
        if res != {}:
            return Netcast_FObj(**res)
        return None

    res = get_results_assoc_dict(sql)
    results = []
    for r in res:
        results.append(Netcast_FObj(**r))
    return results
    

def get_expired_netcasts():
    sql = """SELECT * 
             FROM netcasts
             WHERE expire_time <= NOW() OR expire_time IS NULL"""
    return get_results_assoc_dict(sql)

def user_history_sanity_check():
    sql = """UPDATE user_history 
             SET time_played = current_timestamp 
             WHERE time_played > current_timestamp"""
    query(sql)

    sql = """UPDATE user_history 
             SET date_played = current_timestamp::date
             WHERE date_played > current_timestamp::date"""
    query(sql)

def format_sql(sql, sql_args={}, sets=[], wheres=[], values=[],
               wheres_join=" AND \n", sets_join=",\n",
               cols_join=",", values_join=","):
    sql_sets = []
    for key in sets:
        if key in sql_args:
            sql_sets.append("{key} = %({key})s".format(key=key))
        else:
            logging.warn("%s not in sql_args skipping", key)

    sql_wheres = []
    for key in wheres:
        if key in sql_args and sql_args.get(key) is not None:
            value = sql_args.get(key)
            sql_wheres.append("{key} = %({key})s".format(key=key))
        else:
            # The value either doesn't exist in our sql_args
            # OR it is None eg:NULL
            sql_wheres.append("{key} IS NULL".format(key=key))
            if key not in sql_args:
                logging.warn("%s not in sql_args fallback to IS NULL", key)

    sql_cols = []
    sql_values = []
    for key in values:
        if key in sql_args:
            sql_cols.append(key)
            sql_values.append("%({key})s".format(key=key))
        else:
            logging.warn("%s not in sql_args", key)

    return sqlparse.format(
        sql.format(
            sets=sets_join.join(sql_sets),
            wheres=wheres_join.join(sql_wheres),
            cols=cols_join.join(sql_cols),
            values=values_join.join(sql_values),
        ),
        reindent=True, 
        keyword_case='upper'
    )


JSON_WHITE_LIST = [
    'album_name',
    'aid',
    'alid',
    'altp',
    'artist',
    'artists',
    'date_played',
    'eid',
    'enabled',
    'episode_title',
    'fid',
    'genre',
    'genres',
    'gid',
    'listening',
    'listeners',
    'ltp',
    'netcast_name',
    'nid',
    'non_listeners',
    'percent_played',
    'plid',
    'preload',
    'rating',
    'reason',
    'score',
    'seq',
    'title',
    'time_played',
    'true_score',
    'uhid',
    'uid',
    'ultp',
    'uname',
    'users',
    'user_file_info',
]


def jsonize(dbInfo):
    if isinstance(dbInfo, list):
        result = []
        for item in dbInfo:
            result.append(jsonize(item))
        return result
    dbInfo = deepcopy(dbInfo)
    remove_keys = []
    for key, item in dbInfo.iteritems():
        if key not in JSON_WHITE_LIST:
            remove_keys.append(key)
            continue
        if isinstance(item, (datetime, date)):
            dbInfo[key] = item.isoformat()
        #if isinstance(dbInfo[key], dict):
        #    dbInfo[key] = jsonize(dbInfo[key])
    for key in remove_keys:
        del dbInfo[key]
    return dbInfo
