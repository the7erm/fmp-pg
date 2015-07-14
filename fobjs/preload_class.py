
try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from utils import utcnow
from misc import _listeners

from log_class import Log, logging
logger = logging.getLogger(__name__)
from misc import get_fobj
from pprint import pprint

class Preload(Log):
    def __init__(self, *args, **kwargs):
        self.refresh_lock = False
        self.logger = logger
        super(Preload, self).__init__(*args, **kwargs)
        self.preload = []
        self.plids = []

    def refresh_once(self, *args, **kwargs):
        self.refresh()

    def refresh(self, *args, **kwargs):
        if self.refresh_lock:
            return True
        self.refresh_lock = True
        self.log_debug(".refresh")
        sql = """SELECT *
             FROM preload
             ORDER BY plid, uid"""
        results = get_results_assoc_dict(sql)
        self.plids = []
        seen_plids = []
        for p in self.preload:
            self.plids.append(p.kwargs.get('plid'))
        for r in results:
            wait()
            seen_plids.append(r['plid'])
            if r['plid'] in self.plids:
                continue
            self.plids.append(r['plid'])
            fobj = get_fobj(**r)
            if fobj:
                self.preload.append(fobj)

        to_remove_plids = set(self.plids) - set(seen_plids)
        to_remove = []
        print "to_remove_plids:", to_remove_plids
        
        for fobj in self.preload:
            if fobj.kwargs.get('plid') in to_remove_plids:
                to_remove.append(fobj)

        for fobj in to_remove:
            self.preload.remove(fobj)
        self.refresh_lock = True
        return True


    def json(self):
        results = []
        for obj in self.preload:
            results.append(obj.json())
        # self.log_debug("preload:%s", results)
        return results
