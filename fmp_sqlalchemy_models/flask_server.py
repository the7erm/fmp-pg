from twisted.internet import gtk2reactor # for gtk-2.0
gtk2reactor.install()

from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site
import gobject
from twisted.internet import reactor
import json
import subprocess
import os
import time
import re
from flask import Flask, Response, render_template, request, send_file, session
from player_refactored import STOPPED, PAUSED, PLAYING
from jukebox import HISTORY_LENGTH
from picker import Picker

from sqlalchemy import and_
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import InvalidRequestError

from user import User
from file_info import FileInfo
from keywords import Keywords
from files_model_idea import simple_rate, MIME_TYPES, AUDIO_MIMES, VIDEO_MIMES
from baseclass import log
from alchemy_session import db_connection_string, DB, Base
db = DB(db_connection_string)

def make_session():
    return db.session(Base)

TEMP_FOLDER = "/home/erm/tmp/converted/"

app = Flask(__name__)
app.debug = True
app.secret_key = '\xd1\x1bF\xa7\xee\xdd\x1f\xce\xec\xd9\xff\x9a\xd5\x9c\x9d\x98qN\n\x0e\xec \xb7\xfb'


jukebox = None
jukebox_fid = None
JUKEBOX_PLAYING_KEYS = [
    'fid',
    'artist_title',
    'artists',
    'titles',
    'genres',
    'albums',
    'listeners_ratings',
    'history',
    'keywords'
]

def get_listeners():
    sqla_session = make_session()
    listeners = sqla_session.query(User).order_by(User.admin.desc(), User.uname.asc()).all()
    sqla_session.close()
    return listeners

def get_file_info(fid):
    sqla_session = make_session()
    file_info = sqla_session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    print "GET FILE INFO:", file_info.to_dict(JUKEBOX_PLAYING_KEYS)
    sqla_session.close()
    return file_info

@app.route('/')
def index():
    listeners = get_listeners()
    playing = get_file_info(jukebox.fid)
    pos_data = jukebox.player.pos_data

    playing_fid = get_playing_fid(listeners)
    session['playing_fid'] = playing_fid

    return render_template("index.html", pos_data=pos_data, playing=playing, 
                           listeners=listeners)

def get_playing_fid(listeners):
    """
    session['percent_played'] = percent_played
    session['playing_fid'] = fid
    session['mode'] = request.form['mode']
    session['webPlayerMode'] = request.form['webPlayerMode']
    session['singleModeUid'] = request.form['singleModeUid']
    """

    mode = session.get('mode', 'remote')
    if mode == 'remote':
        return jukebox.fid
    web_player_mode = session.get('webPlayerMode', 'multi')
    if web_player_mode == 'multi':
        return session.get('playing_fid', jukebox.fid)

    sqla_session = make_session()
    try:
        most_recent = sqla_session.query(UserHistory)\
                                  .filter(and_(
                                        UserHistory.uid == session.get(
                                            'singleModeUid', listeners[0].uid),
                                        UserHistory.time_played != None
                                   ))\
                                  .order_by(UserHistory.time_played.desc())\
                              .limit(1)\
                              .one()
    except NoResultFound:
        sqla_session.close()
        return jukebox.fid
    sqla_session.close()
    return most_recent.fid


@app.route('/search/')
def search():
    sqla_session = make_session()
    keywords = request.args.get('q', '').lower().split(' ')
    offset = int(request.args.get('o', 0))

    query = sqla_session.query(FileInfo)\
                        .filter(Keywords.word.in_(keywords))\
                        .limit(10)\
                        .offset(offset)

    """
    KEYWORDS: [u'test', u'again']
    QUERY: SELECT files_info.fid AS files_info_fid, files_info.ltp AS files_info_ltp, files_info.fingerprint AS files_info_fingerprint, files_info.file_size AS files_info_file_size 
    FROM files_info, keywords 
    WHERE keywords.word IN (:word_1, :word_2)
     LIMIT :param_1 OFFSET :param_2

    This should have something referencing file_keywords table
    """
    
    results_list = []
    print "KEYWORDS:", keywords
    print "QUERY:",query
    for r in query.all():
        results_list.append(r.to_dict(JUKEBOX_PLAYING_KEYS))
    sqla_session.close()
    return json_response(results_list)

@app.route('/history/<uids>')
def history(uids):
    sqla_session = make_session()
    uids = uids.split(',')
    history = jukebox.get_history(uids, session=sqla_session);
    resp = json_response(history)
    sqla_session.close()
    return resp

