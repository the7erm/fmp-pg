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

from flask import Flask, Response, render_template, request, send_file
from player_refactored import STOPPED, PAUSED, PLAYING
from jukebox import HISTORY_LENGTH
from picker import Picker

from files_model_idea import simple_rate, FileInfo, MIME_TYPES, \
                             AUDIO_MIMES, VIDEO_MIMES, User, \
                             UserFileInfo, Base

from sqlalchemy.orm.exc import NoResultFound
from alchemy_session import db_connection_string, DB

db = DB(db_connection_string)

def make_session():
    return db.session(Base)

TEMP_FOLDER = "/home/erm/tmp/converted/"

app = Flask(__name__)
app.debug = True

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
    print "GET LISTENERS:"
    session = make_session()
    print "SESSION MADE"
    listeners = session.query(User).order_by(User.admin.desc(), User.uname.asc()).all()
    print "GOT LISTENERS ... "
    print "GOT LISTENERS:", listeners
    session.close()
    return listeners

def get_file_info(fid):
    session = make_session()
    file_info = session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    print "GET FILE INFO:", file_info.to_dict(JUKEBOX_PLAYING_KEYS)
    session.close()
    return file_info

@app.route('/')
def index():
    print "INDEX"
    listeners = get_listeners()
    print "GOT LISTNERS"
    playing = get_file_info(jukebox.fid)
    pos_data = jukebox.player.pos_data
    return render_template("index.html", pos_data=pos_data, playing=playing, 
                           listeners=listeners)

@app.route('/search/')
def search():
    listeners = get_listeners()
    playing = get_file_info(jukebox.fid)
    return render_template("search.html", playing=playing, listeners=listeners)

@app.route('/history/<uids>')
def history(uids):
    session = make_session()
    uids = uids.split(',')
    history = jukebox.get_history(uids, session=session);
    resp = json_response(history)
    session.close()
    return resp

@app.route('/listening/<uid>/<state>')
def listening(uid, state):
    uid = int(uid)
    listening_state = False
    if state == 'true':
        listening_state = True
    session = make_session()
    try:
        user = session.query(User)\
                      .filter(User.uid == uid)\
                      .limit(1)\
                      .one()
        user.listening = listening_state
        user.save(session=session)
        resp = json_response({'STATUS': 'SUCCESS'})
    except NoResultFound:
        resp = json_response({'STATUS': 'FAIL'})
    finally:
        session.close()
    return resp

@app.route("/pop-preload/")
def pop_preload():
    print '@app.route("/pop-preload/")'
    session = make_session()
    picker = Picker(session=session)
    file_info = picker.pop()
    resp = json_response(file_info.to_dict(JUKEBOX_PLAYING_KEYS))
    session.commit()
    session.close()
    print '[DONE]@app.route("/pop-preload/")'
    return resp

@app.route('/web-player/')
def web_player():
    print "WEB player"
    listeners = get_listeners()
    playing = get_file_info(jukebox.fid)
    pos_data = jukebox.player.pos_data
    return render_template("web-player.html", pos_data=pos_data, 
                           playing=playing, listeners=listeners)

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
    session = make_session()
    session.add(file_info)
    dict_file_info = file_info.to_dict(JUKEBOX_PLAYING_KEYS, session=session)
    resp = json_response(dict_file_info)
    session.close()
    return resp

@app.route('/status/')
def status():
    obj = status_obj()
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

@app.route("/rate/<fid>/<uid>/<rating>")
def rate(fid, uid, rating):
    fid = int(fid)
    uid = int(uid)
    rating = int(rating)
    found = False
    
    if jukebox.fid == fid:
        found = jukebox.rate(uid, rating)
    if not found:
        session = make_session()
        simple_rate(fid, uid, rating, session)
        session.commit()
        session.close()
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

    session = make_session()
    print "made session"
    mimetypes = request.args.get("mimetypes", "")
    mimetypes = mimetypes.split(',')
    fid = int(fid)
    print "GETTING FILE INFO"
    file_info = session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    session.add(file_info)
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
    session.close()
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

@app.route("/mark-as-played/<fid>/<percent_played>/<uids>")
def mark_as_played(fid, percent_played, uids):
    fid = int(fid)
    uids = uids.split(',')
    percent_played = float(percent_played)
    print '@app.route("/mark-as-played/%s/%s/%s")' % (fid, percent_played, uids)
    obj = {}
    obj['STATUS'] = 'SUCCESS'
    print "MARCUS PLAYED", "uids:", uids, "percent_played:", percent_played
    session = make_session()
    file_info = session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    file_info.mark_as_played(percent_played=percent_played, uids=uids, session=session)
    resp = json_response(file_info.to_dict())
    print '[DONE]@app.route("/mark-as-played/%s/%s/%s")' % (fid, percent_played, uids)
    session.close()
    return resp

@app.route("/inc-skip-score/<fid>/<uids>")
def inc_skip_score(fid, uids):
    fid = int(fid)
    uids = uids.split(',')
    print '@app.route("/inc-skip-score/%s/%s")' % (fid, uids)
    if not fid or not uids:
        return json_response({"STATUS": "FAIL"})
    session = make_session()
    file_info = session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    
    file_info.inc_skip_score(uids=uids, session=session)
    resp = json_response(file_info.to_dict())
    session.close()
    print '[DONE]@app.route("/inc-skip-score/%s/%s")' % (fid, uids)
    return resp

@app.route("/deinc-skip-score/<fid>/<uids>")
def deinc_skip_score(fid, uids):
    fid = int(fid)
    uids = uids.split(',')
    print '@app.route("/deinc-skip-score/%s/%s")' % (fid, uids)
    if not fid or not uids:
        return json_response({"STATUS": "FAIL"})
    session = make_session()
    file_info = session.query(FileInfo)\
                       .filter(FileInfo.fid == fid)\
                       .limit(1)\
                       .one()
    file_info.deinc_skip_score(uids=uids, session=session)
    resp = json_response(file_info.to_dict())
    session.close()
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
