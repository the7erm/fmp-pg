
import os
import sys
import json
from time import time
from datetime import date, datetime
import cherrypy
from cherrypy.lib.static import serve_file
import configparser
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage, BinaryMessage

sys.path.append("../")
from fmp_utils.db_session import session_scope, Session
from fmp_utils.misc import to_bool, session_add
from fmp_utils.first_run import first_run, check_config
from fmp_utils.constants import CONFIG_DIR, CONFIG_FILE, VALID_EXT
from models.base import to_json
from models.user import User
from models.file import File
from models.location import Location
from models.folder import Folder, scan_folder
from models.user_file_info import UserFileInfo
from models.preload import Preload
from models.artist import Artist
from models.album import Album
from models.genre import Genre
from models.user import get_users
from models.user_file_history import UserFileHistory
from sqlalchemy.sql import not_, text, and_, func
from sqlalchemy.exc import InvalidRequestError
import subprocess
from pprint import pprint, pformat
import shlex
import re

hostname = subprocess.check_output(['hostname'])
hostname = hostname.strip()

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

MEDIA_NONE = 0
MEDIA_STARTING = 1
MEDIA_RUNNING = MEDIA_PLAYING = 2
MEDIA_PAUSED = 3
MEDIA_STOPPED = 4

class ChatWebSocketHandler(WebSocket):
    def received_message(self, m):
        try:
            playlist.broadcast_playing()
        except NameError:
            print("Playlist not initialized")
            pass
        #  print ("json.loads()", json.loads(str_mdata))

        # cherrypy.engine.publish('websocket-broadcast', m)

    def opened(self):
        print("****"*10)
        print ("OPENED")
        # return json.dumps(playlist.json())

    def closed(self, code, reason="A client left the room without a proper explanation."):
        cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

cherrypy.config.update({
    'server.socket_port': 5050,
    'server.socket_host': '0.0.0.0',
    'tools.encode.on': True,
    'tools.encode.encoding': 'utf-8',
    '/ws': {
        'tools.websocket.on': True,
        'tools.websocket.handler_cls': ChatWebSocketHandler
    }
})