@app.route('/listening/<uid>/<state>')
def listening(uid, state):
    uid = int(uid)
    listening_state = False
    if state == 'true':
        listening_state = True
    sqla_session = make_session()
    try:
        user = sqla_session.query(User)\
                      .filter(User.uid == uid)\
                      .limit(1)\
                      .one()
        user.listening = listening_state
        user.save(session=sqla_session)
        if listening_state:
            picker = Picker(session=sqla_session)
            picker.do()
        resp = json_response({'STATUS': 'SUCCESS'})
    except NoResultFound:
        resp = json_response({'STATUS': 'FAIL'})
    finally:
        sqla_session.close()
    return resp

@app.route("/pop-preload/<uids>")
def pop_preload(uids):
    print '@app.route("/pop-preload/%s")' % (uids,)
    uids = uids.split(",")
    sqla_session = make_session()
    picker = Picker(session=sqla_session)
    file_info = picker.pop(uids)
    resp = json_response(file_info.to_dict(JUKEBOX_PLAYING_KEYS))
    sqla_session.commit()
    sqla_session.close()
    print '[DONE]@app.route("/pop-preload/")'
    return resp

def json_response(obj):
    json_obj = json.dumps(obj, indent=4)
    return Response(response=json_obj,
                    status=200,
                    mimetype="application/json")

def status_obj():
    player_state = jukebox.player.playingState
    state = 'STOPPED'
    if player_state == PLAYING:
        state = 'PLAYING'
    elif player_state == PAUSED:
        state = 'PAUSED'

    playing = get_file_info(jukebox.fid)

    return {
        'playing': playing.to_dict(JUKEBOX_PLAYING_KEYS),
        'pos_data': jukebox.player.pos_data,
        'state': state
    }

@app.route('/file-info/<fid>')
def file_info(fid):
    file_info = get_file_info(fid)
    sqla_session = make_session()
    sqla_session.add(file_info)
    dict_file_info = file_info.to_dict(JUKEBOX_PLAYING_KEYS)
    resp = json_response(dict_file_info)
    sqla_session.close()
    return resp

@app.route('/status/')
def status():
    obj = status_obj()
    session['percent_played'] = obj['pos_data']['decimal'] * 100;
    session['playing_fid'] = obj['playing']['fid'];
    session['mode'] = 'remote'
    return json_response(obj)

@app.route('/pause/')
def pause():
    jukebox.pause()
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)

@app.route('/next/')
def next():
    jukebox.next()
    time.sleep(1)
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)

@app.route('/prev/')
def prev():
    jukebox.prev()
    time.sleep(1)
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)

@app.route("/rate/<fid>/<uid>/<rating>", methods=['POST', 'PUT'])
def rate(fid, uid, rating):
    fid = int(fid)
    uid = int(uid)
    rating = int(rating)
    found = False
    
    if jukebox.fid == fid:
        found = jukebox.rate(uid, rating)
    if not found:
        sqla_session = make_session()
        simple_rate(fid, uid, rating, sqla_session)
        sqla_session.commit()
        sqla_session.close()
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)


