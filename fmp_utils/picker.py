
import sys
sys.path.append('../')

from fmp_utils.db_session import Session, session_scope
from models.file import File
from models.user import User
from models.user_file_info import UserFileInfo, DEFAULT_RATING,\
                                  DEFAULT_SKIP_SCORE, DEFAULT_TRUE_SCORE
from models.pick_from import PickFrom
from models.preload import Preload
from sqlalchemy.sql import not_, and_, text
from random import shuffle
from collections import defaultdict
from pprint import pprint
from fmp_utils.jobs import jobs
from fmp_utils.misc import session_add
import math

true_score_pool = defaultdict(list)

def insert_missing_user_file_info_for_user_id(user_id):
    with session_scope() as session:
        sql = """INSERT INTO user_file_info (file_id, user_id, rating,
                                             skip_score, true_score)
                     SELECT f.id, :user_id, :rating, :skip_score, :true_score
                     FROM files f
                     WHERE id NOT IN (
                        SELECT file_id
                        FROM user_file_info ufi
                        WHERE user_id = :user_id
                     )"""

        print ("SQL:", sql)
        spec = {
            "user_id": user_id,
            "rating": DEFAULT_RATING,
            "skip_score": DEFAULT_SKIP_SCORE,
            "true_score": DEFAULT_TRUE_SCORE
        }
        print ("spec:", spec)
        session.execute(text(sql), spec)
        session.commit()

def build_truescore_list(user_id):
    scores = []

    with session_scope() as session:
        true_scores = session.query(UserFileInfo.true_score)\
                             .filter(and_(
                                    UserFileInfo.user_id==user_id,
                                    UserFileInfo.true_score >= 0
                                  ))\
                             .distinct()\
                             .all()

        minimum = 0
        for true_score in true_scores:
            true_score = true_score[0]
            print("true_score:", true_score)
            tmp = math.ceil(true_score * 0.1)
            if tmp <= 0:
                tmp = 1
            for i in range(0, tmp):
                true_score = int(true_score)
                if true_score % 10 == 0:
                    scores.append(true_score)

        if scores:
            scores.sort()
            print("SCORES:", scores)
            shuffle(scores)
            return scores

    for i in range(0, 11):
        for score in range(0, i+1):
            scores.append(i*10)
    shuffle(scores)
    return scores


def get_preload(uids=[], remove_item=True, user_ids=[], minimum=0,
                primary_user_id=None, prefetch_num=None,
                secondary_prefetch_num=None):
    if user_ids:
        uids = user_ids

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

        needs_populated = []

        for user in users:
            session_add(session, user)
            if primary_user_id is not None:
                if user.id == primary_user_id:
                    minimum = prefetch_num
                if user.id != primary_user_id:
                    minimum = secondary_prefetch_num

            total = session.query(Preload)\
                           .filter(Preload.user_id==user.id)\
                           .count()

            if total <= minimum:
                needs_populated.append(user)

        if needs_populated:
            populate_preload(users,
                             primary_user_id=primary_user_id,
                             prefetch_num=prefetch_num,
                             secondary_prefetch_num=secondary_prefetch_num)

        for user in users:
            session_add(session, user)
            # This code isn't needed because it's ok if we get an item.
            # total = session.query(Preload)\
            #                .filter(Preload.user_id==user.id)\
            #                .count()
            # if total <= minimum:
            #    continue

            pick, preload = session.query(File, Preload)\
                                   .join(Preload, Preload.file_id == File.id)\
                                   .filter(Preload.user_id==user.id)\
                                   .order_by(Preload.from_search.desc(), Preload.id)\
                                   .first()

            if pick:
                pick.reason = preload.reason
                session_add(session, pick, commit=True)
                results.append(pick)
                if remove_item:
                    session.delete(preload)
                session.commit()

    return results

def get_recently_played(limit=1):
    files = None
    with session_scope() as session:
        files = session.query(File)\
                      .filter(File.time_played!=None)\
                      .order_by(File.time_played.desc())\
                      .limit(limit)\
                      .all()
        files.reverse()
    return files


