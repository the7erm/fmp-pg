#!/usr/bin/env python2
import sys
import os
import time
from subprocess import PIPE, Popen
from threading  import Thread
import json
import pprint
import glob
import datetime

def json_handler(obj):
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    else:
        return obj
    #else:
    #    raise TypeError, 'Object of type %s with value of %s is not JSON serializable' % (type(obj), repr(obj))
pp = pprint.PrettyPrinter(indent=4)

try:
    from Queue import Queue, Empty
except ImportError:
    from queue import Queue, Empty  # python 3.x

ON_POSIX = 'posix' in sys.builtin_module_names

def enqueue_output(out, queue):
    for line in iter(out.readline, b''):
        queue.put(line)
    out.close()

# parts of this code were stolen from
# http://stackoverflow.com/questions/375427/non-blocking-read-on-a-subprocess-pipe-in-python

class FmpPlugin(object):
    def __init__(self, args=None):
        self.connections = [
            'time-status',
            'mark-as-played',
            'end-of-stream',
            'on-state-change',
            'on-scroll'
        ]
        if args is not None:
            self.process = Popen(args, stdout=PIPE, bufsize=1, 
                                 close_fds=ON_POSIX, stdin=PIPE)
        self.recv_que = Queue()
        self.init_thread()
        self.thread.daemon = True # thread dies with the program
        self.thread.start()

    def connect(self, typ):
        # print "CONNECT:",typ
        if isinstance(typ, list):
            for t in typ:
                self.connect(t)
            return

        self.connections.append(typ)
        self.connections = list(set(self.connections))

    def disconnect(self, typ):
        if isinstance(self, FmpPluginParent):
            print "DISCONNECT:",typ
        if isinstance(typ, list):
            for t in typ:
                self.disconnect(t)
            return
        while self.connections.count(typ) > 0:
            
            self.connections.remove(typ)

    def read(self):
        objs = []
        buf = ""
        try:
            line = None
            while line is None or line:
                line = self.recv_que.get_nowait() # or q.get(timeout=.1)
                buf += line
                try:
                    json_obj = json.loads(buf)
                    objs.append(json_obj)
                    buf = ""
                except:
                    pass
        except Empty:
            pass

        return objs

class FmpPluginParent(FmpPlugin):
    def init_thread(self):
        self.thread = Thread(target=enqueue_output, args=(self.process.stdout, 
                             self.recv_que))

    def write(self, obj, msg_type=None):
        keys = obj.keys()
        found = False
        for k in keys:
            if k in self.connections:
                found = True
                break
        if not found:
            return
        # print "WRITE:",obj
        self.process.stdin.write(json.dumps(obj, default=json_handler))
        self.process.stdin.write("\n")
        self.process.stdin.flush()


class FmpPluginChild(FmpPlugin):

    def init_thread(self):
        self.thread = Thread(target=enqueue_output, args=(sys.stdin, self.recv_que))

    def write(self, obj):
        print_json(obj)
        print "\n";

    def write_test(self):
        self.write({
            'response': 'ok'
        })
    
    def read_test(self):
        rec = self.read()
        self.write({"child-process-recv": rec})

    def connect(self, typ):
        self.write({"connect": typ})
        super(FmpPluginChild, self).connect(typ)
        

    def disconnect(self, typ):
        self.write({"disconnect": typ})
        super(FmpPluginChild, self).disconnect(typ)

class FmpPluginWrapper:
    def __init__(self):
        self.plugins = []
        self.disabled = True
        if self.disabled:
            print "DISABLED FmpPluginWrapper"
            return
        files = glob.glob(os.path.join(sys.path[0],'plugins/*'))
        for f in files:
            print "F:",f
            self.plugins.append(FmpPluginParent([f]))
        self.read()

    def write(self, obj):
        if self.disabled:
            return
        print "FmpPluginWrapper.write:", obj
        for p in self.plugins:
            p.write(obj)

        self.read()

    def read(self):
        for p in self.plugins:
            data_from_child = p.read()
            print "READ:", data_from_child
            for res in data_from_child:
                print "RES:",res
                self.process_data_from_child(p, res)

    def process_data_from_child(self, plugin, data_from_child):
        if 'connect' in data_from_child:
            plugin.connect(data_from_child['connect'])
            return
        if 'disconnect' in data_from_child:
            plugin.disconnect(data_from_child['disconnect'])


def print_json(obj):
    print json.dumps(obj, sort_keys=True, indent=2, separators=(',', ': '), 
                     default=json_handler)
    sys.stdout.flush()

def test_child():
    tester = FmpPluginChild()
    while True:
        tester.write_test()
        tester.read_test()
        time.sleep(1)

def test_parent():
    parent = FmpPluginParent(["./fmp_plugin.py", "--test"])
    while True:
        parent.write({"to_child": "ok"})
        print "received:"
        objs = parent.read()
        for o in objs:
            pp.pprint(o)
        time.sleep(1)

if __name__ == '__main__':
    if "--test" in sys.argv:
        test_child()
        sys.exit()

    test_parent()