@app.route("/stream/<fid>/")
def stream(fid):
    print '@app.route("/stream/%s/")' % (fid,)
    def do_converting_stream(filename, mimetype):
        # gst-launch  -q filesrc location=./test.avi ! 
        # decodebin2 ! audioconvert  ! lame ! fdsink fd=1 > out.mp3
        basename = os.path.basename(filename)
        convert_with = 'lame'
        ext = '.mp3'
        if mimetype == AUDIO_MIMES['.ogg']:
            ext = '.ogg'
            convert_with = 'vorbisenc'

        temp_location = os.path.join(TEMP_FOLDER, basename)
        lock_file = temp_location + ".lock" + ext
        converted_file = temp_location + ".converted" + ext
        if os.path.exists(converted_file):
            print "converted_file exists"
            # if the lock file exists ... 
            if not os.path.exists(lock_file):
                print "streaming already converted file"
                fp = open(converted_file, "r")
                data = fp.read(10240)
                yield data
                while data:
                    data = fp.read(10240)
                    if not data:
                        time.sleep(1)
                        data = fp.read(10240)
                    yield data
                return

            size = os.path.getsize(converted_file)
            subprocess.check_call(["sync"])
            time.sleep(1)
            if size > os.path.getsize(converted_file):
                print "file being converted streaming..."
                # It's being converted by another process stream the file.
                fp = open(converted_file, "r")
                data = fp.read(10240)
                yield data
                while data:
                    data = fp.read(10240)
                    if not data:
                        time.sleep(1)
                        data = fp.read(10240)
                    yield data
                return

        # TODO remove converted file & lock_file if the stream is canceled.
        open(lock_file, "w").close()
        dstfp = open(converted_file, "w")
        args = [
                'gst-launch', '-q',
                'filesrc', 'location=%s' % filename, '!',
                'decodebin2', '!',
                'audioconvert', '!',
                convert_with, '!',
                'fdsink', 'fd=1'
            ]
        print "ARGS:"
        process = subprocess.Popen(args, shell=False, 
            stdout=subprocess.PIPE)
        data = process.stdout.read(10240)
        dstfp.write(data)
        yield data
        while data:
            data = process.stdout.read(10240)
            dstfp.write(data)
            dstfp.flush()
            yield data
        print "DONE CONVERTING"
        os.unlink(lock_file)
        dstfp.close()

    sqla_session = make_session()
    print "made session"
    mimetypes = request.args.get("mimetypes", "")
    mimetypes = mimetypes.split(',')
    fid = int(fid)
    print "GETTING FILE INFO"
    file_info = sqla_session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    sqla_session.add(file_info)
    print "fetched file info."
    mimetype = file_info.get_best_mime(mimetypes)
    send_as_file = True
    filename = file_info.filename
    size = file_info.size
    stream_handler = None
    if mimetype != file_info.mimetype:
        basename = os.path.basename(filename)
        ext = '.mp3'
        if mimetype == AUDIO_MIMES['.ogg']:
            ext = '.ogg'
        temp_location = os.path.join(TEMP_FOLDER, basename)
        lock_file = temp_location + ".lock" + ext
        converted_file = temp_location + ".converted" + ext
        if os.path.exists(converted_file) and not os.path.exists(lock_file):
            filename = converted_file
            size = os.path.getsize(filename)
            send_as_file = True
        else:
            size = 0
            send_as_file = False

    print "MADEIT", mimetype
    sqla_session.close()
    if send_as_file:
        print '[DONE]@app.route("/stream/%s/") send as file' % (fid,)
        return send_file_partial(filename, mimetype=mimetype)
    response = Response(do_converting_stream(filename, mimetype), mimetype=mimetype)
    if size:
        response.headers.add('Content-Length', str(size))
        response.headers.add('Content-Range', 'bytes 0-%s/%s' % (size, size))
        response.headers.add('Accept-Ranges', 'bytes')
        # response.headers.add('Content-Type', mimetype)
        # Content-Range:bytes 0-6202476/6202477
    print '[DONE]@app.route("/stream/%s/") convert' % (fid,)
    return response

@app.route("/mark-as-played/<fid>/<percent_played>/<uids>", methods=['POST', 'GET'])
def mark_as_played(fid, percent_played, uids):
    fid = int(fid)
    uids = uids.split(',')
    percent_played = float(percent_played)
    print '@app.route("/mark-as-played/%s/%s/%s")' % (fid, percent_played, uids)
    obj = {}
    obj['STATUS'] = 'SUCCESS'
    print "MARCUS PLAYED", "uids:", uids, "percent_played:", percent_played
    sqla_session = make_session()
    print "session made for markus"
    try_cnt = 0;
    while try_cnt < 10:
        try:
            file_info = sqla_session.query(FileInfo)\
                                    .filter(FileInfo.fid == fid)\
                                    .limit(1)\
                                    .one()
            print "file info:", file_info
        except InvalidRequestError, e:
            try_cnt += 1
            print "*"*80
            print "InvalidRequestError:",e
            sqla_session.rollback()
            time.sleep(0.1)
            continue
        break

    if try_cnt >= 10:
        print "Failed"
        sqla_session.close()
        return json_response({})
    session['percent_played'] = percent_played
    session['playing_fid'] = fid
    session['mode'] = request.form['mode']
    session['webPlayerMode'] = request.form['webPlayerMode']
    session['singleModeUid'] = request.form['singleModeUid']

    print "session:",session

    print "file_info was fetched"
    file_info.mark_as_played(percent_played=percent_played, uids=uids, session=sqla_session)
    print "actual mark_as_played succeeded"
    resp = json_response(file_info.to_dict(JUKEBOX_PLAYING_KEYS))
    print '[DONE]@app.route("/mark-as-played/%s/%s/%s")' % (fid, percent_played, uids)
    sqla_session.close()
    return resp

