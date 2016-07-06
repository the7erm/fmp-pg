import os
import sys
import json
import shlex
import re
import cherrypy
import configparser
import threading
import subprocess
import mimetypes
mimetypes.init()
from time import time, sleep
from datetime import date, datetime
from cherrypy.lib.static import serve_file
from cherrypy.process import wspbus, plugins
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage, BinaryMessage
from base64 import b64encode

sys.path.append("../")
from fmp_utils.db_session import session_scope, Session
from fmp_utils.misc import to_bool, session_add, to_int
from fmp_utils.first_run import first_run, check_config
from fmp_utils.media_tags import MediaTags
from fmp_utils.constants import CONFIG_DIR, CONFIG_FILE, VALID_EXT, \
                                CONVERT_DIR, TMP_DIR
from fmp_utils.jobs import jobs
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
from sqlalchemy.sql import not_, text, and_, or_, func
from sqlalchemy.exc import InvalidRequestError
from pprint import pprint, pformat

hostname = subprocess.check_output(['hostname'])
hostname = hostname.strip()

WebSocketPlugin(cherrypy.engine).subscribe()
cherrypy.tools.websocket = WebSocketTool()

MEDIA_NONE = 0
MEDIA_STARTING = 1
MEDIA_RUNNING = 2
MEDIA_PLAYING = 2
MEDIA_PAUSED = 3
MEDIA_STOPPED = 4
LEAVE_REASON = "A client left the room without a proper explanation."

fnCache = {}


class Converter(object):
    def __init__(self):
        self.files = []
        self.converting = False
        self.die = False

    def append(self, src, tmp_dst, dst):
        if self.die:
            return
        found = False
        for f in self.files:
            _src, _tmp_dst, _dst = f
            if _dst == dst:
                found = True
                break

        if not found:
            self.files.append([src, tmp_dst, dst])
        self.start()

    def start(self):
        if self.die:
            return
        if self.converting:
            print("current conversion:", self.converting)
            return
        self.converting = True
        t = threading.Thread(target=self.do)
        t.start()

    def do(self):
        print("DO", "!"*100)
        if len(self.files) == 0:
            self.converting = False
            return
        while len(self.files) > 0:
            if self.die:
                return

            # Grab the first set of files.
            src, tmp_dst, dst = self.files.pop(0)
            if os.path.exists(dst):
                print("EXISTS:", dst)
                continue

            tmp_basename = os.path.basename(tmp_dst)
            tmp_dst = os.path.join(TMP_DIR, tmp_basename)

            self.converting = "%s => %s" % (src, dst)
            print("DOING:", src, "=>", dst)
            # # avconv -i "$FILENAME" -c:a copy -vn -sn "$FILENAME.m4a"
            base, ext = os.path.splitext(os.path.basename(src))
            ext = ext.lower()

            output = ""
            audio_tmp = ""
            if ext in (".mp4", ".wmv", ".flv", ".avi"):

                # avprobe -v quiet -show_format -of json -pretty  -show_streams
                # '/home/erm/disk2/acer-home/media/video/c
                #  /child beater/Child Beater - not really.flv'
                ex = [
                    "avprobe", "-v", "quiet", "-show_format", "-show_streams",
                               "-of", "json", "-pretty",
                               src
                ]
                try:
                    output = subprocess.check_output(ex)
                    output = output.decode('utf-8')
                    print("avprobe:", output)
                except Exception as e:
                    print("Probe Error:", e)
                    continue

                avprobe = json.loads(output)
                for s in avprobe['streams']:
                    if s['codec_name'] == "mp3" and s['codec_type'] == 'audio':
                        ex = [
                            "avconv", "-y", "-i", src, "-c:a", "copy", "-vn",
                            "-sn", tmp_dst
                        ]
                        try:
                            output = subprocess.check_output(ex)
                            output = output.decode('utf-8')
                        except Exception as e:
                            print("Conversion Exception:", e)
                        if os.path.exists(tmp_dst):
                            os.rename(tmp_dst, dst)
                            break

                    if (s['codec_name'] in ("aac",) and
                            s['codec_type'] == "audio"):
                            ext = ".m4a"

                    if (s['codec_name'] in ('wmav2',) and
                            s['codec_type'] == 'audio'):
                            ext = ".wma"

                    if (s['codec_name'] in ('pcm_s16le',) and
                            s['codec_type'] == 'audio'):
                            ext = ".wav"

                if os.path.exists(dst):
                    continue

                # extracting the audio and then converting that to mp3
                # is faster
                if ext in (".m4a", ".wma", ".wav"):
                    tmp_basename += ext
                    audio_tmp = os.path.join(TMP_DIR, tmp_basename)
                    print("extracting audio:%s => %s" % (src, audio_tmp))
                    ex = [
                        "avconv", "-y", "-i", src, "-c:a", "copy", "-vn",
                        "-sn", audio_tmp
                    ]
                    try:
                        output = subprocess.check_output(ex)
                        output = output.decode('utf-8')
                    except Exception as e:
                        print("Conversion Exception:", e)

                    if os.path.exists(audio_tmp):
                        src = audio_tmp

            print("final conversion:%s => %s" % (src, tmp_dst))

            ex = [
                "avconv", "-y", "-i", src, tmp_dst
            ]
            print("ex:", " ".join(ex))
            output = ""
            try:
                output = subprocess.check_output(ex)
                output = output.decode('utf-8')
            except Exception as e:
                print("Conversion Exception:", e)

            print ("output:", output)
            if os.path.exists(tmp_dst):
                os.rename(tmp_dst, dst)
            if audio_tmp and os.path.exists(audio_tmp):
                os.unlink(audio_tmp)

        self.converting = False


class ConverterPlugin(cherrypy.process.plugins.SimplePlugin):
    def __init__(self, bus):
        plugins.SimplePlugin.__init__(self, bus)

    def start(self):
        self.bus.log('Start Called')

    def stop(self):
        self.bus.log('Stop Called')
        converter.die = True
        self.bus.log("CONVERTER THREAD:%s" % converter.thread)
        pprint(dir(converter.thread))


ConverterPlugin(cherrypy.engine).subscribe()

converter = Converter()


def convert(id=None, locations=[], to=".mp3", unique=True,  *args, **kwargs):
    if converter.converting and len(converter.files) > 10:
        print("converter.converting and len(converter.files) > 10",
              len(converter.files))
        return
    # convert
    # print("CONVERT: id:%s locations:%s, to:%s" % (id, pformat(locations),
    #                                               to))
    if not to.startswith("."):
        to = ".%s" % to
    dst = convert_filename(id)
    if os.path.exists(dst):
        print("EXISTS:", dst)
        return
    src = None
    base = None
    ext = None

    for l in locations:
        src = os.path.join(l['dirname'], l['basename'])
        if os.path.exists(src):
            # print ("location:",l)
            base, ext = os.path.splitext(l['basename'])
            # print("base:%s ext:%s" % (base, ext))
            break

    if src is None:
        print("NO SRC:", dst)
        return
    # ## avconv -i "$FILENAME" -c:a copy -vn -sn "$FILENAME.m4a"

    tmp_dst = "%s.%s.mp3" % (dst, ext)

    converter.append(src, tmp_dst, dst)


