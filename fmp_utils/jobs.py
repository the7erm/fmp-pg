
import sys
from collections import defaultdict
from time import time

class Jobs():
    # This class is designed to be called every once in a while.
    # the idea is to execute a job once a second during the time_status
    # iteration.
    def __init__(self):
        self.low = []
        self.med = []
        self.high = []
        self.picker = defaultdict(list)
        self.user_ids = []

    def run_next_job(self):
        end_time = time() + 0.5

        print("end_time:", end_time, 'time:', time())
        self.run_picker_jobs(end_time)

        while self.high:
            job = self.high.pop(0)
            self.exe(job)
            if time() < end_time:
                 return

        while self.med:
            job = self.med.pop(0)
            self.exe(job)
            if time() < end_time:
                 return

        while self.low:
            job = self.low.pop(0)
            self.exe(job)
            if time() < end_time:
                 return

        print ("jobs complete")

    def run_picker_jobs(self, end_time):

        if not self.picker:
            return

        one_has_jobs = False
        for user_id, user_jobs in self.picker.items():
            if user_jobs:
                one_has_jobs = True
            if user_id not in self.user_ids:
                self.user_ids.append(user_id)

        if not self.user_ids or not one_has_jobs:
            return

        exe_cnt = 0
        while time() < end_time or exe_cnt == 0:
            print("time():", time(), end_time, end_time - time())
            exe_cnt += 1
            user_turn = self.user_ids.pop(0)
            self.user_ids.append(user_turn)
            print(self.user_ids)

            for user_id, user_jobs in self.picker.items():

                if user_id != user_turn:
                    continue

                if user_jobs:
                    job = user_jobs.pop(0)
                    self.exe(job)

    def exe(self, job):
        cmd, args, kwargs = job
        print("exe:", cmd, args, kwargs)
        try:
            cmd(*args, **kwargs)
        except:
            e = sys.exc_info()[0]
            print("Error cmd:", cmd)
            print("Error args:", args)
            print("Error kwargs:", kwargs)
            print("Error:", e)

    def append(self, cmd, *args, **kwargs):
        priority = kwargs.get('priority', 'low')
        if priority not in ('low', 'med', 'high'):
            priority = 'low'

        jobs = getattr(self, priority)
        jobs.append((cmd, args, kwargs))

    def append_low(self, cmd, *args, **kwargs):
        self.low.append((cmd, args, kwargs))

    def append_med(self, cmd, *args, **kwargs):
        self.med.append((cmd, args, kwargs))

    def append_high(self, cmd, *args, **kwargs):
        self.high.append((cmd, args, kwargs))

    def append_picker(self, user_id, cmd, *args, **kwargs):
        self.picker[user_id].append((cmd, args, kwargs))

jobs = Jobs()


