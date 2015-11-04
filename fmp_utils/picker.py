
import sys
sys.path.append('../')

from fmp_utils.db_session import Session, session_scope
from models.file import File
from models.user import User
from models.user_file_info import UserFileInfo
from models.pick_from import PickFrom
from models.preload import Preload
from sqlalchemy.sql import not_, and_, text
from random import shuffle
from collections import defaultdict
from pprint import pprint
from fmp_utils.jobs import jobs
import math

true_score_pool = defaultdict(list)

def build_truescore_list():
    scores = []
    for i in range(0, 11):
        for score in range(0, i+1):
            scores.append(i*10)

    shuffle(scores)
    return scores


def get_preload(uids=[]):

    results = []
    with session_scope() as session:
        user_query = session.query(User)
        if uids:
            user_query = user_query.filter(User.id.in_(uids))
        else:
            user_query = user_query.filter(User.listening==True)

        users = user_query.all()

        if not users:
            users = session.query(User).all()

        for user in users:
            session.add(user)
            total = session.query(Preload)\
                           .filter(Preload.user_id==user.id)\
                           .count()

            if total == 0:
                session.add(user)
                populate_preload([user])
            session.add(user)
            total = session.query(Preload)\
                           .filter(Preload.user_id==user.id)\
                           .count()
            if total == 0:
                continue

            pick, preload = session.query(File, Preload)\
                           .join(Preload, Preload.file_id == File.id)\
                           .filter(Preload.user_id==user.id)\
                           .order_by(Preload.from_search.desc(), Preload.id)\
                           .first()

            if pick:
                pick.reason = preload.reason
                session.add(pick)
                session.commit()

                results.append(pick)
                session.delete(preload)
                session.commit()

    return results

def get_recently_played(limit=1):
    file = None
    with session_scope() as session:
        file = session.query(File)\
                      .filter(File.time_played!=None)\
                      .order_by(File.time_played.desc())\
                      .limit(limit)\
                      .all()
    return file

