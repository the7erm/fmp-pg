try:
    from db.db import *
except:
    from sys import path
    path.append("../")
    from db.db import *

from user_file_info_class import UserFileInfo, UserNetcastInfo
from utils import utcnow
from misc import _listeners

from log_class import Log, logging
logger = logging.getLogger(__name__)

class Listeners(Log):
    __name__ = 'Listeners'
    def __init__(self, *args, **kwargs):
        self.kwargs = kwargs
        self.logger = logger
        super(Listeners, self).__init__(*args, **kwargs)
        self.listeners = _listeners(kwargs.get('listeners', None))
        self.parent = kwargs.get('parent')
        self.user_file_info = []
        
        if kwargs.get('fid'):
            for l in self.listeners:
                kwargs.update(l)
                kwargs['userDbInfo'] = l
                self.user_file_info.append(UserFileInfo(**kwargs))

        if kwargs.get('eid'):
            for l in self.listeners:
                kwargs.update(l)
                kwargs['userDbInfo'] = l
                self.user_file_info.append(UserNetcastInfo(**kwargs))

    def init_mark_as_played_sql_args(self, sql_args):
        ultp = sql_args.get('ltp', 
                            sql_args.get('now', utcnow())
                         )
        sql_args.update({
            'ultp': ultp,
            'time_played': ultp,
            'date_played': ultp.date(),
            'fid': self.parent.fid,
            'eid': self.parent.eid,
        })

    def mark_as_played(self, **sql_args):
        self.log_debug(".mark_as_played")
        self.init_mark_as_played_sql_args(sql_args)
        for user_file_info in self.user_file_info:
            user_file_info.mark_as_played(**sql_args)
        return

    def calculate_true_score(self, *args, **sql_args):
        for user_file_info in self.user_file_info:
            user_file_info.calculate_true_score()
            

    def inc_score(self, **sql_args):
        sql_args['edited'] = sql_args.get('edited', False)
        for user_file_info in self.user_file_info:
            user_file_info.inc_score(**sql_args)

    def deinc_score(self, **sql_args):
        for user_file_info in self.user_file_info:
            user_file_info.deinc_score(**sql_args)