def convert_filename(file_id):
    dst_basename = "%s%s" % (file_id, ".mp3")
    dst = os.path.join(CONVERT_DIR, dst_basename)
    return dst


def check_for_files_that_need_converting():
    print("- STARTTED -", "-"*100)
    while True:
        if converter.die:
            return
        # print("check_for_files_that_need_converting()")
        if converter.converting and len(converter.files) > 10:
            print("converter.converting and len(converter.files) > ",
                  len(converter.files))
            cnt = 60
            while cnt > 0:
                cnt = cnt - 1
                sleep(1)
                if converter.die:
                    return
            continue
        awaiting_download = []
        with session_scope() as session:
            sql = """SELECT f.*
                     FROM files f,
                          preload p
                     WHERE f.id = p.file_id
                     ORDER BY p.from_search DESC, p.id ASC"""
            _files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()
            files = [f for f in _files]

            users = session.query(User).all()
            for user in users:
                # print ("USER:", user.name)
                sql = """SELECT f.*
                         FROM files f
                         WHERE f.id IN (
                            SELECT file_id
                            FROM user_file_info ufi
                            WHERE ufi.user_id = %s AND
                                  ufi.time_played IS NOT NULL
                            ORDER BY ufi.time_played DESC NULLS LAST
                            LIMIT 100
                         )
                         ORDER BY f.time_played DESC NULLS LAST""" % (user.id,)
                _files = session.query(File)\
                               .from_statement(
                                    text(sql)
                                )\
                           .all()
                files = files + [f for f in _files]

            for f in files:
                if converter.die:
                    return
                user_id = 0
                session_add(session, f)
                filename = f.filename

                if filename.lower().endswith(".mp3"):
                    continue
                # print("f.filename:",filename)

                session_add(session, f)
                _id = f.id
                dst = convert_filename(_id)
                awaiting_download.append(dst)
                if os.path.exists(dst):
                    # print("exists:", dst)
                    continue
                # print("MISSING:", dst)

                locations = []
                session_add(session, f)
                for l in f.locations:
                    session_add(session, l)
                    locations.append(l.json())
                jobs.append(cmd=convert,
                            id=_id,
                            locations=locations,
                            to='.mp3',
                            unique=True)

        threashold = (time() - (24 * 60 * 60))
        for root, dirs, files in os.walk(CONVERT_DIR):
            for name in files:
                fn = os.path.join(root, name)
                mtime = os.path.getmtime(fn)
                # print("mtime     :", mtime)
                # print("threashold:", threashold)
                if fn not in awaiting_download and mtime < threashold:
                    print("__"*100)
                    print("remove:", fn, mtime)
                    os.unlink(fn)
                    continue
                # print("keep:", fn)
        cnt = 60
        while cnt > 0:
            cnt = cnt - 1
            sleep(1)
            if converter.die:
                return