def remove_duplicate_entries(user_id):
    print("remove_duplicate_entries user_id:", user_id)
    with session_scope() as session:
        sql = """SELECT file_id, count(*)
                 FROM user_file_info
                 WHERE user_id = :user_id
                 GROUP BY file_id HAVING count(*) > 1"""

        print ("SQL:", sql)
        spec = {
            "user_id": user_id
        }
        print ("spec:", spec)
        result = session.execute(text(sql), spec)

        for d in result:
            print("DUP:", d)
            file_id = d.file_id
            entries = session.query(UserFileInfo)\
                .filter(and_(
                    UserFileInfo.file_id==file_id,
                    UserFileInfo.user_id==user_id
                )).all()
            use_entry = None
            for e in entries:
                if use_entry is None:
                    use_entry = e
                    continue

                if e.rating != 6 and use_entry.rating == 6:
                    use_entry = e
                    continue

                if not e.time_played and use_entry.time_played:
                    use_entry = e
                    continue

                if e.time_played and use_entry.time_played and \
                   e.time_played > use_entry.time_played:
                    use_entry = e
                    continue


            if use_entry is None:
                continue

            print("USE:", use_entry)
            print("rating:", use_entry.rating)
            print("true_score:", use_entry.true_score)
            print("skip_score:", use_entry.skip_score)

            spec['id'] = use_entry.id
            spec['user_id'] = use_entry.user_id
            spec['file_id'] = use_entry.file_id
            spec['user_file_id'] = use_entry.id
            print(spec)
            sql = """UPDATE user_file_history
                     SET user_file_id = :user_file_id
                     WHERE user_id = :user_id AND
                           file_id = :file_id"""

            session.execute(text(sql), spec)
            session.commit()

            print (sql)

            sql = """DELETE FROM user_file_history
                     WHERE user_id = :user_id AND
                           file_id = :file_id AND
                           user_file_id != :user_file_id"""

            session.execute(text(sql), spec)
            session.commit()

            print (sql)

            sql = """DELETE FROM user_file_info
                     WHERE file_id = :file_id AND
                           user_id = :user_id AND
                           id != :id"""

            session.execute(text(sql), spec)
            session.commit()

            print (sql)

