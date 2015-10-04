import logging
import logging.handlers
import os
import sys  
from datetime import datetime
import traceback
from pprint import pformat

log_args = {
    'level': logging.DEBUG, 
    'format':'%(asctime)s - %(name)s - %(levelname)s:%(message)s',
    
}

log_dir = os.path.expanduser("~/.fmp/logs")
if not os.path.exists(log_dir):
    os.mkdir(log_dir)
LOGFILE = os.path.join(log_dir, "fmp.log")

log_args['filename'] = LOGFILE

logger = logging.getLogger('')

logger.setLevel(logging.DEBUG)
format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:%(message)s')

ch = logging.StreamHandler(sys.stdout)
ch.setFormatter(format)
logger.addHandler(ch)

fh = logging.handlers.RotatingFileHandler(LOGFILE, maxBytes=(1048576*5), backupCount=7)
fh.setFormatter(format)
logger.addHandler(fh)

def outer_applicator(func, *args, **kwargs):
    try:
        # print "outer_applicator:", func, "args:", args, "kwargs:", kwargs
        func(*args,**kwargs)
    except:
        exc_info = sys.exc_info()
        stack = traceback.extract_stack()
        tb = traceback.extract_tb(exc_info[2])
        full_tb = stack[:-1] + tb
        exc_line = traceback.format_exception_only(*exc_info[:2])
        spec = {
            "func": func.__name__,
            "error_type": exc_info[0].__name__,
            "error_message": exc_info[1],
            "traceback": ("Traceback (most recent call last):\n"
                          "".join(traceback.format_list(full_tb))+"\n"
                          "".join(exc_line)),
            "args": "%s" % pformat(args),
            "kwargs": "%s" % pformat(kwargs)
        }
        msg = "ERROR func:%(func)r error_type:%(error_type)s error_message:%(error_message)s\n%(traceback)s args:%(args)r kwargs:%(kwargs)s" % spec
        try:
            logger.error(msg)
        except:
            print msg
            raise

def log_failure(func):
    def applicator(*args, **kwargs):
        outer_applicator(func, *args, **kwargs)
    
    return applicator

@log_failure
def test_log_failure(*args, **kwargs):
    int(None)

test_log_failure()

class Log(object):
    __name__ = 'Log'
    logger = logger
    show_args = False
    def __init__(self, *args, **kwargs):
        if self.show_args:
            self.log_debug('.__init__() args:%s kwargs:%s' % (args, kwargs))
        return

    @log_failure
    def log(self, funct, message, *args, **kwargs):
        if (isinstance(message, dict)):
            message = pformat(message)

        formatted_args = []
        for arg in args:
            formatted_args.append(pformat(arg))

        if not message.startswith(" ") and not message.startswith("."):
            message = " "+message
        if "%" not in message and formatted_args:
            message = message + " ".join(formatted_args)
            formatted_args = formatted_args
        funct(self.__name__+message, *formatted_args)
            
    def log_debug(self, message, *args, **kwargs):
        self.log(self.logger.debug, message, *args, **kwargs)

    def log_info(self, message, *args, **kwargs):
        self.log(self.logger.info, message, *args, **kwargs)

    def log_warning(self, message, *args, **kwargs):
        self.log(self.logger.warning, message, *args, **kwargs)

    def log_error(self, message, *args, **kwargs):
        self.log(self.logger.error, message, *args, **kwargs)

    def log_critical(self, message, *args, **kwargs):
        self.log(self.logger.critical, message, *args, **kwargs)
