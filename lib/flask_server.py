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
import socket
import alsaaudio

from player import PLAYING

import threading

from flask import render_template

threads = []

app = Flask(__name__)

@app.route("/")
def index():
    global playing, player, tray
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
        if cmd == "seek_ns":
            pos = request.args.get("value",0)
            player.seek_ns(pos)
            
        if cmd == "rate":
            rating = request.args.get("value",0)
            uid = request.args.get("uid",0)
            print "************* RATE ****************"
            print "RATE:uid:%s rating:%s" % (uid, rating)
            if uid and hasattr(playing, "ratings_and_scores"):
                print "RATE 2:uid:%s rating:%s" % (uid, rating)
                playing.rate(uid=uid, rating=rating)
        if cmd == "vol":
            set_volume(request.args.get("value",-1))

        if request.args.get("status",""):
            return status()
        return redirect("/")
    return render_template("index.html", player=player, playing=playing, 
                           PLAYING=PLAYING, volume=get_volume())

@app.route("/status/")
def status():
    # -{{player.pos_data["left_str"]}} {{player.pos_data["pos_str"]}}/{{player.pos_data["dur_str"]}}
    global player, playing
    # print "PLAYING",playing.to_dict()

    return jsonify(player=player.to_dict(), playing=playing.to_dict(),
                   volume=get_volume())

def get_volume():
    cards = alsaaudio.cards()
    for i, c in enumerate(cards):
        try:
            m = alsaaudio.Mixer('Master',cardindex=i)
            result = m.getvolume()
            volume = result.pop()
            return volume
        except alsaaudio.ALSAAudioError:
            continue
    return -1;


def set_volume(vol):
    cards = alsaaudio.cards()
    print "SET_VOLUME:",vol
    print "type:",type(vol)
    if isinstance(vol, str) or isinstance(vol,unicode):
        print "SET_VOLUME2:",vol
        if vol in ("-","+"):
            cur_vol = get_volume()
            if vol == "-":
                vol = cur_vol - 3
            else:
                vol = cur_vol + 3

            if vol < 0:
                vol = 0
            if vol > 100:
                vol = 100
        print "SET_VOLUME3:",vol
    try:
        vol=int(vol)
    except:
        print "FAIL:",vol
        return

    if vol < 0 or vol > 100:
        return;
    for i, c in enumerate(cards):
        try:
            m = alsaaudio.Mixer('Master',cardindex=i)
            m.setvolume(vol)
        except alsaaudio.ALSAAudioError:
            continue

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
    while True:
        try:
            app.run(debug=False, host='0.0.0.0', port=5050)
        except socket.error, e:
            print "##########################################"
            print "socket.error:",e
            print "##########################################"
            print "ATTEMPTING RE-BIND in 10 seconds"
            time.sleep(10)
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
    worker()
    # app.run(debug=False, host='0.0.0.0', port=5050)