class FmpServer(object):
    @cherrypy.expose
    def index(self):

        template_data = {
            'host': cherrypy.request.headers['Host'],
            'scheme': 'ws',
            'playlist_data': []
        }
        static_path = sys.path[0]
        index_path = os.path.join(static_path, "server", "templates",
                                  "index.html")
        data = "Error"
        with open(index_path, 'r') as fp:
            data = fp.read()
        return data % template_data

    @cherrypy.expose
    def set_listening(self, user_id, listening, *args, **kwargs):
        with session_scope() as session:
            user = session.query(User)\
                          .filter(User.id==user_id)\
                          .first()

            if user:
                user.listening = to_bool(listening)
                session.commit()
                session.add(user)
                if user.listening:
                    playlist.populate_preload([user.id])

        playlist.broadcast_playing()
        return self.listeners()

    @cherrypy.expose
    def set_admin(self, user_id, admin, *args, **kwargs):
        with session_scope() as session:
            user = session.query(User)\
                          .filter(User.id==user_id)\
                          .first()

            admin = to_bool(admin)

            if user:
                user.admin = admin
            session_add(session, user, commit=True)

        return self.listeners()

    @cherrypy.expose
    def ws(self):
        # you can access the class instance through
        handler = cherrypy.request.ws_handler

    @cherrypy.expose
    def set_score(self, *args, **kwargs):

        file_id = int(kwargs.get('file_id'))
        user_id = int(kwargs.get('user_id'))
        skip_score = int(kwargs.get('skip_score', 5))

        return self.set_rating_or_score(file_id, user_id, 'skip_score', skip_score)

    @cherrypy.expose
    def rate(self, *args, **kwargs):
        file_id = int(kwargs.get('file_id'))
        user_id = int(kwargs.get('user_id'))
        rating = int(kwargs.get('rating', 6))
        return self.set_rating_or_score(file_id, user_id, 'rating', rating)

    @cherrypy.expose
    def set_rating_or_score(self, file_id, user_id, attr, value):

        user_file_info = self.get_user_file_info(file_id, user_id)
        with session_scope() as session:
            session_add(session, user_file_info)
            setattr(user_file_info, attr, value)
            user_file_info.calculate_true_score()
            session.commit()
            response = json_dumps(user_file_info.json(history=True))
            playlist.broadcast_playing()
        return response

    def get_user_file_info(self, file_id, user_id):
        with session_scope() as session:
            user_file_info = None
            playing_file = playlist.files[playlist.index]
            session_add(session, playing_file)
            for ufi in playing_file.user_file_info:
                session_add(session, ufi)
                if ufi.file_id != file_id:
                    break
                if ufi.user_id == user_id:
                    user_file_info = ufi
                    break;

            if not user_file_info:
                user_file_info = session.query(UserFileInfo)\
                                        .filter(and_(
                                            UserFileInfo.file_id==file_id,
                                            UserFileInfo.user_id==user_id
                                        ))\
                                        .first()
        return user_file_info


    @cherrypy.expose
    def mark_as_played(self, *args, **kwargs):
        with session_scope() as session:
            f = session.query(File)\
                       .filter(File.id==kwargs.get('file_id'))\
                       .first()
            session.add(f)
            mark_as_played_kwargs = {
                "user_ids": [kwargs.get('user_id')],
                "percent_played": kwargs.get("percent_played", 0),
                "now": int(kwargs.get("now", time()))
            }
            f.mark_as_played(**mark_as_played_kwargs)
            cue_kwargs = {
                "id": kwargs.get("file_id"),
                "uid": kwargs.get("user_id"),
                "cued": False
            }
            self.cue(**cue_kwargs)
            session.add(f)
            response = f.json()
            preload = []
            for p in playlist.preload:
                session.add(p)
                if p.id != kwargs.get("file_id"):
                    preload.append(p)
            playlist.preload = preload
            return response

    @cherrypy.expose
    def next(self):
        playlist.next()
        return "Next"

    @cherrypy.expose
    def prev(self):
        playlist.prev()
        return "Prev"

    @cherrypy.expose
    def pause(self):
        playlist.pause()
        # broadcast({"state-changed": playlist.player.state_string })
        return "pause"

    @cherrypy.expose
    def vote_to_skip(self, *args, **kwargs):
        playing_file = playlist.files[playlist.index]
        with session_scope() as session:
            session_add(session, playing_file)
            file_id = kwargs.get('file_id')
            user_id = kwargs.get('user_id')
            voted_to_skip = to_bool(kwargs.get('voted_to_skip'))
            print("VOTED TO SKIP:", voted_to_skip)
            if playing_file.id == file_id:
                found = False
                for ufi in playing_file.user_file_info:
                    if ufi.user_id == user_id:
                        found = True
                        ufi.voted_to_skip = voted_to_skip
                        break
                if not found:
                    ufi = playing_file.create_ufi(user_id)
                    ufi.voted_to_skip = voted_to_skip
            else:
                ufi = session.query(UserFileInfo)\
                             .filter(and_(
                                 UserFileInfo.file_id==file_id,
                                 UserFileInfo.user_id==kwargs.get('user_id')
                             ))\
                             .first()
                session_add(session, ufi)
                ufi.voted_to_skip = voted_to_skip

            session_add(session, ufi, commit=True)
            if voted_to_skip:
                playlist.skip_countdown = 5
            playlist.broadcast_playing()
            print("VOTED TO SKIP")

    @cherrypy.expose
    def genres(self, *args, **kwargs):
        with session_scope() as session:
            genres = session.query(Genre)
            name = kwargs.get('name')
            if name:
                genres = genres.filter(Genre.name.ilike("%s%%" % name))
            genres = genres.order_by(Genre.name).all()
            return json_dumps([g.json() for g in genres])

    @cherrypy.expose
    def tags(self, *args, **kwargs):
        word = kwargs.get('word')
        hard_limit = 8
        word_len = len(word)
        lower_search = 3
        with session_scope() as session:
            results = []
            limit = hard_limit
            artists = session.query(Artist)\
                             .filter(and_(
                                Artist.name.ilike("%s%%" % word),
                                func.length(Artist.name) < (
                                    word_len + lower_search)
                              ))\
                             .order_by(Artist.name)\
                             .limit(limit)
            results = [a.name for a in artists]
            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                genres = session.query(Genre)\
                             .filter(and_(
                                Genre.name.ilike("%s%%" % word),
                                func.length(Genre.name) < (
                                    word_len + lower_search)
                              ))\
                             .order_by(Genre.name)\
                             .limit(limit)
                results += [g.name for g in genres]
                results = list(set(results))

            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                albums = session.query(Album)\
                             .filter(and_(
                                Album.name.ilike("%s%%" % word),
                                func.length(Album.name) < (word_len + lower_search)
                              ))\
                             .order_by(Album.name)\
                             .limit(limit)
                results += [a.name for a in albums]
                results = list(set(results))

            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                artists = session.query(Artist)\
                                 .filter(Artist.name.ilike("%s%%" % word))\
                                 .order_by(Artist.name)\
                                 .limit(limit)
                results += [a.name for a in artists]
                results = list(set(results))

            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                genres = session.query(Genre)\
                             .filter(Genre.name.ilike("%s%%" % word))\
                             .order_by(Genre.name)\
                             .limit(limit)
                results += [g.name for g in genres]
                results = list(set(results))

            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                albums = session.query(Album)\
                             .filter(Album.name.ilike("%s%%" % word))\
                             .order_by(Album.name)\
                             .limit(limit)
                results += [a.name for a in albums]
                results = list(set(results))

            return json_dumps(results)


    @cherrypy.expose
    def genre_enabled(self, *args, **kwargs):
        session = Session()
        genre = session.query(Genre)\
                       .filter(Genre.id==kwargs.get('id'))\
                       .first()

        genre.enabled = to_bool(kwargs.get('enabled'))
        session.commit()

    @cherrypy.expose
    def add_genre(self, *args, **kwargs):
        params = cherrypy.request.params
        print("PARAMS:")
        pprint(params)
        file_id = params.get('file_id')
        genre_name = params.get("genre", "").strip()
        if not genre_name:
            return json_dumps({
                "RESULT": "FAIL",
                "Error":"Empty genre name:%s" % genre_name
            })
        with session_scope() as session:
            file = session.query(File)\
                          .filter(File.id==file_id)\
                          .first()
            if not file:
                return json_dumps({
                    "RESULT": "FAIL",
                    "Error":"No file found for file_id:%s" % file_id
                })
            genre = session.query(Genre)\
                           .filter(Genre.name==genre_name)\
                           .first()
            if not genre:
                genre = Genre()
                genre.name = genre_name
                genre.enabled = True
                session_add(session, genre, commit=True)
            session_add(session, file)
            found = False
            for g in file.genres:
                if g.id == genre.id:
                    found = True
                    break
            if not found:
                file.genres.append(genre)
                session.commit()

        return json_dumps({"RESULT": "OK"})

    @cherrypy.expose
    def remove_genre(self, *args, **kwargs):
        params = cherrypy.request.params
        print("PARAMS:")
        pprint(params)
        file_id = params.get('file_id')
        genre_name = params.get("genre", "").strip()
        if not genre_name:
            return json_dumps({
                "RESULT": "FAIL",
                "Error":"Empty genre name:%s" % genre_name
            })

        with session_scope() as session:
            file = session.query(File)\
                          .filter(File.id==file_id)\
                          .first()
            if not file:
                return json_dumps({
                    "RESULT": "FAIL",
                    "Error":"No file found for file_id:%s" % file_id
                })
            genre = session.query(Genre)\
                           .filter(Genre.name==genre_name)\
                           .first()
            if not genre:
                genre = Genre()
                genre.name = genre_name
                genre.enabled = True
                session_add(session, genre, commit=True)
            session_add(session, file)
            found = False
            for g in file.genres:
                if g.id == genre.id:
                    file.genres.remove(g)
            session.commit()

        return json_dumps({"RESULT": "OK"})


    @cherrypy.expose
    def listeners(self, *args, **kwargs):
        with session_scope() as session:
            users = session.query(User)\
                           .order_by(User.listening.desc().nullslast(),
                                     User.admin.desc().nullslast(),
                                     User.name.nullslast())\
                           .all()
            results = []
            for u in users:
                results.append(u.json())
        return json_dumps(results)

    @cherrypy.expose
    def preload(self, *args, **kwargs):
        params = cherrypy.request.params
        user_ids = self.get_user_ids(user_ids=kwargs.get('user_ids', []))
        user_sql = """SELECT user_id AS id
                      FROM preload
                      WHERE user_id IN(%s)
                      GROUP BY user_id"""  % ",".join(user_ids)

        sql = """SELECT f.*
                 FROM files f,
                      preload p
                 WHERE user_id IN (%s) AND
                       f.id = p.file_id
                 ORDER BY p.from_search DESC, p.id ASC""" % ",".join(user_ids)

        results = []
        preload_user_ids = []
        with session_scope() as session:
            user_count = session.query(User)\
                                .from_statement(
                                    user_sql)\
                                .all()

            for user_id in user_ids:
                found = False
                for user in user_count:
                    session.add(user)
                    if str(user.id) == user_id:
                        found = True
                        break
                if not found:
                    preload_user_ids.append(user_id)

            if preload_user_ids:
                preloaded = picker.get_preload(preload_user_ids)
                for p in preloaded:
                    results.append(p.json(user_ids=user_ids))

            files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()
            for f in files:
                results.append(f.json(user_ids=user_ids))

        if not kwargs.get("raw"):
            return json_dumps(results)

        return results


    def get_user_ids(self, *args, **kwargs):
        user_ids = []
        with session_scope() as session:
            params = cherrypy.request.params
            users = get_users(user_ids=kwargs.get('user_ids', []))
            for u in users:
                session_add(session, u)
                user_ids.append(str(u.id))
            users = get_users(user_ids=params.get('user_ids', []))
            for u in users:
                session_add(session, u)
                u_id = str(u.id)
                if u_id not in user_ids:
                    user_ids.append(u_id)

        return user_ids


    @cherrypy.expose
    def search(self, *args, **kwargs):
        with session_scope() as session:
            params = cherrypy.request.params
            if 'params' in kwargs:
                params = kwargs.get("params")

            cherrypy.log(("+"*20)+" SEARCH "+("+"*20))
            cherrypy.log("search: kwargs:%s" % ( kwargs,))
            start = int(params.get("s", 0))
            limit = int(params.get("l", 10))
            only_cued = params.get('oc', False)
            owner = params.get("owner",'')
            try:
                uid = int(params.get('uid', 0))
            except:
                uid = 0

            only_cued = to_bool(only_cued)

            q = params.get("q", '').strip()
            query_offset = "LIMIT %d OFFSET %d" % (limit, start)
            query_args = {}
            query_spec = {
              "SELECT": ["""f.*"""],
              "FROM": ["""files f"""],
              "COUNT_FROM": ["files f"],
              "ORDER_BY": [],
              "WHERE": [],
              "WHERERATINGSCORE": [],
            }

            query_base = """SELECT {SELECT}
                            FROM {FROM}
                            WHERE {WHERE}
                            ORDER BY {ORDER_BY}
                            {query_offset}"""

            query_base_count = """SELECT count(*) AS total
                                  FROM {COUNT_FROM}
                                  WHERE {WHERE}"""

            if only_cued:
                user_ids = self.get_user_ids(user_ids=kwargs.get('user_ids', []))
                USER_IDS = ",".join(user_ids)
                query_spec["FROM"].append("preload p")
                query_spec["COUNT_FROM"].append("preload p")
                query_spec["WHERE"].append("f.id = p.file_id AND "
                                           "p.user_id IN ({USER_IDS})".format(
                                                USER_IDS=USER_IDS
                                          ))
                query_spec['ORDER_BY'].append("from_search DESC NULLS LAST, p.id")

            if q:
                query_spec["SELECT"].append("ts_rank_cd(to_tsvector('english', keywords_txt), query) AS rank")
                count_from = """plainto_tsquery('english', :q) query"""
                query_spec["FROM"].append(count_from)
                query_spec["COUNT_FROM"].append(count_from)
                query_spec["WHERE"].append("query @@ to_tsvector('english', keywords_txt)")
                query_args['q'] = q
                query_spec['ORDER_BY'].append("rank DESC")

            query_spec['ORDER_BY'].append("time_played DESC NULLS LAST")

            search_query = query_base.format(
                SELECT=",".join(query_spec['SELECT']),
                FROM=",".join(query_spec['FROM']),
                WHERE=" AND ".join(query_spec['WHERE']),
                ORDER_BY=",".join(query_spec['ORDER_BY']),
                query_offset=query_offset
            )

            count_query = query_base_count.format(
                SELECT=",".join(query_spec['SELECT']),
                COUNT_FROM=",".join(query_spec['COUNT_FROM']),
                WHERE=" AND ".join(query_spec['WHERE']),
                ORDER_BY=",".join(query_spec['ORDER_BY'])
            )

            if not query_spec['WHERE']:
                search_query = search_query.replace("WHERE", '')
                count_query = count_query.replace("WHERE", '')

            print("search_query:", search_query)
            print("count_query:", count_query)

            print ("FETCHING 'files'")
            files = session.query(File)\
                           .from_statement(
                                text(search_query))\
                           .params(**query_args)\
                           .all()

            results = []
            for res in files:
                results.append(res.json(history=True))

            print ("counting total")
            total = session.execute(text(count_query),query_args).first()

            session.close()
            if params.get("raw", False):
                return results

            return json_dumps({
                "results": results,
                "total": total[0]
            })

    @cherrypy.expose
    def users(self, *args, **kwargs):
        return []

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def fmp_version(self):
        return {
            "fmp": 0.01,
            "api": 1,
            "hostname": hostname.decode("utf8")
        }

    @cherrypy.expose
    def cue(self, *args, **kwargs):
        # uid,
        # id
        # cued
        _id = kwargs.get('id')
        user_id = kwargs.get('uid')
        if not user_id:
            user_id = kwargs.get("user_id")
        cued = to_bool(kwargs.get('cued'))
        with session_scope() as session:
            is_cued = session.query(Preload).filter(and_(
                Preload.file_id==_id
            )).first()
            if cued and not is_cued:
                preload = Preload()
                user = session.query(User)\
                              .filter(User.id==user_id)\
                              .first()
                preload.file_id = _id
                preload.user_id = user_id
                preload.reason = "From Search for %s" % user.name
                preload.from_search = True
                session_add(session, preload, commit=True)
            elif not cued and is_cued:
                session_add(session, is_cued)
                session.delete(is_cued)
                session.commit()
        return

    @cherrypy.expose
    def check_install(self):
        return json_dumps(check_config())

    @cherrypy.expose
    def save_config(self, **kwargs):
        cfg = check_config()
        obj = self.load_json()
        print("OBJ:", obj, kwargs)
        cfg['postgres']['config'] = obj
        database = obj.get('database')
        exists = False

        self.write_config(obj)
        cfg = check_config()
        if cfg['postgres']['db_exists'] and \
           cfg['postgres']['can_connect']['connected']:
            from fmp_utils.db_session import fmp_session
            from models.base import Base
            fmp_session.connect()
            fmp_session.create_all(Base)

        return json_dumps(cfg)


    def validate_db_config(self, obj, required=['database', 'username']):
        errors = []
        keys = ['database', 'username', 'host', 'password']
        for k in keys:
            value = obj.get(k, '')
            if value and not re.match("^[A-z0-9\-\_]+$", value):
                errors.append("%s has an invalid character" % k)
            if not value and k in required:
                errors.append("%s requires a value" % k)
        return errors

    @cherrypy.expose
    def create_db(self):
        obj = self.load_json()

        database = obj.get("database", 'fmp')
        username = obj.get('username', '')
        host = obj.get('host', 'localhost')
        password = obj.get('password', '')
        errors = self.validate_db_config(obj)
        if errors:
            return json_dumps({
                "RESULT": "FAIL",
                "Error": ",".join(errors)
            })

        spec = {
            'username': username,
            'database': database
        }

        fp = open("/tmp/create_db.sh",'w')
        fp.write("""!#/bin/sh
        createdb -O %(username)s %(username)s
        createdb -O %(username)s %(database)s
        """ % spec)
        fp.close()
        os.chmod("/tmp/create_db.sh", 0o777)
        try:
            op = [
                'gksu', '-m', 'Create postgres db %s' % database,
                '-u', 'postgres', "/tmp/create_db.sh"]
            print("op:", op)
            self.write_config(obj)
            output = subprocess.check_output(op)
            os.unlink("/tmp/create_db.sh")
            output = output.decode("utf8")
            print("output:",  output)
            self.write_config(obj)
            return json_dumps({"RESULT": "OK",
                               "output": output})
        except:
            err = "%s" % sys.exc_info()[0]
            if 'already exists' in err:
                self.write_config(obj)
            print ("sys.exc_info()[0]:", sys.exc_info()[0], sys.exc_info()[1])

            return json_dumps({"RESULT": "FAIL"})

    def write_config(self, data):
        print("write_config:", data)
        config = configparser.RawConfigParser()

        config.add_section('postgres')
        for k, v in data.items():
            print(k,":",v)
            config.set('postgres', k, v)

        with open(CONFIG_FILE, 'w') as configfile:
            config.write(configfile)
        print("/write_config")

    def load_json(self):
        rawbody = cherrypy.request.body.read()
        obj = json.loads(rawbody.decode("utf8"))
        return obj

    @cherrypy.expose
    def add_user(self):
        obj = self.load_json()
        name = obj.get('name', '').strip()
        if not name:
            return self.listeners()
        with session_scope() as session:
            user = session.query(User)\
                          .filter(User.name == obj['name'])\
                          .first()
            if user:
                return self.listeners()
            user = User()
            user.name = obj.get('name')
            session_add(session, user, commit=True)

        return self.listeners()

    @cherrypy.expose
    def create_role(self):
        obj = self.load_json()
        print("obj:", obj);
        """
        gksudo -m "Create postgres user 'test'" -u postgresql "psql -c '"""

        database = obj.get("database", '')
        username = obj.get('username', '')
        host = obj.get('host', '')
        password = obj.get('password', '')
        errors = self.validate_db_config(obj, ['username'])
        if errors:
            return json_dumps({
                "RESULT": "FAIL",
                "Error": ",".join(errors)
            })

        try:
            if password:
                fp = open("/tmp/create_role.sh",'w')
                fp.write("""!#/bin/sh
                psql -c "CREATE ROLE %s WITH LOGIN ENCRYPTED PASSWORD \'%s\'"
                """ % (username, password))
                fp.close()
            else:
                fp = open("/tmp/create_role.sh",'w')
                fp.write("""!#/bin/sh
                psql -c "CREATE ROLE %s WITH LOGIN"
                """ % (username,))
                fp.close()
            os.chmod("/tmp/create_role.sh", 0o777)
            op = [
                'gksu', '-m', 'Create postgres user %s' % username,
                '-u', 'postgres', "/tmp/create_role.sh"]
            print("op:", op)
            self.write_config(obj)
            output = subprocess.check_output(op)
            if os.path.exists("/tmp/create_role.sh"):
                os.unlink("/tmp/create_role.sh")
            output = output.decode("utf8")
            print("output:",  output)
            return json_dumps({"RESULT": "OK",
                               "output": output})
        except:
            err = "%s" % sys.exc_info()[0]
            if 'already exists' in err:
                self.write_config(obj)
            print ("sys.exc_info()[0]:", sys.exc_info()[0], sys.exc_info()[1])
            if os.path.exists("/tmp/create_role.sh"):
                os.unlink("/tmp/create_role.sh")
            return json_dumps({"RESULT": "FAIL"})

    @cherrypy.expose
    def browse(self, folder):
        with session_scope() as session:
            results = json_dumps(self.get_dirs(folder, 1, session=session))
        return results

    @cherrypy.expose
    def add_folder(self,*args,**kwargs):
        obj = self.load_json()
        print("add_folder()")
        pprint(obj)
        """
        {'children': [],
         'collapsed': True,
         'dirname': 'Amazon MP3',
         'folder_data': {},
         'has_media': True,
         'realpath': '/home/erm/disk2/acer-home/Amazon MP3'}"""
        result = {
            "RESULT": "FAIL",
        }
        realpath = obj.get('realpath', '')
        if not realpath or not os.path.exists(realpath):
            result['Error'] = 'Missing %s' % realpath
            return json_dumps(result)

        scan_folder(realpath, add_to_folder_scanner=True, recurse=2)
        json_dumps({"RESULT": "OK",
                    "msg": "already added"})

        return json_dumps(result)

    def get_dirs(self, folder, recurse=0, session=None):
        if recurse <= 0:
            return []

        dirs = []
        files = []
        has_media = False

        for root, _dirs, files in os.walk(folder):
            for d in _dirs:
                if d.startswith("."):
                    continue
                dirs.append(d)
            for f in files:
                base, ext = os.path.splitext(f)
                ext = ext.lower()
                if ext in VALID_EXT:
                    has_media = True
            break
        dirs.sort()
        files.sort()
        folders = []


        for d in dirs:
            if d.startswith("."):
                continue
            realpath = os.path.join(folder, d)
            folder_data_json = {}
            try:
                folder_data = session.query(Folder)\
                                     .filter(Folder.dirname==realpath)\
                                     .first()

                if folder_data:
                    folder_data_json = folder_data.json()
            except NameError:
                pass

            folders.append({
                'realpath': realpath,
                'dirname': d,
                'children': self.get_dirs(os.path.join(root,d),
                                          recurse-1),
                'collapsed': True,
                'has_media': has_media,
                'folder_data': folder_data_json
            })
        return folders

    @cherrypy.expose
    def history(self, file_id):
        results = []
        with session_scope() as session:
            history = session.query(UserFileHistory)\
                             .filter(UserFileHistory.file_id==file_id)\
                             .order_by(UserFileHistory.user_id.asc(),
                                       UserFileHistory.date_played.desc())
            for h in history:
                session.add(h)
                results.append(h.json(user=True))

        return json_dumps(results)

    @cherrypy.expose
    def download(self, file_id, convert=False, extract_audio=False):
        location = None
        with session_scope() as session:
            locations = session.query(Location)\
                               .filter(Location.file_id==file_id)\
                               .all()
            if not locations:
                raise cherrypy.NotFound()

            for loc in locations:
                session.add(loc)
                if not loc.exists:
                    continue

                if not convert:
                    return serve_file(loc.filename,
                                      "application/x-download",
                                      "attachment")
                ## TODO extract audio, then convert.
                ### Extract audio
                ### FILENAME="$1"
                ### avconv -i "$FILENAME" -c:a copy -vn -sn "$FILENAME.m4a"


            raise cherrypy.NotFound()

    def process_satellite_ufi(self, ufi):
        satellite_history = ufi.get('satellite_history')
        if satellite_history is None:
            return
        for _date, item in satellite_history.items():
            # print("_date:", _date, "item:", item)
            rating = item.get("rating")
            if rating is not None:
                print("RATING DETECTED")
                res = self.set_rating_or_score(ufi.get('file_id'),
                                               ufi.get('user_id'),
                                               'rating',
                                               rating)

            skip_score = item.get("skip_score")
            if skip_score is not None:
                print("SKIP_SCORE DETECTED")
                res = self.set_rating_or_score(ufi.get('file_id'),
                                               ufi.get('user_id'),
                                               'skip_score',
                                               skip_score)

            percent_played = item.get('percent_played')
            if percent_played is not None:
                print("PERCENT_PLAYED DETECTED")
                self.mark_as_played(**{
                    "user_id": ufi.get('user_id'),
                    "file_id": ufi.get('file_id'),
                    "now": item.get('timestamp_UTC', time()),
                    "percent_played": percent_played
                })

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def sync(self, *args, **kwargs):
        result = {
            "result": "OK",
            "processed_history": [],
            "preload": [],
            "history": []
        }
        post_data = cherrypy.request.json
        user_ids = post_data.get("listeners", {}).get("user_ids", [])
        satellite_playlist_collection = post_data.get("playlist",{})
        files = satellite_playlist_collection.get("files", [])
        satellite_state = int(satellite_playlist_collection.get("state", 0))
        with session_scope() as session:
            # Always sync this data so it's marked as played.
            for f in files:
                for ufi in f['user_file_info']:
                    self.process_satellite_ufi(ufi)
                _f = session.query(File)\
                            .filter(File.id==f.get("id"))\
                            .first()
                if _f:
                    session.add(_f)
                    result['processed_history'].append(_f.json(history=True))

        print("satellite_state:", satellite_state)
        kwargs = {
            "params": {
                "s": 0,
                "l": 10,
                "oc": False,
                "raw": True
            },
            "user_ids": user_ids
        }
        result['history'] = self.search(**kwargs)
        result['history'].reverse()
        result['preload'] = self.preload(**{
            "user_ids": user_ids,
            "raw": True
        })

        result["sync_priority"] = ""

        satellite_last_action = float(post_data.get("lastAction", 0))

        if playlist.player.state_string == "PLAYING" and\
           satellite_state == MEDIA_PLAYING:
            print("Mothership & satellite are playing")
        elif playlist.player.state_string == "PLAYING" and\
            satellite_state != MEDIA_PLAYING:
            result["sync_priority"] = "mothership"
        else:
            # Neither are playing.
            if satellite_last_action > playlist.last_action:
                playing = post_data.get("playing", {})
                if playing and playing != {}:
                    playlist.reset()
                    result["sync_priority"] = "satellite"
            else:
                result["sync_priority"] = "mothership"

        print("playlist.last_action", playlist.last_action)
        print("satellite_last_action", satellite_last_action)
        return result

