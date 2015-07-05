import logging

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s:%(message)s',)
logger = logging.getLogger(__name__)

from pprint import pformat

class Log(object):
    __name__ = 'Log'
    logger = logger
    show_args = False
    def __init__(self, *args, **kwargs):
        if self.show_args:
            self.log_debug('.__init__() args:%s kwargs:%s' % (args, kwargs))
        return

    def log(self, funct, message, *args, **kwargs):
        try:
            for arg in args:
                arg = pformat(arg)
            if not message.startswith(" ") and not message.startswith("."):
                message = " "+message
            funct(self.__name__+message, *args)
        except:
            print "ERROR DISPLAYING message"
            print "message:",message
            print "args:", args
            print "kwargs:", kwargs

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