def populate_pick_from(user_id=None, truncate=False):
    with session_scope() as session:
        if user_id is None:
            truncate = True
        spec = {
            "user_id": user_id
        }
        insert_missing_user_file_info_for_user_id(user_id)
        remove_duplicate_entries(user_id)
        if truncate:
            session.execute(text("""DELETE FROM pick_from
                                    WHERE user_id = :user_id""",
                                    ),
                            spec)
            session.execute(text("""INSERT INTO pick_from (file_id, user_id)
                                    SELECT id, :user_id
                                    FROM files"""),
                            spec)
            session.commit()

            # Remove the last 100 songs that have been played
            # note, some files don't have an artist.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM user_file_info ufi
                                         WHERE time_played IS NOT NULL AND
                                               user_id = :user_id
                                         ORDER BY time_played DESC NULLS LAST
                                         LIMIT 200
                                    ) AND
                                    user_id = :user_id"""),
                            spec)

            # remove the last 50 artists
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM artist_association
                                         WHERE artist_id IN (
                                             SELECT artist_id
                                             FROM artist_association
                                             WHERE file_id IN (
                                                   SELECT file_id
                                                   FROM user_file_info ufi
                                                   WHERE time_played IS NOT NULL AND
                                                         user_id = :user_id
                                                   ORDER BY time_played DESC NULLS LAST
                                                   LIMIT 50
                                             )
                                        )
                                   )"""),
                            spec)

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
                                    ) AND user_id = :user_id"""),
                            spec)

        if user_id is not None:
            # Remove files rated 0
            #session.execute(text("""DELETE FROM pick_from
            #                        WHERE file_id IN (
            #                             SELECT file_id
            #                             FROM user_file_info
            #                             WHERE rating = 0 AND
            #                                   user_id = :user_id
            #                        )"""),
            #                {"user_id": user_id})

            # Remove files that are already in the preload for that user.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                        SELECT file_id
                                         FROM preload
                                         WHERE user_id = :user_id
                                    )"""),
                           spec)

            # Remove the last 100 songs that have been played for the user
            # note, some files don't have an artist.
            session.execute(text("""DELETE FROM pick_from
                                    WHERE file_id IN (
                                         SELECT file_id
                                         FROM user_file_info
                                         WHERE time_played IS NOT NULL AND
                                               user_id = :user_id
                                         ORDER BY time_played DESC NULLS LAST
                                         LIMIT 100
                                    )"""),
                            spec)

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
                            spec)

        session.commit()

def insert_random_unplayed_for_user_from_pick_from(user):
    result = None
    with session_scope() as session:
        session_add(session, user)
        user_id = user.id
        result = session.query(File).from_statement(
            text("""SELECT f.*
                    FROM pick_from pf, files f
                    LEFT JOIN user_file_info ufi ON user_id = :user_id AND
                                                    ufi.file_id = f.id
                    WHERE (ufi.user_id = :user_id AND
                           pf.file_id = f.id AND
                           pf.user_id = :user_id AND
                           ufi.time_played IS NULL)
                          OR
                          (ufi.file_id IS NULL AND
                           pf.file_id = f.id AND
                           pf.user_id = :user_id)
                    ORDER BY random()
                    LIMIT 1"""))\
            .params(user_id=user_id)\
            .first()
        session_add(session, user)
        remove_file_from_pick_from(result, session, user_id=user_id)
        if result:
            session_add(session, user)
            insert_into_preload(
                    user_id, result.id, "random unplayed for %s" % user.name)
    return result

def insert_random_for_user_true_score_from_pick_from(user, true_score):
    with session_scope() as session:
        session_add(session, user)
        user_id = user.id
        user_name = user.name
        sql = """SELECT f.*, ufi.time_played
                 FROM files f,
                      user_file_info ufi,
                      pick_from pf
                 WHERE ufi.file_id = f.id AND
                       ufi.user_id = :user_id AND
                       ufi.true_score >= :true_score AND
                       pf.file_id = f.id AND
                       ufi.rating > 0 AND
                       pf.user_id = ufi.user_id
                 ORDER BY ufi.time_played NULLS FIRST,
                          f.time_played NULLS FIRST,
                          random()
                 LIMIT 1"""

        result = session.query(File)\
                        .from_statement(text(sql))\
                        .params(user_id=user_id, true_score=true_score)\
                        .first()

        if not result:
            return insert_random_unplayed_for_user_from_pick_from(user)
        session_add(session, user)
        insert_into_preload(
            user_id, result.id, "%s true_score >= %s" % (user_name, true_score))
        remove_file_from_pick_from(result, session, user_id=user_id)

    return result

def remove_file_from_pick_from(result, session, user_id=None):
    if not result:
        return
    session_add(session, result)
    if not user_id:
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
    else:
        spec = {
            'file_id': result.id,
            'user_id': user_id
        }
        session.execute(text("""DELETE FROM pick_from
                                WHERE file_id = :file_id AND
                                      user_id = :user_id"""),
                        spec)

        session.execute(text("""DELETE FROM pick_from
                                WHERE file_id IN (
                                     SELECT file_id
                                     FROM artist_association
                                     WHERE artist_id IN (
                                         SELECT artist_id
                                         FROM artist_association
                                         WHERE file_id = :file_id
                                    )
                               ) AND
                               user_id = :user_id"""),
                       spec)
    session.commit()

def insert_into_preload(user_id, file_id, reason="", from_search=False):
    with session_scope() as session:
        preload = Preload()
        preload.user_id = user_id
        preload.file_id = file_id
        preload.reason = reason
        preload.from_search = from_search
        session_add(session, preload, commit=True)


def populate_preload(users=[], primary_user_id=None, prefetch_num=None,
                     secondary_prefetch_num=None):
    with session_scope() as session:
        # populate_pick_from(truncate=True)
        if not users:
            # User list defined, use users who are marked `listening`
            users = session.query(User).filter(User.listening == True).all()

        if not users:
            # No `listening` users were set so grab everyone.
            users = session.query(User).all()


        for user in users:
            session_add(session, user)
            # Prepare a list that is safe for all our users.
            user_id = user.id
            populate_pick_from(user_id=user_id, truncate=True)

        threashold = math.floor(len(users) / 5)
        if threashold <= 0:
            threashold = 1

        for user in users:
            session_add(session, user)
            if primary_user_id is not None:
                if user.id == primary_user_id:
                    if prefetch_num is not None:
                        try:
                            threashold = int(prefetch_num)
                        except:
                            threashold = 50
                    else:
                        threashold = 50
                else:
                    if secondary_prefetch_num is not None:
                        try:
                            threashold = int(secondary_prefetch_num)
                        except:
                            threashold = 10
                    else:
                        threashold = 10

            populate_preload_for_user(user, threashold)

def populate_preload_for_user(user, threashold=1):
    with session_scope() as session:
        session_add(session, user)
        user_id = user.id
        true_score_pool[user_id] = build_truescore_list(user_id)
        session_add(session, user)
        cnt = 0
        if threashold <= 0:
            threashold = 1

        session_add(session, user)
        for true_score in true_score_pool[user.id]:
            if cnt <= threashold:
                # Run queries up to the threashold.
                session_add(session, user)
                insert_random_unplayed_for_user_from_pick_from(user)
                session_add(session, user)
                insert_random_for_user_true_score_from_pick_from(user, true_score)
            else:
                # Defer all the other queries.
                session_add(session, user)
                jobs.append_picker(
                    user.id, insert_random_unplayed_for_user_from_pick_from, user)

                session_add(session, user)
                jobs.append_picker(
                    user.id, insert_random_for_user_true_score_from_pick_from, user,
                    true_score)

            cnt += 1
