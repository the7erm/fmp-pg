from twisted.internet import gtk2reactor # for gtk-2.0
gtk2reactor.install()

from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site
import gobject
from twisted.internet import reactor
import json

from flask import Flask, Response
from flask import render_template
from player_refactored import STOPPED, PAUSED, PLAYING

from files_model_idea import simple_rate, FileInfo, session

app = Flask(__name__)
app.debug = True

jukebox = None
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

@app.route('/')
def index():
    return render_template("index.html", jukebox=jukebox)

@app.route('/search/')
def search():
    return render_template("search.html", jukebox=jukebox)

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

    return {
        'playing': jukebox.playing.to_dict(JUKEBOX_PLAYING_KEYS),
        'pos_data': jukebox.player.pos_data,
        'state': state
    }

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
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)

@app.route('/prev/')
def prev():
    jukebox.prev()
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)

@app.route("/rate/<fid>/<uid>/<rating>")
def rate(fid, uid, rating):
    fid = int(fid)
    uid = int(uid)
    rating = int(rating)
    # TODO LOOP THROUGH JUKEBOX
    found = False
    if jukebox.playing.fid == fid:
        found = jukebox.rate(uid, rating)

    if not found:
        simple_rate(fid, uid, rating)
    obj = status_obj()
    obj['STATUS'] = 'SUCCESS'
    return json_response(obj)



@app.route("/stream/<fid>/<format>")
def stream(fid, format):
    def do_stream(fid, format):
        file_info = session.query(FileInfo)\
                           .filter(FileInfo.fid==fid)\
                           .limit(1)\
                           .one()
        fp = open(file_info.filename, "r")
        data = fp.read(102400)
        yield data
        while data:
            data = fp.read(102400)
            yield data
    if format == 'mp3':
        mimetype = "audio/mpeg"
    if format == 'ogg':
        mimetype = "audio/ogg"
    """
    <audio controls>
      <source src="horse.ogg" type="audio/ogg">
      <source src="horse.mp3" type="audio/mpeg">
    Your browser does not support the audio element.
    </audio>"""
    return Response(do_stream(fid, format), mimetype=mimetype)

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
reactor.listenTCP(5050, Site(resource))

def start():
    gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    reactor.startRunning()

if __name__ == '__main__':
    reactor.run()
    # gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    # reactor.startRunning()
