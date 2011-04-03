# vim: set fileencoding=utf-8:

import sys

def info(message):
    print message

def debug(message):
    print message

def error(message):
    print >>sys.stderr, message