class ChatWebSocketHandler(WebSocket):
    def received_message(self, message):
        print(">"*80)
        print("message.data:", message.data)
        obj = "FAILED"
        try:
            obj = json.loads(message.data.decode("utf-8"))

            print("json.loads()", pformat(obj))
            self.process_action(obj)
        except Exception as e:
            print("ChatWebSocketHandler Exception:", e)
            try:
                print("ChatWebSocketHandler Exception data:",
                      message.data.decode("utf-8"))
            except Exception as e:
                print("ChatWebSocketHandler ERROR DECODING:", e)
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

    def closed(self, code, reason=LEAVE_REASON):
        print("****"*10)
        print ("CLOSED")
        # cherrypy.engine.publish('websocket-broadcast', TextMessage(reason))

    def process_action(self, obj):
        if not isinstance(obj, dict):
            print("NOT A DICT:", obj)
            return
        action = obj.get('action')
        if action == "broadcast-playing":
            playlist.broadcast_playing()
            return

        if action == "sync":
            json_broadcast({"debug": "sync"})
            payload = obj.get('payload', {})
            self.sync(payload)

        if action == "sync-collections":
            json_broadcast({"debug": "sync-collections"})
            payload = obj.get('payload', {})
            self.sync_collections(payload)

        if action == "sync-users":
            self.sync_users()
            json_broadcast({"debug": "syncing-users"})

        if action == "sync-file":
            json_broadcast({"debug": "sync-file"})

        if action == "test":
            broadcast({
                "processed": [
                    {
                        'spec': obj
                    }
                ]
            })

    def sync_users(self):
        users = get_all_users()
        json_broadcast({"users": users})

    def sync(self, payload):
        print("-sync")
        for _date, files in payload.items():
            print("-sync %s:" % _date)
            self.process_files(files)
            # collection.sync[today][file_id][elementType][action]

    def process_needs_synced(self, needs_synced_files, transaction_id,
                             user_ids=[], deleted=[]):
        print("PROCESS NEEDS SYNCED")
        for file_id in deleted:
            with session_scope() as session:
                    needs_marked_as_played = True
                    session.query(Preload)\
                           .filter(Preload.file_id == file_id)\
                           .delete()
                    session.commit()

                    exists = session.query(Preload)\
                                    .filter(Preload.file_id == file_id)\
                                    .first()
                    print("removed file_id from preload:", file_id)
                    print("proof:", exists)

        for needs_synced in needs_synced_files:
            with session_scope() as session:
                needs_marked_as_played = False
                if needs_synced.get("played", False):
                    needs_marked_as_played = True
                    session.query(Preload)\
                           .filter(Preload.file_id == needs_synced['id'])\
                           .delete()
                    session.commit()

                    exists = session.query(Preload)\
                                    .filter(Preload.file_id ==
                                            needs_synced['id'])\
                                    .first()
                    print("removed needs_synced['id']", needs_synced['id'])
                    print("proof:", exists)

                dbInfo = session.query(File)\
                                .filter(File.id == needs_synced.get("id"))\
                                .first()
                session_add(session, dbInfo)

                for ns_ufi in needs_synced.get("user_file_info", []):
                    # print("needs_synced:", pformat(needs_synced))
                    and_filter = and_(
                        UserFileInfo.file_id == ns_ufi['file_id'],
                        UserFileInfo.user_id == ns_ufi['user_id']
                    )
                    db_ufi = session.query(UserFileInfo)\
                                    .filter(and_filter)\
                                    .first()
                    session_add(session, db_ufi)

                    db_ufi_timestamp = to_int(db_ufi.timestamp)
                    ns_ufi_timestamp = to_int(ns_ufi.get("timestamp", 0))
                    force = True

                    if not db_ufi.timestamp or force or \
                       db_ufi_timestamp < ns_ufi_timestamp:
                        sync_keys = ["time_played", "rating", "skip_score",
                                     "true_score", "voted_to_skip",
                                     "timestamp"]
                        for k in sync_keys:
                            value = ns_ufi.get(k)
                            if value is None:
                                continue
                            if k == "voted_to_skip":
                                value = to_bool(value)
                            if k in("timestamp", "time_played") and not value:
                                continue

                            print("set %s to %s" % (k, value))
                            session_add(session, db_ufi)
                            setattr(db_ufi, k, value)
                        session_add(session, db_ufi)
                        db_ufi.calculate_true_score()
                    else:
                        print("db_ufi.timestamp > ns_ufi['timestamp']")
                        print(db_ufi.timestamp, ns_ufi['timestamp'])
                    session.commit()
                # End of for ns_ufi in needs_synced.get("user_file_info",[]):

                if needs_marked_as_played:
                    kwargs = {
                        "user_ids": needs_synced.get("listener_user_ids",
                                                     user_ids),
                        "percent_played": needs_synced.get("percent_played",
                                                           0),
                        "now": needs_synced.get("time_played", 0),
                        "force": True
                    }
                    session_add(session, dbInfo)
                    try:
                        dbInfo.mark_as_played(**kwargs)
                    except Exception as e:
                        print("dbInfo.mark_as_played Exception:", e)
                    session_add(session, dbInfo)
                print("MADE IT TO THE END")
                json_broadcast({
                    "playlist-item": dbInfo.json(user_ids=user_ids),
                    "transaction_id": transaction_id,
                    "needsSyncedProcessed": True
                })

        print("/PROCESS NEEDS SYNCED")

    def sync_collections(self, payload):
        print("****** sync_collections:", pformat(payload))
        json_broadcast({"debug": "syncing collections"})
        transaction_id = payload.get("transaction_id")

        if transaction_id is None:
            return

        playlist_ids = payload.get("playlist_ids", [])
        preload_ids = payload.get("preload_ids", [])
        primary_user_id = payload.get("primary_user_id", 0)
        listener_user_ids = payload.get("listener_user_ids", [])
        secondary_user_ids = payload.get("secondary_user_ids", [])
        prefetchNum = payload.get("prefetchNum", 100)
        secondaryPrefetchNum = payload.get("secondaryPrefetchNum", 20)
        needs_synced_files = payload.get("needs_synced_files", [])
        user_ids = listener_user_ids + secondary_user_ids + [primary_user_id]
        user_ids = list(set(user_ids))

        deleted = payload.get("deleted", [])

        try:
            self.process_needs_synced(needs_synced_files, transaction_id,
                                      user_ids, deleted)
        except Exception as e:
            print ("self.process_needs_synced Exception:", e)

        try:
            self.send_playlist_data(transaction_id, playlist_ids, user_ids)
        except Exception as e:
            print ("Exception send_playlist_data :", e)

        try:
            self.send_preload_data(transaction_id,
                                   preload_ids,
                                   primary_user_id,
                                   listener_user_ids,
                                   secondary_user_ids,
                                   prefetchNum,
                                   secondaryPrefetchNum)
        except Exception as e:
            print ("Exception send_playlist_data :", e)
        json_broadcast({"transaction-complete": transaction_id})

    def send_playlist_data(self, transaction_id, playlist_ids, user_ids):
        response = []
        print("user_ids:", user_ids)
        with session_scope() as session:
            files = session.query(File)\
                           .filter(File.id.in_(playlist_ids))\
                           .all()

            for f in files:
                session_add(session, f)
                json_broadcast({
                    "transaction_id": transaction_id,
                    "playlist-item": f.json(user_ids=user_ids)
                })

    def send_preload_data(self,
                          transaction_id,
                          preload_ids,
                          primary_user_id,
                          listener_user_ids,
                          secondary_user_ids,
                          prefetchNum,
                          secondaryPrefetchNum):

        prefetchNum = int(prefetchNum)
        secondaryPrefetchNum = int(secondaryPrefetchNum)
        primary_user_id = int(primary_user_id)
        listener_user_ids = listener_user_ids + [primary_user_id]
        listener_user_ids = list(set(listener_user_ids))
        user_ids = listener_user_ids + secondary_user_ids + [primary_user_id]
        user_ids = list(set(user_ids))
        user_ids = [int(x) for x in user_ids]

        print("PRIMARY USER ID:", primary_user_id)

        sql = """SELECT f.*
                 FROM files f,
                      preload p
                 WHERE user_id IN (%s) AND
                       f.id = p.file_id
                 ORDER BY p.from_search DESC, p.id ASC""" % ",".join(
                    str(x) for x in user_ids)

        results = []
        group_by_user = {}
        with session_scope() as session:
            # Check the preload and make sure all the users have files
            # up to their minimums ready.
            preloaded = picker.get_preload(
                user_ids=user_ids,
                remove_item=False,
                primary_user_id=primary_user_id,
                prefetch_num=prefetchNum,
                secondary_prefetch_num=secondaryPrefetchNum
            )

            for p in preloaded:
                session_add(session, p)

            # TODO wait

            # 1. Select prefetchNum files for primary_user_id
            # 2. Select secondaryPrefetchNum for secondary_user_ids
            files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()
            for f in files:
                user_id = 0
                session_add(session, f)
                if f.cued:
                    user_id = f.cued['user_id']
                if not group_by_user.get(user_id):
                    group_by_user[user_id] = []
                if user_id != primary_user_id:
                    if len(group_by_user[user_id]) >= secondaryPrefetchNum:
                        # skip because we've fetched enough.
                        continue
                elif user_id == primary_user_id:
                    if len(group_by_user[user_id]) >= prefetchNum:
                        # skip because we've fetched enough.
                        continue

                # Group the files by their user_id.
                session_add(session, f)
                item = f.json(user_ids=user_ids)
                group_by_user[user_id].append(item)
                json_broadcast({"preload-item": item,
                                "transaction_id": transaction_id})

    def process_files(self, files):
        # collection.sync[today][file_id][elementType][action]
        for file_id, element_types in files.items():
            print("-process_files file_id:%s:" % file_id)
            self.process_element_types(element_types)

    def process_element_types(self, element_types):
        for element_type, actions in element_types.items():
            print("-process_element_types element_type:%s:" % element_type)
            if element_type == 'object':
                for action, action_spec in actions.items():
                    self.process_action_spec(action, action_spec)
                continue

            if element_type == 'list':
                print("**** ACTIONS **** ")
                pprint(actions)
                for action, action_specs in actions.items():
                    print("action:", action)
                    print("action_specs:", action_specs)
                    for action_spec in action_specs:
                        print("action_spec:", action_spec)
                        if action_spec is None:
                            broadcast({
                                "processed": [{
                                    'spec': action_spec
                                }]
                            })
                            continue
                        self.process_action_spec(action, action_spec)

    def process_action_spec(self, action, action_spec):
        with session_scope() as session:
            file_id = action_spec.get("file_id")
            user_id = action_spec.get("user_id")
            user_ids = action_spec.get('user_ids', [])

            if action == 'mark_as_played':
                file = session.query(File)\
                              .filter(File.id == file_id)\
                              .first()
                if not file:
                    return {
                        "error": "no file for file_id %s" % file_id
                    }
                session_add(session, file)
                kwargs = {
                    "user_ids": user_ids,
                    "percent_played": action_spec.get("percent_played"),
                    "now": int(action_spec.get("now"))
                }
                # print("DISABLED mark_as_played")
                file.mark_as_played(**kwargs)
                session_add(session, file)
                # import pdb; pdb.set_trace()
                file_json = file.json(user_ids=user_ids)
                processed = {
                    "processed": [{
                        'file': file_json,
                        'spec': action_spec
                    }]
                }
                print("-="*40)
                pprint(processed)
                broadcast(processed)
                return
            if action in ("rating", "skip_score", "voted_to_skip"):
                ufi = session.query(UserFileInfo)\
                             .filter(and_(
                                UserFileInfo.file_id == file_id,
                                UserFileInfo.user_id == user_id
                              ))\
                             .first()
                if not ufi:
                    return {
                        "error": "UserFileInfo for file_id:%s user_id:%s" % (
                            file_id, user_id)
                    }
                session.add(ufi)
                attr = action_spec.get('attr')
                value = int(action_spec.get('value'))
                if attr == 'rating':
                    if value >= 0 and value <= 5:
                        ufi.rating = value

                if attr == 'skip_score':
                    """
                    if value >= -15 and value <= 15:
                        ufi.skip_score = value
                    """
                    ufi.skip_score = value

                if attr == 'voted_to_skip':
                    value = to_bool(value)

                ufi.calculate_true_score()
                session.add(ufi)
                session.commit()
                print("/calculate_true_score")
                broadcast({
                    "processed": [{
                        'ufi': ufi.json(),
                        'spec': action_spec
                    }]
                })


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
    def satellite(self):
        static_path = sys.path[0]
        index_path = os.path.join(static_path, "server", "templates",
                                  "satellite.html")
        data = "Error"
        with open(index_path, 'r') as fp:
            data = fp.read()
        return data

    @cherrypy.expose
    def set_listening(self, user_id, listening, *args, **kwargs):
        with session_scope() as session:
            user = session.query(User)\
                          .filter(User.id == user_id)\
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
                          .filter(User.id == user_id)\
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

        return self.set_rating_or_score(
            file_id, user_id, 'skip_score', skip_score)

    @cherrypy.expose
    def rate(self, *args, **kwargs):
        file_id = int(kwargs.get('file_id'))
        user_id = int(kwargs.get('user_id'))
        rating = int(kwargs.get('rating', 6))
        return self.set_rating_or_score(file_id, user_id, 'rating', rating)

    @cherrypy.expose
    def set_rating_or_score(self, file_id, user_id, attr, value):
        print("set_rating_or_score file_id:%s user_id:%s attr:%s value:%s" % (
            file_id, user_id, attr, value))
        user_file_info = self.get_user_file_info(file_id, user_id)
        with session_scope() as session:
            session_add(session, user_file_info)
            setattr(user_file_info, attr, value)
            user_file_info.calculate_true_score()
            session.commit()
            response = json_dumps(user_file_info.json(history=True))
            try:
                session_add(session, playlist.files[playlist.index])
                if playlist.files[playlist.index].id == file_id:
                    playlist.broadcast_playing()
            except IndexError:
                pass

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
                    break

            if not user_file_info:
                user_file_info = session.query(UserFileInfo)\
                                        .filter(and_(
                                            UserFileInfo.file_id == file_id,
                                            UserFileInfo.user_id == user_id
                                        ))\
                                        .first()
        return user_file_info

    @cherrypy.expose
    def mark_as_played(self, *args, **kwargs):
        print("kwargs:", kwargs)
        with session_scope() as session:
            f = session.query(File)\
                       .filter(File.id == kwargs.get('file_id'))\
                       .first()
            session.add(f)
            user_id = kwargs.get("user_ids")
            user_ids = [user_id]
            if "," in user_id:
                user_ids = user_id.split(",")

            user_ids = [str(int(x)) for x in user_ids]
            mark_as_played_kwargs = {
                "user_ids": user_ids,
                "percent_played": int(float(kwargs.get("percent_played", 0))),
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
            return json.dumps(response)

    @cherrypy.expose
    def next(self):
        playlist.next()
        return "NEXT"

    @cherrypy.expose
    def prev(self):
        playlist.prev()
        return "PREV"

    @cherrypy.expose
    def pause(self):
        playlist.pause()
        # broadcast({"state-changed": playlist.player.state_string })
        if playlist.player.state_string == "PLAYING":
            return "PLAYING"
        return "PAUSED"

    @cherrypy.expose
    def status(self):
        return "%s %s" % (playlist.player.state_string,
                          os.path.basename(playlist.player.filename))

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
                                 UserFileInfo.file_id == file_id,
                                 UserFileInfo.user_id == kwargs.get('user_id')
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
            # Get all the artists that match the word + 3 characters
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
                                   func.length(Album.name) < (
                                       word_len + lower_search)
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

            if len(results) < hard_limit:
                limit = hard_limit - len(results)
                locations = session.query(Location)\
                                   .filter(Location.basename.ilike(
                                        "%s%%" % word))\
                                   .order_by(Location.basename)\
                                   .limit(limit)
                for l in locations:
                    basename = l.basename
                    if "_" in basename:
                        parts = basename.split("_")
                        basename = parts[0]
                    if " " in basename:
                        parts = basename.split(" ")
                        basename = parts[0]
                    results.append(basename)
                    results.append(l.basename)

                results = list(set(results))

            results.sort()
            return json_dumps(results)

    @cherrypy.expose
    def genre_enabled(self, *args, **kwargs):
        session = Session()
        genre = session.query(Genre)\
                       .filter(Genre.id == kwargs.get('id'))\
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
                "Error": "Empty genre name:%s" % genre_name
            })
        with session_scope() as session:
            file = session.query(File)\
                          .filter(File.id == file_id)\
                          .first()
            if not file:
                return json_dumps({
                    "RESULT": "FAIL",
                    "Error": "No file found for file_id:%s" % file_id
                })
            genre = session.query(Genre)\
                           .filter(Genre.name == genre_name)\
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
                "Error": "Empty genre name:%s" % genre_name
            })

        with session_scope() as session:
            file = session.query(File)\
                          .filter(File.id == file_id)\
                          .first()
            if not file:
                return json_dumps({
                    "RESULT": "FAIL",
                    "Error": "No file found for file_id:%s" % file_id
                })
            genre = session.query(Genre)\
                           .filter(Genre.name == genre_name)\
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
        results = get_all_users()
        return json_dumps(results)

    @cherrypy.expose
    def ip_addresses(self, *args, **kwargs):
        local = cherrypy.request.local
        return json_dumps({"ip_addresses": IP_ADDRESSES,
                           "port": local.port})

    @cherrypy.expose
    def preload(self, *args, **kwargs):
        params = cherrypy.request.params
        user_ids = self.get_user_ids(user_ids=kwargs.get('user_ids', []))
        limit = int(kwargs.get("limit", 0))
        user_sql = """SELECT user_id AS id
                      FROM preload
                      WHERE user_id IN(%s)
                      GROUP BY user_id""" % ",".join(user_ids)

        sql = """SELECT f.*
                 FROM files f,
                      preload p
                 WHERE user_id IN (%s) AND
                       f.id = p.file_id
                 ORDER BY p.from_search DESC, p.id ASC""" % ",".join(user_ids)

        results = []
        preload_user_ids = []
        with session_scope() as session:
            user_count = session.query(Preload.user_id,
                                       func.count(Preload.user_id))\
                                .filter(Preload.user_id.in_(user_ids))\
                                .group_by(Preload.user_id)\
                                .all()

            for user in user_count:
                print ("USER:", user)
            print("/"*100)
            for user_id in user_ids:
                found = False
                for count_user_id, total in user_count:
                    if total <= 10:
                        preload_user_ids.append(user_id)
                        continue

                    if str(user.user_id) == user_id:
                        found = True
                        break
                if not found:
                    preload_user_ids.append(user_id)

            if preload_user_ids:
                preloaded = picker.get_preload(user_ids=preload_user_ids,
                                               remove_item=False)
                for p in preloaded:
                    results.append(p.json(user_ids=user_ids))

            files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()
            for f in files:
                if limit and len(results) >= limit:
                    break
                results.append(f.json(user_ids=user_ids))

        _results = []
        group_by_user = {}
        for r in results:
            cued = r.get("cued", {})
            user_id = cued.get("user_id", 0)
            if user_id not in group_by_user:
                group_by_user[user_id] = []
            group_by_user[user_id].append(r)

        has_files = True
        while has_files:
            has_files = False
            for user_id, group in group_by_user.items():
                if not group:
                    continue
                file = group.pop(0)
                has_files = True
                _results.append(file)
        results = _results

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
            print("KWARGS:")
            pprint(kwargs)
            print("PARAMS:", params)
            if 'params' in kwargs:
                params = kwargs.get("params")

            cherrypy.log(("+"*20)+" SEARCH "+("+"*20))
            cherrypy.log("search: kwargs:%s" % (kwargs,))
            start = int(params.get("s", 0))
            limit = int(params.get("l", 10))
            only_cued = params.get('oc', False)
            owner = params.get("owner", '')

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

            user_ids = self.get_user_ids(user_ids=kwargs.get('user_ids', []))
            USER_IDS = ",".join(user_ids)
            if only_cued:

                query_spec["FROM"].append("preload p")
                query_spec["COUNT_FROM"].append("preload p")
                query_spec["WHERE"].append(
                    ("f.id = p.file_id AND p.user_id IN ({USER_IDS})").format(
                        USER_IDS=USER_IDS)
                )
                query_spec['ORDER_BY'].append(
                    "from_search DESC NULLS LAST, p.id")

            if q:
                query_spec["SELECT"].append(
                    "ts_rank_cd(to_tsvector('english', keywords_txt), query) "
                    "AS rank")
                count_from = """plainto_tsquery('english', :q) query"""
                query_spec["FROM"].append(count_from)
                query_spec["COUNT_FROM"].append(count_from)
                query_spec["WHERE"].append(
                    "query @@ to_tsvector('english', keywords_txt)")
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
                results.append(res.json(history=True, user_ids=user_ids))

            print ("counting total")
            total = session.execute(text(count_query), query_args).first()

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
                Preload.file_id == _id
            )).first()
            if cued and not is_cued:
                preload = Preload()
                user = session.query(User)\
                              .filter(User.id == user_id)\
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

        fp = open("/tmp/create_db.sh", 'w')
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
            print(k, ":", v)
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
        print("obj:", obj)
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
                fp = open("/tmp/create_role.sh", 'w')
                fp.write("""!#/bin/sh
                psql -c "CREATE ROLE %s WITH LOGIN ENCRYPTED PASSWORD \'%s\'"
                """ % (username, password))
                fp.close()
            else:
                fp = open("/tmp/create_role.sh", 'w')
                fp.write("""!#/bin/sh
                psql -c "CREATE ROLE %s WITH LOGIN"
                """ % (username,))
                fp.close()
            os.chmod("/tmp/create_role.sh", 0o777)
            op = ['gksu', '-m', 'Create postgres user %s' % username,
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
    def add_folder(self, *args, **kwargs):
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
                                     .filter(Folder.dirname == realpath)\
                                     .first()

                if folder_data:
                    folder_data_json = folder_data.json()
            except NameError:
                pass

            folders.append({
                'realpath': realpath,
                'dirname': d,
                'children': self.get_dirs(os.path.join(root, d),
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
                             .filter(UserFileHistory.file_id == file_id)\
                             .order_by(UserFileHistory.user_id.asc(),
                                       UserFileHistory.date_played.desc())
            for h in history:
                session.add(h)
                results.append(h.json(user=True))

        return json_dumps(results)

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def user_history(self, *args, **kwargs):
        post_data = cherrypy.request.json
        user_ids = [str(int(x)) for x in post_data.get('user_ids', [])]
        limit = int(post_data.get("limit", 1))
        if not limit:
            limit = 1
        results = []
        with session_scope() as session:
            sql = """SELECT f.*
                     FROM files f, user_file_history ufh
                     WHERE f.id = ufh.file_id AND
                           ufh.user_id IN (%s)
                     ORDER BY ufh.time_played DESC NULLS LAST
                     LIMIT %s""" % (",".join(user_ids), limit)
            files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()
            for f in files:
                session_add(session, f)
                item = f.json(user_ids=user_ids, get_image=False)
                item['user_ids'] = user_ids
                print("ITEM:")
                pprint(item)
                results.append(item)

        return results

    @cherrypy.expose
    def download(self, file_id, convert_to=".mp3", **kwargs):
        location = None
        with session_scope() as session:
            dst = convert_filename(file_id)
            print ("cherrypy.request.headers[Accept]:",
                   cherrypy.request.headers.get("Accept"))
            if os.path.exists(dst):
                mimetype = mimetypes.guess_type(dst)
                print("mimetype 1:", mimetype)
                return serve_file(dst,
                                  mimetype[0],
                                  "attachment")

            locations = session.query(Location)\
                               .filter(Location.file_id == file_id)\
                               .all()
            if not locations:
                raise cherrypy.NotFound()

            for loc in locations:
                session_add(session, loc)
                if not loc.exists:
                    continue

                convert_to = convert_to.lower()
                if convert_to not in (".mp3",):
                    # TODO add other file types
                    convert_to = ".mp3"

                session_add(session, loc)
                basename = os.path.basename(loc.filename)
                base, ext = os.path.splitext(basename)
                ext = ext.lower()
                if not convert_to or ext == convert_to:
                    """
                    cherrypy.request.headers[Accept]: audio/webm,audio/ogg,audio/wav,audio/*;q=0.9,application/ogg;q=0.7,video/*;q=0.6,*/*;q=0.5
                    mimetype 2: ('audio/x-ms-wma', None)
                    """
                    session_add(session, loc)
                    mimetype = mimetypes.guess_type(loc.filename)
                    print("mimetype 2:", mimetype)
                    return serve_file(loc.filename,
                                      mimetype[0],
                                      "attachment")

                _locations = []
                for l in locations:
                    session_add(session, l)
                    _locations.append(l.json())
                session_add(session, loc)
                jobs.append(cmd=convert,
                            id=loc.file_id,
                            locations=_locations,
                            to=convert_to,
                            unique=True,
                            priority="high")
                cnt = 0
                while cnt < 30:
                    cnt += 1
                    if os.path.exists(dst):
                        break
                    sleep(1)

                if os.path.exists(dst):
                    mimetype = mimetypes.guess_type(dst)
                    print("mimetype 3:", mimetype)
                    return serve_file(dst,
                                      mimetype[0],
                                      "attachment")
                # ## TODO extract audio, then convert.
                # ## Extract audio
                # ## FILENAME="$1"
                # ## avconv -i "$FILENAME" -c:a copy -vn -sn "$FILENAME.m4a"

            raise cherrypy.NotFound()

    def process_satellite_ufi(self, ufi):
        satellite_history = ufi.get('satellite_history')
        if satellite_history is None:
            return
        for _date, item in satellite_history.items():
            rating = item.get("rating")
            skip_score = item.get("skip_score")
            percent_played = item.get('percent_played')
            if rating is None and skip_score is None and \
               percent_played is None:
                    continue

            pprint(ufi)
            print("_date:", _date, "item:", pformat(item))

            if rating is not None:
                print("RATING DETECTED")
                res = self.set_rating_or_score(ufi.get('file_id'),
                                               ufi.get('user_id'),
                                               'rating',
                                               rating)

            if skip_score is not None:
                print("SKIP_SCORE DETECTED")
                res = self.set_rating_or_score(ufi.get('file_id'),
                                               ufi.get('user_id'),
                                               'skip_score',
                                               skip_score)

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
    def preloadSync(self, *args, **kwargs):
        post_data = cherrypy.request.json
        # print("newSync:", args, kwargs)
        # print("post_data:", post_data)
        result = []

        listener_user_ids = post_data.get('listener_user_ids', [])
        primary_user_id = int(post_data.get('primary_user_id'))
        secondary_user_ids = post_data.get('secondary_user_ids', [])

        prefetchNum = int(post_data.get('prefetchNum', 100))
        secondaryPrefetchNum = int(post_data.get('secondaryPrefetchNum', 20))
        include_admins = post_data.get("include_admins", True)
        primary_user_id = int(primary_user_id)
        listener_user_ids = listener_user_ids + [primary_user_id]
        listener_user_ids = list(set(listener_user_ids))
        user_ids = listener_user_ids + secondary_user_ids + [primary_user_id]
        user_ids = list(set(user_ids))
        user_ids = [int(x) for x in user_ids]
        group_by_user_file_ids = {}
        files = post_data.get("files", [])
        already_added = []
        already_added_sql = ""

        for f in files:
            cued = f.get("cued", {})
            if not cued:
                cued = {}
            user_id = cued.get("user_id", 0)
            if not group_by_user_file_ids.get(user_id):
                group_by_user_file_ids[user_id] = []
            file_id = f.get("id")
            if file_id:
                file_id = int(file_id)
                already_added.append(file_id)

            if file_id and file_id not in group_by_user_file_ids[user_id]:
                group_by_user_file_ids[user_id].append(file_id)

        if already_added:
            already_added_sql = " AND p.file_id NOT IN (%s) " % (
                ",".join(str(x) for x in already_added),
            )

        print("PRIMARY USER ID:", primary_user_id)
        # print("FILES:", files)

        sql = """SELECT f.*, l.basename
                 FROM files f,
                      preload p,
                      locations l
                 WHERE user_id IN (%s) AND
                       f.id = p.file_id AND
                       l.file_id = f.id %s
                 ORDER BY p.from_search DESC, p.id ASC""" % (
                    ",".join(str(x) for x in user_ids),
                    already_added_sql

                 )
        print("sql:", sql)

        with session_scope() as session:
            ufi_user_ids = user_ids
            if include_admins:
                ufi_user_ids = merge_admin_user_ids(session, user_ids)

            # Check the preload and make sure all the users have files
            # up to their minimums ready.
            preloaded = picker.get_preload(
                user_ids=user_ids,
                remove_item=False,
                primary_user_id=primary_user_id,
                prefetch_num=prefetchNum,
                secondary_prefetch_num=secondaryPrefetchNum
            )

            for p in preloaded:
                session_add(session, p)

            # TODO wait

            # 1. Select prefetchNum files for primary_user_id
            # 2. Select secondaryPrefetchNum for secondary_user_ids
            files = session.query(File)\
                           .from_statement(
                                text(sql))\
                           .all()

            group_by_user = {}
            for f in files:
                session_add(session, f)
                f_id = f.id
                user_id = 0
                session_add(session, f)
                if f_id in already_added:
                    continue
                already_added.append(f_id)

                filename = fnCache.get(f_id, f.filename)
                session_add(session, f)
                fnCache[f_id] = filename
                # print("f.filename:", filename)

                if not filename.lower().endswith(".mp3"):
                    if converter.converting and len(converter.files) > 10:
                        continue
                    session_add(session, f)
                    _id = f.id
                    dst = convert_filename(_id)
                    if not os.path.exists(dst):
                        locations = []
                        for l in f.locations:
                            session_add(session, l)
                            locations.append(l.json())

                        jobs.append(cmd=convert,
                                    id=_id,
                                    locations=locations,
                                    to='.mp3',
                                    unique=True)

                        continue  # for f in files:
                if f.cued:
                    user_id = f.cued['user_id']
                if not group_by_user.get(user_id):
                    group_by_user[user_id] = []
                if not group_by_user_file_ids.get(user_id):
                    group_by_user_file_ids[user_id] = []
                if user_id != primary_user_id:
                    if (len(group_by_user[user_id]) +
                        len(group_by_user_file_ids[user_id])) >= (
                            secondaryPrefetchNum):
                        # skip because we've fetched enough.
                        continue
                elif user_id == primary_user_id:
                    if (len(group_by_user[user_id]) +
                        len(group_by_user_file_ids[user_id])) >= (
                            prefetchNum):
                            # skip because we've fetched enough.
                            continue

                # Group the files by their user_id.
                session_add(session, f)
                item = f.json(user_ids=ufi_user_ids, get_image=False)
                group_by_user[user_id].append(item)

        file_found = True
        result = []
        while file_found:
            file_found = False
            for user_id in group_by_user:
                if len(group_by_user[user_id]) > 0:
                    # Grab the first item so it matches the order it
                    # was placed in the array.
                    item = group_by_user[user_id].pop(0)
                    file_found = True
                    result.append(item)

        return {"STATUS": "OK",
                "preload": result}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def playedSince(self, *args, **kwargs):
        # The concept for this section of code is to keep track of the
        # timestamp so if a user on one device plays a file it will
        # be removed on other devices.
        # It limits the query to files only on the device so it will
        # limit the result to only files the device cares about.
        # If any of the files are in the preload it will not delete them.
        post_data = cherrypy.request.json

        listener_user_ids = post_data.get('listener_user_ids', [])
        primary_user_id = int(post_data.get('primary_user_id'))
        secondary_user_ids = post_data.get('secondary_user_ids', [])
        file_ids = post_data.get("file_ids", [])

        primary_user_id = int(primary_user_id)
        listener_user_ids = listener_user_ids + [primary_user_id]
        listener_user_ids = list(set(listener_user_ids))
        user_ids = listener_user_ids + secondary_user_ids + [primary_user_id]
        user_ids = list(set(user_ids))
        user_ids = [int(x) for x in user_ids]
        file_ids = [int(x) for x in file_ids]
        str_user_ids = ",".join(str(x) for x in user_ids)
        str_file_ids = ",".join(str(x) for x in file_ids)

        removeTimestamp = to_int(post_data.get("removeTimestamp", 0))
        removeThreshold = time() - (24 * 60 * 60 * 31)  # 31 days
        if removeTimestamp < removeThreshold:
            removeTimestamp = removeThreshold

        # The goal here is to get any recently played files that aren't
        # in the preload to tell the system it's ok to delete them.
        sql = """SELECT ufi.*
                 FROM user_file_info ufi
                 WHERE time_played >= %d AND
                       ufi.user_id IN (%s) AND
                       ufi.file_id IN (%s) AND
                       ufi.file_id NOT IN(SELECT file_id
                                          FROM preload
                                          WHERE user_id IN (%s))
                 ORDER BY ufi.time_played DESC""" % (
                    removeTimestamp,
                    str_user_ids,
                    str_file_ids,
                    str_user_ids
                 )

        print("QUERY:", sql)

        result = []
        with session_scope() as session:
            ufis = session.query(UserFileInfo)\
                           .from_statement(
                                text(sql))\
                           .all()
            for ufi in ufis:
                session_add(session, ufi)
                result.append(ufi.json())

        return {"STATUS": "OK",
                "result": result}

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def fileSync(self, *args, **kwargs):
        post_data = cherrypy.request.json
        # print("newSync:", args, kwargs)
        # print("post_data:", post_data)
        result = {}
        user_ids = []
        for user_id in post_data.get('user_ids', []):
            user_ids.append(user_id)

        print("post_data:", pformat(post_data))

        deviceTimestamp = float(post_data.get("deviceTimestamp"))
        serverTimestamp = time()
        print ("deviceTimestamp:%s\n"
               "serverTimestamp:%s" % (deviceTimestamp, serverTimestamp))

        with session_scope() as session:
            ufi_user_ids = merge_admin_user_ids(session, user_ids)

            file_id = post_data.get("id")
            dbInfo = session.query(File)\
                            .filter(File.id == file_id)\
                            .first()
            if not dbInfo:
                return {"STATUS": "ERROR",
                        "result": result,
                        "ERROR": "No dbInfo for file_id: %s" % file_id}

            post_data_timestamp = to_int(post_data.get('timestamp', 0))
            dbInfo_timestamp = to_int(dbInfo.timestamp)

            print("post_data_timestamp:%s\n"
                  "dbInfo_timestamp:   %s" % (
                    post_data_timestamp, dbInfo_timestamp))

            played = to_bool(post_data.get("played", False))
            deleted = to_bool(post_data.get("deleted", False))

            if played or deleted:
                session.query(Preload)\
                               .filter(Preload.file_id == file_id)\
                               .delete()
                session.commit()

                exists = session.query(Preload)\
                                .filter(Preload.file_id == file_id)\
                                .first()
                print("removed file_id from preload:", file_id)
                print("proof:", exists)

            session.add(dbInfo)

            if post_data_timestamp >= dbInfo_timestamp:
                for ns_ufi in post_data.get("user_file_info", []):
                    print("ns_ufi:", pformat(ns_ufi))
                    and_filter = and_(
                        UserFileInfo.file_id == ns_ufi['file_id'],
                        UserFileInfo.user_id == ns_ufi['user_id']
                    )
                    db_ufi = session.query(UserFileInfo)\
                                    .filter(and_filter)\
                                    .first()
                    session_add(session, db_ufi)

                    db_ufi_timestamp = to_int(db_ufi.timestamp)
                    ns_ufi_timestamp = to_int(ns_ufi.get("timestamp", 0))
                    force = False

                    print("db_ufi_timestamp:", db_ufi_timestamp)
                    print("ns_ufi_timestamp:", ns_ufi_timestamp)

                    if not db_ufi.timestamp or force or \
                       db_ufi_timestamp <= (ns_ufi_timestamp + 10):
                        sync_keys = ["time_played", "rating", "skip_score",
                                     "true_score", "voted_to_skip",
                                     "timestamp"]
                        for k in sync_keys:
                            value = ns_ufi.get(k)
                            if value is None:
                                continue
                            if k == "voted_to_skip":
                                value = to_bool(value)
                            if k in("timestamp", "time_played") and not value:
                                continue

                            old_value = getattr(db_ufi, k)
                            if old_value == value:
                                continue
                            print("set %s => %s was:%s" % (
                                k, value, old_value))
                            session_add(session, db_ufi)
                            setattr(db_ufi, k, value)
                        session_add(session, db_ufi)
                        session.commit()
                        db_ufi.calculate_true_score()
                    else:
                        print("db_ufi.timestamp > ns_ufi['timestamp']")
                        print(db_ufi.timestamp, ns_ufi['timestamp'])
                    session.commit()

                # mark as played AFTER
                if post_data.get("played", False):
                    mark_as_played_kwargs = {
                        "user_ids": user_ids,
                        "percent_played": to_int(
                            post_data.get('percent_played', 0)),
                        "now": to_int(post_data.get('now', 0)),
                        "force": True
                    }

                    try:
                        dbInfo.mark_as_played(**mark_as_played_kwargs)
                    except Exception as e:
                        print("dbInfo.mark_as_played Exception:", e)
                    session_add(session, dbInfo)
                    session.commit()

            elif dbInfo_timestamp > post_data_timestamp:
                print("dbInfo_timestamp > post_data_timestamp")

            session.commit()

            dbInfo = session.query(File)\
                            .filter(File.id == file_id)\
                            .first()

            session.add(dbInfo)

            result = dbInfo.json(history=True, user_ids=ufi_user_ids,
                                 get_image=False)

            print("AFTER dbInfo:", pformat(result))

        return_data = {
            "STATUS": "OK",
            "deleted": False,
            "result": result
        }
        if deleted:
            return_data['deleted'] = True

        return return_data

    @cherrypy.expose
    @cherrypy.tools.json_in()
    @cherrypy.tools.json_out()
    def sync(self, *args, **kwargs):
        result = {
            "result": "OK",
            "processed_history": [],
            "preload": [],
            "history": [],
            "playing": {}
        }
        post_data = cherrypy.request.json
        listener_user_ids = post_data.get("listeners", {}).get(
            "listener_user_ids", [])
        secondary_user_ids = post_data.get("listeners", {}).get(
            "secondary_user_ids", [])
        satellite_preload_collection = post_data.get("preload", {})
        satellite_playlist_collection = post_data.get("playlist", {})

        satellite_state = int(satellite_playlist_collection.get("state", 0))
        print("*"*100)
        print("satellite_state:", satellite_state)
        # with session_scope() as session:

        with session_scope() as session:
            # Always sync this data so it's marked as played.
            files = satellite_playlist_collection.get("files", [])
            for f in files:
                for ufi in f['user_file_info']:
                    self.process_satellite_ufi(ufi)
                _f = session.query(File)\
                            .filter(File.id == f.get("id"))\
                            .first()
                if _f:
                    session.add(_f)
                    result['processed_history'].append(
                        _f.json(history=True, user_ids=listener_user_ids))
            files = satellite_preload_collection.get("files", [])
            for f in files:
                for ufi in f['user_file_info']:
                    self.process_satellite_ufi(ufi)
                _f = session.query(File)\
                            .filter(File.id == f.get("id"))\
                            .first()
                if _f:
                    session.add(_f)
                    result['processed_history'].append(
                        _f.json(history=True, user_ids=listener_user_ids))

        print("satellite_state:", satellite_state)
        kwargs = {
            "params": {
                "s": 0,
                "l": 10,
                "oc": False,
                "raw": True
            },
            "user_ids": listener_user_ids
        }
        result['history'] = self.search(**kwargs)
        result['history'].reverse()
        result['preload'] = self.preload(**{
            "user_ids": listener_user_ids,
            "raw": True
        })

        result["sync_priority"] = ""

        satellite_last_action = float(post_data.get("lastAction", 0))

        if playlist.player.state_string == "PLAYING" and\
           satellite_state == MEDIA_PLAYING:
                print("Mothership & satellite are playing")
        elif (playlist.player.state_string == "PLAYING" and
              satellite_state != MEDIA_PLAYING):
                result["sync_priority"] = "mothership"
        elif (playlist.player.state_string != "PLAYING" and
              satellite_state == MEDIA_PLAYING):
                result["sync_priority"] = "satellite"
                playing = satellite_playlist_collection.get("playing", {})
                if playing and playing != {}:
                    playlist.reset()
        else:
            # Neither are playing.
            if satellite_last_action > playlist.last_action:
                playing = satellite_playlist_collection.get("playing", {})
                if playing and playing != {}:
                    playlist.reset()
                    result["sync_priority"] = "satellite"
            else:
                result["sync_priority"] = "mothership"

        result['playing'] = playlist.files[playlist.index].json(
            history=True,
            user_ids=listener_user_ids)
        print("playlist.last_action", playlist.last_action)
        print("satellite_last_action", satellite_last_action)
        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def artist_letters(self):
        result = []
        with session_scope() as session:
            """
            # recommended
            cmd = 'select * from Employees where EmployeeGroup == :group'
            employeeGroup = 'Staff'
            employees = connection.execute(text(cmd), group = employeeGroup)"""

            sql = """SELECT DISTINCT(LOWER(SUBSTRING(name,1,1))) AS letter
                     FROM artists
                     ORDER BY letter"""

            letters = session.execute(text(sql))
            for l in letters:
                result.append(l[0])

        return result

    @cherrypy.expose
    @cherrypy.tools.json_out()
    def artists(self, *args, **kwargs):
        result = []
        letter = kwargs.get("l")
        print("letter:", letter)
        if not letter:
            return result
        """
        files = session.query(File)\
                           .from_statement(
                                text(search_query))\
                           .params(**query_args)\
                           .all()"""

        with session_scope() as session:
            spec = {
                "letter": "%s%%" % letter
            }
            sql = """SELECT *
                     FROM artists
                     WHERE name ILIKE :letter
                     ORDER BY name"""
            artists = session.query(Artist)\
                             .from_statement(text(sql))\
                             .params(**spec)\
                             .all()
            for a in artists:
                result.append(a.name)
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
    """
    if isinstance(data,dict):
        print("data:",)
        pprint(data)
    """
    return TextMessage(json.dumps(data))


def broadcast_jobs():
    json_broadcast({'jobs': job_data})


def json_broadcast(data):
    # print("json_broadcast:", data)
    cherrypy.engine.publish('websocket-broadcast', JsonTextMessage(data))


def broadcast(data):
    if not data.get('time-status'):
        print("BROADCAST:", data)
    json_broadcast(data)
    return
    if not data.get('time-status'):
        print ("BROADCAST:", json.dumps(data, sort_keys=True,
                                        indent=4, separators=(',', ': ')))

    broadcast_countdown()
    json_broadcast({'vote_data': vote_data})


def get_all_users():
    results = []
    with session_scope() as session:
        users = session.query(User)\
                       .order_by(User.listening.desc().nullslast(),
                                 User.admin.desc().nullslast(),
                                 User.name.nullslast())\
                       .all()
        for u in users:
            results.append(u.json())
    return results


def merge_admin_user_ids(session, user_ids=[]):
    user_ids = [int(x) for x in user_ids]
    ufi_user_ids = []
    or_filter = or_(User.admin == True,
                    User.id.in_(user_ids))
    users = session.query(User)\
                   .filter(or_filter)\
                   .order_by(User.admin.desc().nullslast(),
                             User.name.nullslast())\
                   .all()

    for u in users:
        if u.id not in ufi_user_ids:
            ufi_user_ids.append(u.id)

    return ufi_user_ids
