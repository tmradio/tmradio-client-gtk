# vim: set fileencoding=utf-8:

import os
import logging
import logging.handlers
import sys

import tmradio.config

class Logger:
    instance = None

    def __init__(self):
        self.log = logging.getLogger('tmradio-client')
        self.log.setLevel(logging.DEBUG)

        logname = os.path.expanduser(tmradio.config.Open().get_log())
        h = logging.handlers.RotatingFileHandler(logname, maxBytes=1000000, backupCount=5)
        h.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        h.setLevel(logging.DEBUG)
        self.log.addHandler(h)

    @classmethod
    def get(cls):
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance

def debug(text):
    try: print text.strip()
    except: pass
    Logger.get().log.debug(text)

def info(text):
    try: print text.strip()
    except: pass
    Logger.get().log.info(text)

def error(text):
    try: print >>sys.stderr, text.strip()
    except: pass
    Logger.get().log.error(text)
