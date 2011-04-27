# vim: set fileencoding=utf-8:

import os
import logging
import logging.handlers
import sys

import tmradio.config

quiet = False

class Logger(object):
    instance = None
    name = 'default'

    def __init__(self):
        self.log = logging.getLogger(self.name)
        self.log.setLevel(logging.DEBUG)

        logname = os.path.expanduser(self.get_filename())
        h = logging.handlers.RotatingFileHandler(logname, maxBytes=1000000, backupCount=5)
        h.setFormatter(logging.Formatter(self.get_format()))
        h.setLevel(logging.DEBUG)
        self.log.addHandler(h)

    def get_filename(self):
        return tmradio.config.Open().get_log()

    def get_format(self):
        return '%(asctime)s - %(levelname)s - %(message)s'

    @classmethod
    def get(cls):
        if cls.instance is None:
            cls.instance = cls()
        return cls.instance

class ChatLogger(Logger):
    instance = None
    name = 'chat'

    def get_filename(self):
        return tmradio.config.Open().get_chat_log()

    def get_format(self):
        return '%(asctime)s - %(message)s'

def debug(text):
    if not quiet:
        try: print text.strip()
        except: pass
    Logger.get().log.debug(text)

def info(text):
    if not quiet:
        try: print text.strip()
        except: pass
    Logger.get().log.info(text)

def error(text):
    if not quiet:
        try: print >>sys.stderr, text.strip()
        except: pass
    Logger.get().log.error(text)

def chat(text):
    ChatLogger.get().log.info(text)