@app.route("/set-mode/<mode>/<currentTime>")
def set_mode(mode, currentTime):
    print "set_mode"
    if mode in ('web', 'remote'):
        session['mode'] = mode
    if mode == 'remote':
        sync_jukebox()
    if mode == 'web' and jukebox.player.playingState == PLAYING:
        print "MODE CHANGED TO WEB"
        jukebox.player.force_pause()

    return json_response({'STATUS': 'SUCCESS'})

def sync_jukebox():
    # TODO make sure the user is listening (they should be, but just in case)
    if jukebox.player.playingState == PLAYING:
        return

    playing_fid = int(session.get('playing_fid', jukebox.fid))
    if jukebox.history[jukebox.index] != playing_fid:
        jukebox.history.append(playing_fid)
        juekbox.index = len(jukebox) - 1
    jukebox.start(mark_as_played=False)
    percent_played = float(session.get('percent_played', 
                                        jukebox.playing.listeners_ratings[0].percent_played))
    duration = jukebox.player.get_duration()
    pos_ns = int(duration * (percent_played * 0.01))
    jukebox.player.seek_ns(pos_ns)


@app.route("/set-web-player-mode/<mode>")
def set_webplayer_mode(mode):
    print "set_webplayer_mode"
    if mode in ('multi', 'single'):
        session['webPlayerMode'] = mode
    return json_response({'STATUS': 'SUCCESS'})

@app.route("/set-single-player-uid/<uid>")
def set_single_player_mode(uid):
    uid = int(uid)
    session['singleModeUid'] = uid
    return json_response({'STATUS': 'SUCCESS'})

@app.route("/inc-skip-score/<fid>/<uids>")
def inc_skip_score(fid, uids):
    fid = int(fid)
    uids = uids.split(',')
    print '@app.route("/inc-skip-score/%s/%s")' % (fid, uids)
    if not fid or not uids:
        return json_response({"STATUS": "FAIL"})
    sqla_session = make_session()
    file_info = sqla_session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    
    file_info.inc_skip_score(uids=uids, session=sqla_session)
    resp = json_response(file_info.to_dict(JUKEBOX_PLAYING_KEYS))
    sqla_session.close()
    print '[DONE]@app.route("/inc-skip-score/%s/%s")' % (fid, uids)
    return resp


@app.route("/deinc-skip-score/<fid>/<uids>")
def deinc_skip_score(fid, uids):
    fid = int(fid)
    uids = uids.split(',')
    print '@app.route("/deinc-skip-score/%s/%s")' % (fid, uids)
    if not fid or not uids:
        return json_response({"STATUS": "FAIL"})
    sqla_session = make_session()
    file_info = sqla_session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    file_info.deinc_skip_score(uids=uids, session=sqla_session)
    resp = json_response(file_info.to_dict(JUKEBOX_PLAYING_KEYS))
    sqla_session.close()
    print '[DONE]@app.route("/deinc-skip-score/%s/%s")' % (fid, uids)
    return resp

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
reactor.listenTCP(5050, Site(resource))

@app.after_request
def after_request(response):
    # stolen from http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
    response.headers.add('Accept-Ranges', 'bytes')
    return response


def send_file_partial(path, *args, **kwargs):
    # stolen from http://blog.asgaard.co.uk/2012/08/03/http-206-partial-content-for-flask-python
    print "SEND PARTIAL FILE:",path
    """ 
        Simple wrapper around send_file which handles HTTP 206 Partial Content
        (byte ranges)
        TODO: handle all send_file args, mirror send_file's error handling
        (if it has any)
    """
    range_header = request.headers.get('Range', None)
    if not range_header:
        return send_file(path, *args, **kwargs)
    
    size = os.path.getsize(path)    
    byte1, byte2 = 0, None
    
    m = re.search('(\d+)-(\d*)', range_header)
    g = m.groups()
    
    if g[0]: byte1 = int(g[0])
    if g[1]: byte2 = int(g[1])

    length = size - byte1
    if byte2 is not None:
        length = byte2 - byte1
    
    data = None
    with open(path, 'rb') as f:
        f.seek(byte1)
        data = f.read(length)

    mimetype = kwargs.get('mimetype', 'application/octet-stream')

    rv = Response(data, 
        206,
        mimetype=mimetype, 
        direct_passthrough=True)
    rv.headers.add('Content-Range', 'bytes {0}-{1}/{2}'.format(byte1, byte1 + length - 1, size))

    return rv

def start():
    gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    reactor.startRunning()

if __name__ == '__main__':
    reactor.run()
    # gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    # reactor.startRunning()