def cherry_py_worker():
    doc_path = os.path.join(sys.path[0])
    print("doc_path:", doc_path)
    root_path = os.path.join(sys.path[0], "server")
    print("root_path:", root_path)
    static_img_path = os.path.join(root_path, "static", "images")
    print ("IMAGE PATH:", static_img_path)
    favicon = os.path.join(static_img_path, "favicon.ico")
    print ("IMAGE:", favicon)

    cherrypy.quickstart(FmpServer(), '/', config={
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': ChatWebSocketHandler
        },

        '/static': {
            'tools.staticdir.root': root_path,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "static"
        },
        '/docs': {
            'tools.staticdir.root': doc_path,
            'tools.staticdir.on': True,
            'tools.staticdir.dir': "docs"
        }
    })

def json_headers():
    response = cherrypy.response
    response.headers['Content-Type'] = 'application/json'

def json_dumps(obj):
    json_headers()
    return json.dumps(obj).encode("utf8")

def JsonTextMessage(data):
    return TextMessage(json.dumps(data))

def broadcast_jobs():
    json_broadcast({'jobs': job_data})

def json_broadcast(data):
    cherrypy.engine.publish('websocket-broadcast', JsonTextMessage(data))

def broadcast(data):
    print("BROADCAST:", data)
    json_broadcast(data)
    return
    if not data.get('time-status'):
        print ("broadcast:", json.dumps(data, sort_keys=True,
                            indent=4, separators=(',', ': ')))

    broadcast_countdown()
    json_broadcast({'vote_data':vote_data})

