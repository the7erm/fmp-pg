from __init__ import *
from flask import Flask
from flask import request
from flask import redirect
from flask import session
from flask import jsonify
import random
import time
import hashlib
import json

from player import PLAYING

import threading

from flask import render_template

threads = []

app = Flask(__name__)

@app.route("/")
def index():
    global playing, player
    print "FLASK PLAYING:", playing.filename
    print "REQUEST:",request
    print "request.args:",request.args
    cmd = request.args.get("cmd","")
    if cmd:
        if cmd == "pause":
            player.pause()
        if cmd == "next":
            player.next()
        if cmd == "prev":
            player.prev()
        return redirect("/")
    return render_template("index.html", player=player, playing=playing, PLAYING=PLAYING)

@app.route("/status/")
def status():
    # -{{player.pos_data["left_str"]}} {{player.pos_data["pos_str"]}}/{{player.pos_data["dur_str"]}}
    global player, playing
    print "PLAYING",playing.to_dict()

    return jsonify(player=player.to_dict(), playing=playing.to_dict())

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # session['username'] = request.form['username']
        user = get_assoc("""SELECT * 
                            FROM users 
                            WHERE uname = %s 
                            LIMIT 1""", (request.form['username'],))
        if user:

            return redirect(url_for('index'))


    return render_template("login.html", playing=playing, PLAYING=PLAYING)

def worker(*args, **kwargs):
    """thread worker function"""
    print 'WORKER, args:',args, kwargs
    app.run(debug=False, host='0.0.0.0', port=5050)
    return


def start_in_thread():
    print "START CALLED!"
    t = threading.Thread(target=worker, args=(0,))
    threads.append(t)
    t.start()

def start():
    print "START()"
    worker()

def call_test():
    print "CALL TEST COMPLETED"


if __name__ == "__main__":
    app.run(debug=False, host='0.0.0.0', port=5050)

