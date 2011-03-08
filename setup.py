#!/usr/bin/env python
# vim: set fileencoding=utf-8:

import glob
from distutils.core import setup

# Files to install:
data_files = [
    ('share/applications', ['data/tmradio.desktop']),
    ('share/icons/hicolor/16x16/apps', ['data/icon-16.png']),
    ('share/icons/hicolor/24x24/apps', ['data/icon-24.png']),
    ('share/icons/hicolor/256x256/apps', ['data/icon-256.png']),
    ('share/icons/hicolor/32x32/apps', ['data/icon-32.png']),
    ('share/icons/hicolor/48x48/apps', ['data/icon-48.png']),
    ('share/icons/hicolor/64x64/apps', ['data/icon-64.png']),
    ('share/icons/hicolor/72x72/apps', ['data/icon-72.png']),
    ('share/tmradio-client', glob.glob('data/*.ui')),
]

packages = []

setup(
    name = 'tmradio-client',
    version = '0.12',
    package_dir = { '': 'src' },
    packages = packages,
    description = 'media player',
    author = 'Justin Forest',
    author_email = 'hex@umonkey.net',
    url = 'http://tmradio.net/',
    scripts = [ 'bin/tmradio-client' ],
    data_files = data_files
)
