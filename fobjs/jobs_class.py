#!/usr/bin/env python2
# -*- coding: utf-8 -*-
# fobjs/jobs_class.py -- job cue.
#    Copyright (C) 2015 Eugene Miller <theerm@gmail.com>
#
#    This program is free software; you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation; either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program; if not, write to the Free Software
#    Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst, Gtk, GdkX11, GstVideo, Gdk, Pango,\
                          GLib, Gio
GObject.threads_init()

from time import time
import random

try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

import string
from pprint import pprint, pformat

from log_class import Log, logging, log_failure
logger = logging.getLogger(__name__)

def id_generator(size=8, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))

class ExistingProcessError(Exception):
    pass

class ValidationError(Exception):
    pass

class Process(Log):
    __name__ = "Process"
    process_name = 'process'
    def __init__(self, job_params=None,  *args, **kwargs):
        self.logger = logger
        self.log_debug(".__init__()")
        if job_params is None:
            job_params = {}
        self.params = job_params.get('params', {})
        self.process_name = self.process_name+"->"+job_params.get('name','')
        self.kwargs = kwargs
        
        super(Process, self).__init__(*args, **kwargs)
        self.last_progress_time = time()
        self.id = self.params.get('id', id_generator())
        

        self.log_debug(".__init__() params:", self.params)
        if not server.job_data.get(self.process_name):
            server.job_data[self.process_name] = {}
        
        valid = self.validate()
        if not valid:
            raise ValidationError('Error validating process')

        server.job_data[self.process_name][self.id] = self.params
        self.update_params({
            'status': 'cued'
        })

    def update_params(self, params):
        self.params.update(params)
        self.log_debug(".update_params(%s)" % pformat(params))
        server.broadcast_jobs()

    def validate(self):
        if server.job_data.get(self.process_name) and server.job_data[self.process_name].get(self.id):
            raise  ExistingProcessError('Process already exists with that id')
        return True

    def run(self):
        self.done()

    def done(self):
        self.log_debug("ran process")
        self.update_params({
            'status': 'done'
        })
        GObject.timeout_add(60000, self.remove_job)

    def remove_job(self):
        try:
            del server.job_data[self.process_name][self.id]
        except:
            pass
        return False

    

    def progress(self, percent):
        percent = int(percent)
        now = time()
        if self.last_progress_time < now() - 1.5:
            self.update_params({'percent': percent})


class SetOwnerProcess(Process):
    __name__ = "SetOwnerProcess"
    process_name = 'set_owner_recursive'

    def run(self):
        self.log_debug("RUN called process")
        self.update_params({
            'status': 'starting',
            'text': 'Started, loading folders',
            'class':'progress-bar-info'
        })
        server.broadcast_jobs()
        spec = {
            'folder_id': self.params.folder_id
        }
        sql = """SELECT *
                 FROM folder_owners
                 WHERE folder_id = %(folder_id)s"""

        owners = get_results_assoc_dict(sql, spec)

        sql = """SELECT *
                 FROM folders
                 WHERE folder_id = %(folder_id)s"""

        folder = get_assoc(sql, spec)
        if not folder:
            self.params.update({
                'status': 'error',
                'class': 'progress-bar-danger',
                'text': 'No folder matching id',
                'percent': 100
            })
            return

        sql = """SELECT *
                 FROM folders
                 WHERE dirname LIKE %(dirname)s"""
        spec = {
            'dirname': "%s%%" % folder.get('dirname')
        }
        children = get_results_assoc_dict(sql)

        self.update_params({
            'status': 'running',
            'class': 'progress-bar-warning',
            'percent': 0
        })
        delete_sql = """DELETE FROM folder_owners
                        WHERE folder_id = %(folder_id)s"""
        insert_sql = """INSERT INTO folder_owners (uid, folder_id)
                        VALUES(%(uid)s, %(folder_id))"""
        children_length = float(len(children))
        for i, child in children.items():
            # query(delete_sql, child)
            self.progress(i / children_length * 100)
            if not owners:
                continue
            for owner in owners:
                child['uid'] = owner['uid']
                # query(insert_sql, child)


        self.update_params({
            'status': 'running',
            'class': 'progress-bar-success',
            'percent': 100
        })
        self.done()

class Jobs(Log):
    __name__ = "Jobs"
    def __init__(self, *args, **kwargs):
        self.logger = logger
        self.queue = []
        self.running = False
        self.process = None
        self.process_map = {
            'set_owner_recursive': SetOwnerProcess
        }

    def cue(self, obj):
        Gdk.threads_leave()
        self.log_debug(".cue()"+("<"*100))
        name = obj.get('name')
        if not name:
            self.log_debug("No name for job %s skipping" % job)
            return

        process_class = self.process_map.get('set_owner_recursive')
        if not process_class:
            return
        process = self.spawn_process(process_class, obj)
        self.queue.append(process)
        if not self.running:
            self.start()
        else:
            self.log_debug("self.running == true")

    def start(self):
        if self.running:
            self.log_debug("Process is already running")
            return

        # We start it as an idle process so it ALWAYS leaves the thread
        # to prevent deadlocking the gui.
        GObject.idle_add(self.run_processes)

    def run_processes(self):
        Gdk.threads_leave()
        self.log_debug(".run_processes()")
        self.running = True
        len_queue = len(self.queue)

        while len_queue:
            len_queue = len(self.queue)
            self.process = None
            self.log_debug("# Jobs remaining: %s" % len_queue)
            if not len_queue:
                break;
            self.process = self.queue.pop(0) # grab the first element
            self.log_debug("self.process:%s" % self.process)
            if not self.process:
                self.log_debug("NO PROCESS??")
                continue
            self.run_process()
            len_queue = len(self.queue)

        server.broadcast_jobs()

        self.running = False

    @log_failure
    def run_process(self):
        self.log_debug("Running process: %s" % pformat(self.process))
        self.process.run()


    
    def spawn_process(self, process_class, job):
        self.log_debug(".spawn_process(%r, %r)" % (process_class, job))
        try:
            return process_class(job)
        except:
            print "FAILED"
            raise;





