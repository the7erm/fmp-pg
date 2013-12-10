from twisted.internet import gtk2reactor # for gtk-2.0
gtk2reactor.install()

from twisted.web.wsgi import WSGIResource
from twisted.web.server import Site
import gobject
from twisted.internet import reactor

from flask import Flask
app = Flask(__name__)
app.debug = True

jukebox = None

@app.route('/')
def index():
    obj = {
        'playing': jukebox.playing.json(['artists', 'titles', 'fid', 'listeners_ratings', 
                                         'genres'])
    }
    return 

resource = WSGIResource(reactor, reactor.getThreadPool(), app)
reactor.listenTCP(5050, Site(resource))

def start():
    gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    reactor.startRunning()

if __name__ == '__main__':
    reactor.run()
    # gobject.idle_add(lambda *x: reactor.runUntilCurrent())
    # reactor.startRunning()