def populate_pick_from(user_id=None, truncate=False):
    with session_scope() as session:
        if user_id is None:
            truncate = True

        if truncate:
            session.execute(text("TRUNCATE pick_from"))
            session.execute(text("""INSERT INTO pick_from (file_id)
                                    SELECT id
                                    FROM files"""))
            session.commit()

            # Remove the last 100 songs that have been played
            # note, some files don't have an artist.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT id
                                         FROM files
                                         WHERE time_played IS NOT NULL
                                         ORDER BY time_played DESC
                                         LIMIT 100
                                    )"""))

            # remove the last 50 artists
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM artist_association
                                         WHERE artist_id IN (
                                             SELECT artist_id
                                             FROM artist_association
                                             WHERE file_id IN (
                                                   SELECT id
                                                   FROM files
                                                   WHERE time_played IS NOT NULL
                                                   ORDER BY time_played DESC
                                                   LIMIT 50
                                             )
                                        )
                                   )"""))

            # remove disabled genres
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM genre_association
                                         WHERE genre_id IN (
                                               SELECT id
                                               FROM genres
                                               WHERE enabled = false
                                         )
                                    )"""))

        if user_id is not None:
            # Remove files rated 0
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM user_file_info
                                         WHERE rating = 0 AND
                                               user_id = :user_id
                                    )"""),
                            {"user_id": user_id})

            # Remove files that are already in the preload for that user.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                        SELECT file_id
                                         FROM preload
                                         WHERE user_id = :user_id
                                    )"""),
                           {"user_id": user_id})

            # Remove the last 100 songs that have been played for the user
            # note, some files don't have an artist.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM user_file_info
                                         WHERE time_played IS NOT NULL AND
                                               user_id = :user_id
                                         ORDER BY time_played DESC
                                         LIMIT 100
                                    )"""),
                            {"user_id": user_id})

            # remove the last 50 artists heard by that user
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM artist_association
                                         WHERE artist_id IN (
                                             SELECT artist_id
                                             FROM artist_association
                                             WHERE file_id IN (
                                                   SELECT file_id
                                                   FROM user_file_info
                                                   WHERE time_played IS NOT NULL AND
                                                         user_id = :user_id
                                                   ORDER BY time_played DESC
                                                   LIMIT 50
                                             )
                                        )
                                   )"""),
                            {"user_id": user_id})

        session.commit()

def insert_random_unplayed_for_user_from_pick_from(user):
    result = None
    with session_scope() as session:
        session.add(user)
        result = session.query(File).from_statement(
            text("""SELECT f.*
                    FROM pick_from pf, files f
                    LEFT JOIN user_file_info usi ON user_id = :user_id AND
                                                    usi.file_id = f.id
                    WHERE usi.file_id IS NULL AND
                          pf.file_id = f.id
                    ORDER BY random()
                    LIMIT 1"""))\
            .params(user_id=user.id)\
            .first()

        remove_file_from_pick_from(result, session)
        if result:
            insert_into_preload(
                    user.id, result.id, "random unplayed for %s" % user.name)
    return result

def insert_random_for_user_true_score_from_pick_from(user, true_score):
    with session_scope() as session:
        session.add(user)
        sql = """SELECT f.*
                 FROM files f,
                      user_file_info ufi,
                      pick_from pf
                 WHERE ufi.file_id = f.id AND
                       ufi.user_id = :user_id AND
                       ufi.true_score >= :true_score AND
                       pf.file_id = f.id
                 ORDER BY f.time_played NULLS FIRST, random()
                 LIMIT 1"""

        result = session.query(File)\
                        .from_statement(text(sql))\
                        .params(user_id=user.id, true_score=true_score)\
                        .first()

        if not result:
            return insert_random_unplayed_for_user_from_pick_from(user)
        session.add(user)
        insert_into_preload(
            user.id, result.id, "%s true_score >= %s" % (user.name, true_score))
        remove_file_from_pick_from(result, session)

    return result

def remove_file_from_pick_from(result, session):
    if not result:
        return
    session.execute(text("""DELETE FROM pick_from
                            WHERE file_id = :file_id"""),
                    {'file_id': result.id })

    session.execute(text("""DELETE FROM pick_from
                            WHERE file_id IN (
                                 SELECT file_id
                                 FROM artist_association
                                 WHERE artist_id IN (
                                     SELECT artist_id
                                     FROM artist_association
                                     WHERE file_id = :file_id
                                )
                           )"""),
                   {'file_id': result.id})
    session.commit()

def insert_into_preload(user_id, file_id, reason="", from_search=False):
    preload = Preload()
    preload.user_id = user_id
    preload.file_id = file_id
    preload.reason = reason
    preload.from_search = from_search
    session.add(preload)
    session.commit()


def populate_preload(users=[]):
    with session_scope() as session:
        populate_pick_from(truncate=True)
        if not users:
            # User list defined, use users who are marked `listening`
            users = session.query(User).filter(User.listening == True).all()

        if not users:
            # No `listening` users were set so grab everyone.
            users = session.query(User).all()


        for user in users:
            session.add(user)
            # Prepare a list that is safe for all our users.
            user_id = user.id
            populate_pick_from(user_id=user_id, truncate=False)

        threashold = math.floor(len(users) / 5)
        if threashold <= 0:
            threashold = 1

        for user in users:
            session.add(user)
            populate_preload_for_user(user, threashold)

def populate_preload_for_user(user, threashold=1):
    with session_scope() as session:
        session.add(user)
        true_score_pool[user.id] = build_truescore_list()
        cnt = 0
        for true_score in true_score_pool[user.id]:
            if cnt <= threashold:
                # always run the first query.
                session.add(user)
                insert_random_unplayed_for_user_from_pick_from(user)
                session.add(user)
                insert_random_for_user_true_score_from_pick_from(user, true_score)
            else:
                # Defer all the other queries.
                session.add(user)
                jobs.append_picker(
                    user.id, insert_random_unplayed_for_user_from_pick_from, user)

                jobs.append_picker(
                    user.id, insert_random_for_user_true_score_from_pick_from, user,
                    true_score)

            cnt += 1
