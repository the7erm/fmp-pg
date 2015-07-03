
from db.db import *
import pytz

def get_fobj(*args, **kwargs):
    print "GET_FOBJ"
    from netcast_episode_class import Netcast_FObj
    from local_fobj_class import Local_FObj
    if 'fid' in kwargs and kwargs.get('fid'):
        return Local_FObj(*args, **kwargs)
    if 'eid' in kwargs and kwargs.get("eid"):
        return Netcast_FObj(*args, **kwargs)
    if 'id_type' in kwargs:
        id_type = kwargs.get('id_type')
        _id = kwargs.get('id')
        if id_type == 'e':
            kwargs['eid'] = _id
        if id_type == 'f':
            kwargs['fid'] = _id

        if _id and id_type:
            return get_fobj(*args, **kwargs)
    return None

def get_recently_played(limit=10, convert_to_fobj=False, listeners=None):

    uids = get_uids(listeners)

    limit = int(limit)
    user_limit = limit * 3
    # TODO user user_history
    sql = """SELECT uh.id, uh.id_type, time_played, percent_played, count(*)
             FROM user_history uh,
                  users u
             WHERE u.uid IN ({uids}) AND
                   uh.uid = u.uid
             GROUP BY uh.id, uh.id_type, uh.time_played, uh.percent_played
             ORDER BY time_played DESC
             LIMIT {limit}""".format(
                    limit=limit,
                    uids=",".join(uids)
             )

    res = get_results_assoc_dict(sql)
    if not convert_to_fobj:
        return res
    results = []
    for r in res:
        results.append(get_fobj(**r))
    return results

def time_to_cue_netcast(listeners=None):
    listeners = _listeners(listeners)
    recent = get_recently_played(listeners=listeners)
    cue = True
    for r in recent:
        if r.get('id_type') == 'e':
            cue = False
            break
    return cue

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

def get_most_recent(**sql_args):
    target_type = sql_args.get('target_type', 'f')
    target_key = sql_args.get('target_key', 'fid')
    sql_args['id'] = sql_args.get(target_key)
    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s
             ORDER BY time_played DESC
             LIMIT 1"""
    most_recent = get_assoc_dict(sql, sql_args)
    if most_recent.get('id') == sql_args.get(target_key):
        return most_recent

    # This one makes sure it hasn't been played today.
    sql = """SELECT *
             FROM user_history
             WHERE uid = %(uid)s AND
                   id = %(id)s AND
                   id_type = %(target_type)s AND
                   date_played = %(date_played)s
             LIMIT 1"""
    return get_assoc_dict(sql, sql_args)

def get_uids(listeners=None):
    listeners = _listeners(listeners)
    uids = []
    for listener in listeners:
        uids.append(str(int(listener['uid'])))
    return uids

def get_unlistend_episode(listeners=None):
    print "GET_unlistend_episode"
    listeners = _listeners(listeners)
    uids = get_uids(listeners)

    if not uids:
        return None

    sql = """SELECT *
             FROM netcast_episodes ne 
                  LEFT JOIN netcast_listend_episodes nle ON 
                            nle.eid = ne.eid,
                  netcast_subscribers ns
             WHERE ns.uid IN ({uids}) AND
                   ne.nid = ns.nid AND
                   nle.uid IS NULL
             ORDER BY ne.pub_date DESC
             LIMIT 1""".format(uids=",".join(uids))
    res = get_assoc_dict(sql)
    if res != {}:
        from netcast_episode_class import Netcast_FObj
        return Netcast_FObj(**res)
    return None


def get_expired_netcasts():
    sql = """SELECT * 
             FROM netcasts
             WHERE expire_time <= NOW() OR expire_time IS NULL"""
    return get_results_assoc_dict(sql)

def utcnow():
    return datetime.utcnow().replace(tzinfo=pytz.utc)
