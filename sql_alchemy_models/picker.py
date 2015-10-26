from db_session import session
from file import User, UserFileInfo, File
from sqlalchemy.sql import not_, and_, text
from random import shuffle
from collections import defaultdict
from pprint import pprint


def build_truescore_list():
    scores = []
    for i in range(0, 11):
        for score in range(0, i+1):
            scores.append(i*10)

    shuffle(scores)
    return scores

def get_random_unplayed_for_user_id(user_id):
    result = session.query(File).from_statement(
        text("""SELECT f.*
           FROM files f
           LEFT JOIN user_file_info usi ON user_id = :user_id AND
                                           usi.file_id = f.id
           WHERE usi.file_id IS NULL
           ORDER BY random()
           LIMIT 1 """))\
        .params(user_id=user_id)
    return result.first()


def get_random_for_user_id_true_score(user_id, true_score):
    result = session.query(File).from_statement(
        text("""SELECT f.*
                FROM files f, user_file_info ufi
                WHERE ufi.file_id = f.id AND
                      ufi.user_id = :user_id AND
                      ufi.true_score >= :true_score
                ORDER BY time_played, random()
                LIMIT 1"""))\
        .params(user_id=user_id,
                true_score=true_score)
    return result.first()

def get_preload(uids=[]):
    results = []
    query = session.query(User)
    if uids:
        query.filter(User.id.in_(uids))
    else:
        query.filter(User.listening==True)

    for user in query.all():
        pick = get_random_unplayed_for_user_id(user.id)
        if pick:
            results.append(pick)

        if not true_score_pool.get(user.id):
            true_score_pool[user.id] = build_truescore_list()

        true_score = true_score_pool[user.id].pop()
        pick = get_random_for_user_id_true_score(user.id, true_score)
        if not pick:
            while true_score in true_score_pool[user.id]:
                true_score_pool[user.id].remove(true_score)
            continue
        results.append(pick)

    return results

users = ['erm', 'steph', 'sam', 'halle']
true_score_pool = defaultdict(list)

for name in users:
    user = session.query(User).filter(User.name == name).first()

    if not user:
        user = User()
        user.name = name
        session.add(user)
        session.commit()

pprint(get_preload())

